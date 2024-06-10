# mqtt_handler.py
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
        self.attempt_count = 0  # Counter for connection attempts
        self.is_connected = False

    def connect(self) -> None:
        try:
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self._get_client_id())
            self.client.username_pw_set(username=self.config["mqtt"]["usuario"], password=self.config["mqtt"]["contrasena"])
            self.client.tls_set()
            self.client.will_set(self._get_will_topic(), payload=self._get_will_message(), qos=2, retain=True)
            self.client.connect(self.config["mqtt"]["url"], self.config["mqtt"]["puerto"])
            self.client.on_message = self.on_message
            self.client.on_connect = self.on_connect
            self.client.on_disconnect = self.on_disconnect
            self.client.loop_start()
            self._publish_connected_message()
            self.attempt_count = 0  # Reset attempt count after a successful connection
            self.is_connected = True
        except KeyError as e:
            raise KeyError(f"Error en la configuración: falta la clave {e}")
        except Exception as e:
            self.logger.error("Ha ocurrido un error inicializando la conexión MQTT, verifica los credenciales ingresados, así como los datos del broker.")
            self.is_connected = False
            raise ConnectionError("Error al inicializar la conexión MQTT: " + str(e))

    def _get_client_id(self) -> str:
        return f"{self.config['cliente']['id_cliente']}_{self.config['cliente']['id_panel']}_FACP"

    def _get_will_topic(self) -> str:
        return f"{self.config['cliente']['id_cliente']}/FACP/{self.config['cliente']['id_panel']}/Estado"
    
    def on_message(self, client, userdata, msg):
        self.logger.info(f"Mensaje recibido en el tópico {msg.topic}: {msg.payload}")

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            self.is_connected = True
            self.logger.info("Conexión exitosa al broker MQTT")
            self._publish_connected_message()
            self.attempt_count = 0  # Reset attempt count after a successful connection
        else:
            self.logger.error(f"Falló la conexión al broker MQTT con código de error {reason_code}")

    def on_disconnect(self, client, userdata, flags, reason_code, properties):
        self.is_connected = False
        self.logger.warning(f"Desconectado del broker MQTT con código de retorno {reason_code}")
        if reason_code != 0:
            self.logger.info("Desconexión inesperada, intentando reconectar...")
        

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
            if not self.is_connected:
                return False
            else:
                pub_type, message_data = self.queue.get()
                try:
                    self._publish(message_data, pub_type)
                    self.logger.debug(f"Se publico un mensaje exitosamente al broker MQTT")
                except ConnectionError as e:
                    self.logger.error(f"Se perdio la conexion mientras se publicaba, re-encolando el mensaje: {e}")
                    self.queue.put((pub_type, message_data))  # Vuelve a encolar el mensaje
                    return False  # Senal para manejar la reconexion
                except Exception as e:
                    self.logger.error(f"Un error desconocido ha ocurrido mientras se intentaba publicar el mensaje, re-encolando el mensaje: {e}")
                    self.queue.put((pub_type, message_data))
                    return False
        return True

    def listen_to_mqtt(self) -> None:
        while True:
            try:
                if self.client is None or not self.is_connected:
                    if self.client is not None:
                        self.client.loop_stop()
                        self.client = None
                    self.logger.debug(f"Intentando conectar al broker MQTT, intento #{self.attempt_count + 1}")
                    self.connect()
                    self.attempt_count += 1
                    time.sleep(min(60, 2 ** self.attempt_count))  # Exponential backoff up to a maximum of 60 seconds
                if self.client is not None:
                    if not self._process_queue_messages():
                        self.logger.debug("Se perdio la conexion con el broker MQTT. Reiniciando conexion")
                        self.client.loop_stop()
                        self.client = None  # Se resetea el cliente para activar la reconexion
                    else:
                        time.sleep(1)
            except Exception as e:
                self.logger.debug(f"Desde Exception general, intentando conectar al broker MQTT, intento #{self.attempt_count + 1}")
                self.attempt_count += 1
                time.sleep(min(60, 2 ** self.attempt_count))
                self.logger.error("Error inesperado ocurrido. Intentando conectar al broker MQTT de nuevo")
