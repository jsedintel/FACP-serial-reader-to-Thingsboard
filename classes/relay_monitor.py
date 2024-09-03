import RPi.GPIO as GPIO
import threading
from typing import Dict, List
from utils.queue_operations import SafeQueue
from classes.enums import PublishType
import logging
from config.schema import ConfigSchema

class RelayMonitor:
    def __init__(self, config: ConfigSchema, queue: SafeQueue):
        self.config = config
        self.queue = queue
        self.relay_pins = self._get_relay_pins()
        self.publish_interval = config.relay_monitor.publish_interval
        self.logger = logging.getLogger(__name__)
        self._setup_gpio()

    def _get_relay_pins(self) -> Dict[str, int]:
        return {
            'ALARM': self.config.relay_monitor.alarm_pin,
            'TROUBLE': self.config.relay_monitor.trouble_pin,
            'SUPERVISION': self.config.relay_monitor.supervision_pin
        }

    def _setup_gpio(self):
        GPIO.setmode(GPIO.BCM)
        for pin in self.relay_pins.values():
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def monitor_relays(self, shutdown_flag: threading.Event):
        while not shutdown_flag.is_set():
            telemetry = self._get_relay_states()
            self._add_telemetry_to_queue(telemetry)
            
            if shutdown_flag.wait(self.publish_interval):
                break

    def _get_relay_states(self) -> Dict[str, bool]:
        return {
            f"{status.lower()}_relay": GPIO.input(pin) == GPIO.LOW
            for status, pin in self.relay_pins.items()
        }

    def _add_telemetry_to_queue(self, telemetry: Dict[str, bool]):
        self.queue.put((PublishType.TELEMETRY, telemetry))

    def cleanup(self):
        try:
            self._cleanup_gpio()
            self.logger.info("GPIO cleanup completed for RelayMonitor")
        except Exception as e:
            self.logger.error(f"Error during GPIO cleanup in RelayMonitor: {e}")

    def _cleanup_gpio(self):
        GPIO.cleanup(list(self.relay_pins.values()))