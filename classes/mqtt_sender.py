import paho.mqtt.client as mqtt
from utils.queue_operations import SafeQueue
import json
import logging
from typing import Dict, Any
import threading
import time
from classes.enums import PublishType
from config.schema import ConfigSchema
import queue

class MqttHandler:
    def __init__(self, config: ConfigSchema, queue: SafeQueue):
        self.config = config
        self.client = None
        self.queue = queue
        self.logger = logging.getLogger(__name__)
        self.is_connected = False
        self.reconnect_interval = 5
        self.device_token = config.thingsboard.device_token
        self.tb_host = config.thingsboard.host
        self.tb_port = config.thingsboard.port

    def connect(self):
        self.client = mqtt.Client()
        self.client.username_pw_set(self.device_token)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect

        try:
            self.client.connect(self.tb_host, self.tb_port, 60)
            self.client.loop_start()
        except Exception as e:
            self.logger.error(f"Failed to connect to ThingsBoard: {e}")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.logger.info("Connected to ThingsBoard")
            self.is_connected = True
        else:
            self.logger.error(f"Failed to connect to ThingsBoard, return code: {rc}")

    def on_disconnect(self, client, userdata, rc):
        self.logger.warning("Disconnected from ThingsBoard")
        self.is_connected = False

    def publish_telemetry(self, telemetry: Dict[str, Any]):
        if not self.is_connected:
            self.logger.warning("Not connected to ThingsBoard. Queueing telemetry.")
            return

        try:
            self.client.publish('v1/devices/me/telemetry', json.dumps(telemetry))
        except Exception as e:
            self.logger.error(f"Failed to publish telemetry: {e}")

    def publish_attributes(self, attributes: Dict[str, Any]):
        if not self.is_connected:
            self.logger.warning("Not connected to ThingsBoard. Queueing attributes.")
            self.queue.put((PublishType.ATTRIBUTE, attributes))
            return

        try:
            self.client.publish('v1/devices/me/attributes', json.dumps(attributes))
        except Exception as e:
            self.logger.error(f"Failed to publish attributes: {e}")
            self.queue.put((PublishType.ATTRIBUTE, attributes))

    def publish_events(self, event: Dict[str, Any]):
        if not self.is_connected:
            self.logger.warning("Not connected to ThingsBoard. Queueing event.")
            self.queue.put((PublishType.EVENT, event))
            return

        try:
            self.client.publish('v1/devices/me/events', json.dumps(event))
        except Exception as e:
            self.logger.error(f"Failed to publish event: {e}")
            self.queue.put((PublishType.EVENT, event))

    def process_queue(self):
        while not self.shutdown_flag.is_set():
            if self.is_connected:
                try:
                    message_type, message = self.queue.get(block=False)
                    self.logger.debug(f"Processing message of type {message_type}: {message}")
                    if message_type == PublishType.TELEMETRY:
                        if not isinstance(message, dict):
                            self.logger.error(f"Invalid telemetry data format: {message}")
                            continue
                        self.publish_telemetry(message)
                    elif message_type == PublishType.ATTRIBUTE:
                        if not isinstance(message, dict):
                            self.logger.error(f"Invalid attribute data format: {message}")
                            continue
                        self.publish_attributes(message)
                    elif message_type == PublishType.EVENT:
                        if not isinstance(message, str):
                            self.logger.error(f"Invalid event data format: {message}")
                            continue
                        self.publish_events(message)
                    else:
                        self.logger.error(f'PublishType {message_type} is not supported')
                except queue.Empty:
                    time.sleep(1)
            else:
                time.sleep(self.reconnect_interval)

    def start(self):
        self.connect()
        self.shutdown_flag = threading.Event()
        threading.Thread(target=self.process_queue, daemon=True).start()

    def stop(self):
        self.shutdown_flag.set()
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()