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
        self.reconnect_attempts = 0
        self.MAX_RECONNECT_ATTEMPTS = 5
        self.RECONNECT_DELAY = 5

    def connect(self) -> None:
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.config["cliente"]["id_cliente"]+"_"+str(self.config["cliente"]["id_panel"])+"_FACP")
        self.client.username_pw_set(username=self.config["mqtt"]["usuario"], password=self.config["mqtt"]["contrasena"])
        self.client.tls_set()
        lwt_message = self.create_lwt_message("Desconectado")
        self.client.will_set(self.config["cliente"]["id_cliente"]+"/FACP/"+str(self.config["cliente"]["id_panel"])+"/Estado", 
                            payload=lwt_message, qos=2, retain=True)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        try:
            self.client.connect(self.config["mqtt"]["url"], self.config["mqtt"]["puerto"])
            self.client.loop_start()
        except KeyError as e:
            raise KeyError(f"Error en la configuración: falta la clave {e}")
        except Exception as e:
            self.logger.exception("Ha ocurrido un error inicializando la conexión MQTT, verifica los credenciales ingresados, así como los datos del broker.")
            raise ConnectionError("Error al inicializar la conexión MQTT: " + str(e))
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.logger.debug("Conectado al broker MQTT")
            self.reconnect_attempts = 0
            self.publish_connected_message()
        else:
            self.logger.error(f"Fallo al conectar al broker MQTT. Codigo de resultado: {rc}")

    def on_disconnect(self, client, userdata, rc):
        self.logger.debug(f"Desconectado del broker MQTT. Codigo de resultado: {rc}")
        if rc != 0:
            self.reconnect()

    def reconnect(self):
        if self.reconnect_attempts < self.MAX_RECONNECT_ATTEMPTS:
            self.reconnect_attempts += 1
            self.logger.debug(f"Intentando reconectar al broker MQTT. Intento #{self.reconnect_attempts}")
            time.sleep(self.RECONNECT_DELAY)
            self.client.reconnect()
        else:
            self.logger.error("Se alcanzo el numero maximo de intentos de reconexion. Deteniendo el cliente MQTT.")
            self.client.loop_stop()
            self.client = None

    def create_lwt_message(self, status):
        try:
            message = json.dumps(OrderedDict([
                ("ID_Cliente", self.config["cliente"]["id_cliente"]),
                ("ID_Panel", self.config["cliente"]["id_panel"]),
                ("Modelo_Panel", self.config["cliente"]["modelo_panel"]),
                ("ID_Modelo_Panel", self.config['cliente']['id_modelo_panel']),
                ("Mensaje", status),
                ("Tipo", "Estado"),
                ("Nivel_Severidad", 4 if status == "Desconectado" else 0),
                ("latitud", self.config["cliente"]["coordenadas"]["latitud"]),
                ("longitud", self.config["cliente"]["coordenadas"]["longitud"])
            ]))
            return message
        except KeyError as e:
            raise KeyError(f"Error en la configuración: falta la clave {e}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Error al generar el mensaje JSON: {e}")

    def publish_connected_message(self):
        try:
            message = self.create_lwt_message("Conectado")
            self.publish(message, PublishType.ESTADO)
        except Exception as e:
            self.logger.exception("Un error inesperado ha ocurrido al intentar crear el mensaje de estado 'Conectado'")

    def publish(self, message: str, pub_type: PublishType) -> None:
        base_topic = f"{self.config['cliente']['id_cliente']}/FACP/{str(self.config['cliente']['id_panel'])}"
        try:
            match pub_type:
                case PublishType.EVENTO:
                    topic = f"{base_topic}/Eventos"
                case PublishType.REPORTE:
                    topic = f"{base_topic}/Reportes"
                case PublishType.ESTADO:
                    topic = f"{base_topic}/Estado"
                case _:
                    raise ValueError("El tipo de publicacion ingresada es invalido")

            qos = 2
            retain = True if pub_type == PublishType.ESTADO else False
            self.client.publish(topic, message, qos=qos, retain=retain)
        except Exception as e:
            raise ConnectionError(f"Error al intentar publicar el mensaje al broker MQTT: {e}")
    
    def process_queue_messages(self) -> bool:
        while not self.queue.empty():
            pub_type, message_data = self.queue.get()
            try:
                self.publish(message_data, pub_type)
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
    
    def listening_to_mqtt(self) -> None:
        while True:
            try:
                if self.client is None:
                    self.logger.debug("Intentando conectar al broker MQTT")
                    self.connect()
                else:
                    if not self.process_queue_messages():
                        self.logger.debug("Se perdio la conexion con el broker MQTT. Esperando reconexion...")
                    if self.queue.empty():
                        time.sleep(1)
            except Exception as e:
                self.logger.exception("Error inesperado ocurrido. Intentando conectar al broker MQTT de nuevo")
                time.sleep(5)