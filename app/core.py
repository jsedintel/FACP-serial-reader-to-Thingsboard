import logging
import time
from config.loader import ConfigSchema
from classes.mqtt_sender import MqttHandler
from classes.specific_serial_handler import Edwards_iO1000, Edwards_EST3x, Notifier_NFS320
from app_utils.queue_operations import SafeQueue
from components.update_app import update_check_thread
from components.relay_controller import RelayController
from components.queue_manager import QueueManager
from components.thread_manager import ThreadManager
from classes.relay_monitor import RelayMonitor
from classes.serial_port_handler import SerialPortHandler

class Application:
    def __init__(self, config: ConfigSchema, event_severity_levels: dict):
        self.config = config
        self.event_severity_levels = event_severity_levels
        self.queue = SafeQueue()
        self.mqtt_handler = MqttHandler(self.config, self.queue)
        self.id_modelo_panel: int = None
        self.serial_handler: SerialPortHandler = None

        self.queue_manager = QueueManager(self.queue, "queue_backup.pkl")
        self.relay_controller = RelayController(config.relay)
        self.relay_monitor = RelayMonitor(config, self.queue)
        self.thread_manager = ThreadManager()

        self.logger = logging.getLogger(__name__)

    def _create_serial_handler(self):
        if self.id_modelo_panel is None:
            raise ValueError("id_modelo_panel is not set")
        
        severity_list = self.event_severity_levels.get(self.id_modelo_panel, {})
        
        handlers = {
            10001: Edwards_iO1000,
            10002: Edwards_EST3x,
            10003: Notifier_NFS320
        }
        
        handler_class = handlers.get(self.id_modelo_panel)
        if not handler_class:
            raise ValueError(f"Unsupported panel model: {self.id_modelo_panel}")
        
        return handler_class(self.config, severity_list, self.queue)

    def on_attributes_change(self, result, exception):
        if exception is not None:
            self.logger.error(f"Error in attribute update: {exception}")
            return

        self.logger.info(f"Received attribute update: {result}")
        if result and 'shared' in result and 'id_modelo_panel' in result['shared']:
            new_id_modelo_panel = int(result['shared']['id_modelo_panel'])
            self.logger.info(f"Received new id_modelo_panel: {new_id_modelo_panel}")
            if new_id_modelo_panel != self.id_modelo_panel:
                self.id_modelo_panel = new_id_modelo_panel
                self.logger.info(f"id_modelo_panel set to {self.id_modelo_panel}")
                self.restart_serial_handler()
            else:
                self.logger.info(f"id_modelo_panel is already set to {self.id_modelo_panel}")
        elif result and 'id_modelo_panel' in result:
            new_id_modelo_panel = int(result['id_modelo_panel'])
            self.logger.info(f"Received new id_modelo_panel: {new_id_modelo_panel}")
            if new_id_modelo_panel != self.id_modelo_panel:
                self.id_modelo_panel = new_id_modelo_panel
                self.logger.info(f"id_modelo_panel updated to {self.id_modelo_panel}")
                self.restart_serial_handler()
            else:
                self.logger.info(f"id_modelo_panel is already set to {self.id_modelo_panel}")
        else:
            self.logger.warning("Received attribute is not implemented")

    def restart_serial_handler(self):
        if self.serial_handler:
            self.thread_manager.stop_thread("listening_to_serial")
        self.serial_handler = self._create_serial_handler()
        self.thread_manager.start_thread(self.serial_handler.listening_to_serial)

    def request_id_modelo_panel(self):
        retry_delay = 5
        attempt = 0
        while True:
            try:
                self.logger.info(f"Requesting id_modelo_panel (attempt {attempt + 1})")
                self.mqtt_handler.request_attributes([],['id_modelo_panel'], callback=self.on_attributes_change)
                
                # Wait for the id_modelo_panel to be set
                for _ in range(10):  # Wait up to 10 seconds
                    if self.id_modelo_panel is not None:
                        self.logger.info(f"Received id_modelo_panel: {self.id_modelo_panel}")
                        return
                    time.sleep(1)
                
                self.logger.warning(f"Failed to get id_modelo_panel. Retrying in {retry_delay} seconds...")
                attempt=+1
                time.sleep(retry_delay)
            except Exception as e:
                self.logger.error("Unknown error happened: " + e)
                self.logger.info("Retrying...")
                attempt=+1
                time.sleep(1)
                

    def start(self):
        self.logger.info("Starting application...")
        self.queue_manager.load_queue()
        self.mqtt_handler.start()
        time.sleep(2)
        self.mqtt_handler.subscribe_to_attribute("id_modelo_panel", self.on_attributes_change)
        self.logger.info("Requesting initial id_modelo_panel value")
        self.request_id_modelo_panel()

        if self.id_modelo_panel is None:
            raise RuntimeError("Failed to get initial id_modelo_panel value")
        
        self.serial_handler = self._create_serial_handler()
        
        threads = [
            #update_check_thread,
            self.queue_manager.save_queue_periodically,
            self.relay_monitor.monitor_relays,
            self.relay_controller.relay_control
        ]

        self.thread_manager.start_threads(threads)

        try:
            self.thread_manager.monitor_threads()
        except KeyboardInterrupt:
            self.logger.info("Program terminated by user")
        finally:
            self.shutdown()

    def shutdown(self):
        self.logger.info("Initiating graceful shutdown...")
        self.thread_manager.stop_all_threads()
        self.queue_manager.save_queue()
        self.relay_controller.cleanup()
        self.relay_monitor.cleanup()
        self.mqtt_handler.stop()
        self.logger.info("Graceful shutdown completed")