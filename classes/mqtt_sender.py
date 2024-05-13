import paho.mqtt.client as mqtt
from collections import OrderedDict
from classes.enums import PublishType
from classes.utils import SafeQueue
import json
import logging
import time

class MqttHandler:
    def __init__(self, config: dict, queue: SafeQueue):
        self.config = config
        self.client = None
        self.queue = queue
        self.logger = logging.getLogger(__name__)

    def connect(self) -> None:
        try:
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self._get_client_id())
            self.client.username_pw_set(username=self.config["mqtt"]["usuario"], password=self.config["mqtt"]["contrasena"])
            self.client.tls_set()
            self.client.will_set(self._get_will_topic(), payload=self._get_will_message(), qos=2, retain=True)
            self.client.connect(self.config["mqtt"]["url"], self.config["mqtt"]["puerto"])
            self.client.loop_start()
            self._publish_connected_message()
        except KeyError as e:
            raise KeyError(f"Error en la configuración: falta la clave {e}")
        except Exception as e:
            self.logger.exception("Ha ocurrido un error inicializando la conexión MQTT, verifica los credenciales ingresados, así como los datos del broker.")
            raise ConnectionError("Error al inicializar la conexión MQTT: " + str(e))

    def _get_client_id(self) -> str:
        return f"{self.config['cliente']['id_cliente']}_{self.config['cliente']['id_panel']}_FACP"

    def _get_will_topic(self) -> str:
        return f"{self.config['cliente']['id_cliente']}/FACP/{self.config['cliente']['id_panel']}/Estado"

    def _get_will_message(self) -> str:
        return json.dumps(OrderedDict([
            ("ID_Cliente", self.config["cliente"]["id_cliente"]),
            ("ID_Panel", self.config["cliente"]["id_panel"]),
            ("Modelo_Panel", self.config["cliente"]["modelo_panel"]),
            ("ID_Modelo_Panel", self.config['cliente']['id_modelo_panel']),
            ("Mensaje", "Desconectado"),
            ("Tipo", "Estado"),
            ("Nivel_Severidad", 4),
            ("latitud", self.config["cliente"]["coordenadas"]["latitud"]),
            ("longitud", self.config["cliente"]["coordenadas"]["longitud"])
        ]))

    def _publish_connected_message(self) -> None:
        try:
            message = json.dumps(OrderedDict([
                ("ID_Cliente", self.config["cliente"]["id_cliente"]),
                ("ID_Panel", self.config["cliente"]["id_panel"]),
                ("Modelo_Panel", self.config["cliente"]["modelo_panel"]),
                ("ID_Modelo_Panel", self.config['cliente']['id_modelo_panel']),
                ("Mensaje", "Conectado" if self.queue.is_serial_connected else "Fallo serial"),
                ("Tipo", "Estado"),
                ("Nivel_Severidad", 0),
                ("latitud", self.config["cliente"]["coordenadas"]["latitud"]),
                ("longitud", self.config["cliente"]["coordenadas"]["longitud"])
            ]))
            self._publish(message, PublishType.ESTADO)
            self.logger.debug("Se ha conectado al broker MQTT")
        except KeyError as e:
            raise KeyError(f"Error en la configuración: falta la clave {e}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Error al generar el mensaje JSON: {e}")
        except Exception as e:
            raise ConnectionError(f"Un error inesperado ha ocurrido al intentar crear el mensaje de estado 'Conectado' {e}")

    def _get_publish_topic(self, pub_type: PublishType) -> str:
        base_topic = f"{self.config['cliente']['id_cliente']}/FACP/{self.config['cliente']['id_panel']}"
        match pub_type:
            case PublishType.EVENTO:
                return f"{base_topic}/Eventos"
            case PublishType.REPORTE:
                return f"{base_topic}/Reportes"
            case PublishType.ESTADO:
                return f"{base_topic}/Estado"
            case _:
                raise ValueError("El tipo de publicacion ingresada es invalido")

    def _publish(self, message: str, pub_type: PublishType) -> None:
        try:
            topic = self._get_publish_topic(pub_type)
            qos = 2
            retain = pub_type == PublishType.ESTADO
            self.client.publish(topic, message, qos=qos, retain=retain)
        except Exception as e:
            raise ConnectionError(f"Error al intentar publicar el mensaje al broker MQTT: {e}")

    def _process_queue_messages(self) -> bool:
        while not self.queue.empty():
            pub_type, message_data = self.queue.get()
            try:
                self._publish(message_data, pub_type)
                self.logger.debug(f"Se publico un mensaje exitosamente al broker MQTT")
            except ConnectionError as e:
                self.logger.error(f"Se perdio la conexion mientras se publicaba, re-encolando el mensaje: {e}")
                self.queue.put((pub_type, message_data))  # Vuelve a encolar el mensaje
                self.client = None  # Set self.client to None to trigger reconnection
                return False  # Senal para manejar la reconexion
            except Exception as e:
                self.logger.error(f"Un error desconocido ha ocurrido mientras se intentaba publicar el mensaje, re-encolando el mensaje: {e}")
                self.queue.put((pub_type, message_data))
                return False
        return True

    def listen_to_mqtt(self) -> None:
        while True:
            try:
                if self.client is None or not self.client.is_connected():
                    self.logger.debug("Intentando conectar al broker MQTT")
                    self.connect()
                    time.sleep(1)
                if self.client is not None:
                    if not self._process_queue_messages():
                        self.logger.debug("Se perdio la conexion con el broker MQTT. Reiniciando conexion")
                        self.client = None  # Se resetea el cliente para activar la reconexion
                if self.queue.empty():
                    time.sleep(1)
            except Exception as e:
                time.sleep(5)
                self.logger.exception("Error inesperado ocurrido. Intentando conectar al broker MQTT de nuevo")