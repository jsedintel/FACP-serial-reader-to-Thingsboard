from tb_device_mqtt import TBDeviceMqttClient
from app_utils.queue_operations import SafeQueue
import logging
from typing import Dict, Any, Callable
import threading
import time
from classes.enums import PublishType
from config.schema import ConfigSchema
import queue

class MqttHandler:
    def __init__(self, config: ConfigSchema, queue: SafeQueue):
        self.config = config
        self.queue = queue
        self.logger = logging.getLogger(__name__)
        self.is_connected = False
        self.reconnect_interval = 5
        self.device_token = config.thingsboard.device_token
        self.tb_host = config.thingsboard.host
        self.tb_port = config.thingsboard.port
        self.client = TBDeviceMqttClient(host=self.tb_host, username=self.device_token, port=self.tb_port)
        self.client.connect()

    def connect(self):
        try:
            self.client.connect()
            self.is_connected = True
            self.logger.info("Successfully connected to ThingsBoard")
        except Exception as e:
            self.logger.error(f"Failed to connect to ThingsBoard: {e}")
            self.is_connected = False

    def publish_telemetry(self, telemetry: Dict[str, Any]):
        if not self.is_connected:
            self.logger.warning("Not connected to ThingsBoard. Queueing telemetry.")
            self.queue.put((PublishType.TELEMETRY, telemetry))
            return

        try:
            self.client.send_telemetry(telemetry)
            self.logger.debug(f"Telemetry sent successfully: {telemetry}")
        except Exception as e:
            self.logger.error(f"Failed to publish telemetry: {e}")
            self.queue.put((PublishType.TELEMETRY, telemetry))

    def publish_attributes(self, attributes: Dict[str, Any]):
        if not self.is_connected:
            self.logger.warning("Not connected to ThingsBoard. Queueing attributes.")
            self.queue.put((PublishType.ATTRIBUTE, attributes))
            return

        try:
            self.client.send_attributes(attributes)
            self.logger.debug(f"Attributes sent successfully: {attributes}")
        except Exception as e:
            self.logger.error(f"Failed to publish attributes: {e}")
            self.queue.put((PublishType.ATTRIBUTE, attributes))

    def subscribe_to_attribute(self, attribute_name: str, callback: Callable):
        self.client.subscribe_to_attribute(attribute_name, callback)
        self.logger.info(f"Subscribed to attribute: {attribute_name}")

    def request_attributes(self, client_attribute_names: list, shared_attribute_names: list, callback: Callable):
        self.client.request_attributes(client_attribute_names, shared_attribute_names, callback=callback)

    def process_queue(self):
        while not self.shutdown_flag.is_set():
            if self.is_connected:
                try:
                    message_type, message = self.queue.get(block=False)
                    self.logger.debug(f"Processing message of type {message_type}: {message}")
                    if message_type == PublishType.TELEMETRY:
                        self.publish_telemetry(message)
                    elif message_type == PublishType.ATTRIBUTE:
                        self.publish_attributes(message)
                    else:
                        self.logger.error(f'PublishType {message_type} is not supported')
                except queue.Empty:
                    time.sleep(1)
            else:
                self.logger.warning("Not connected to ThingsBoard. Attempting to reconnect...")
                self.connect()
                time.sleep(self.reconnect_interval)

    def start(self):
        self.connect()
        self.shutdown_flag = threading.Event()
        threading.Thread(target=self.process_queue, daemon=True).start()
        self.logger.info("MQTT Handler started")

    def stop(self):
        self.shutdown_flag.set()
        if self.client:
            self.client.disconnect()
        self.logger.info("MQTT Handler stopped")