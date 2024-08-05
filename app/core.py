import threading
import logging
from config.loader import ConfigSchema
from classes.mqtt_sender import MqttHandler
from classes.specific_serial_handler import Edwards_iO1000, Edwards_EST3x, Notifier_NFS320
from utils.queue_operations import SafeQueue
from components.update_app import update_check_thread
from components.relay_controller import RelayController
from components.queue_manager import QueueManager
from components.thread_manager import ThreadManager
from classes.relay_monitor import RelayMonitor
from classes.enums import PublishType

class Application:
    def __init__(self, config: ConfigSchema, event_severity_levels: dict):
        self.config = config
        self.event_severity_levels = event_severity_levels
        self.queue = SafeQueue()
        self.mqtt_handler = MqttHandler(self.config, self.queue)
        self.serial_handler = self._create_serial_handler()
        self.shutdown_flag = threading.Event()

        self.queue_manager = QueueManager(self.queue, "queue_backup.pkl")
        self.relay_controller = RelayController(config.relay)
        self.relay_monitor = RelayMonitor(config, self.queue)
        self.thread_manager = ThreadManager(self.shutdown_flag)

    def _create_serial_handler(self):
        id_modelo_panel = self.config.cliente.id_modelo_panel
        severity_list = self.event_severity_levels.get(id_modelo_panel, {})
        
        handlers = {
            10001: Edwards_iO1000,
            10002: Edwards_EST3x,
            10003: Notifier_NFS320
        }
        
        handler_class = handlers.get(id_modelo_panel)
        if not handler_class:
            raise ValueError(f"Unsupported panel model: {id_modelo_panel}")
        
        return handler_class(self.config, severity_list, self.queue)

    def send_device_attributes(self):
        attributes = {
            "Modelo Panel": self.config.cliente.modelo_panel,
            "Nombre Panel": self.config.cliente.id_panel,
            "Raspberry Pi name:": self.config.cliente.RPi
        }
        self.queue.put((PublishType.ATTRIBUTE, attributes))

    def start(self):
        self.queue_manager.load_queue()
        self.mqtt_handler.start()
        
        # Send device attributes at startup
        self.send_device_attributes()
        
        threads = [
            threading.Thread(target=self.serial_handler.listening_to_serial, args=(self.shutdown_flag,)),
            threading.Thread(target=update_check_thread, args=(self.shutdown_flag,)),
            threading.Thread(target=self.queue_manager.save_queue_periodically, args=(self.shutdown_flag,)),
            threading.Thread(target=self.relay_monitor.monitor_relays, args=(self.shutdown_flag,)),
        ]

        if self.relay_controller.is_raspberry_pi:
            threads.append(threading.Thread(target=self.relay_controller.relay_control, args=(self.shutdown_flag,)))

        self.thread_manager.start_threads(threads)

        try:
            self.thread_manager.monitor_threads()
        except KeyboardInterrupt:
            logging.info("Program terminated by user")
        finally:
            self.shutdown()

    def shutdown(self):
        logging.info("Initiating graceful shutdown...")
        self.shutdown_flag.set()
        self.thread_manager.stop_threads()
        self.queue_manager.save_queue()
        self.relay_controller.cleanup()
        self.relay_monitor.cleanup()
        self.mqtt_handler.stop()
        logging.info("Graceful shutdown completed")