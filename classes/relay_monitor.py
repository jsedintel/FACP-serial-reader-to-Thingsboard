import RPi.GPIO as GPIO
import threading
import time
from typing import Dict
from utils.queue_operations import SafeQueue
from classes.enums import PublishType
import logging
from config.schema import ConfigSchema

class RelayMonitor:
    def __init__(self, config: ConfigSchema, queue: SafeQueue):
        self.config = config
        self.queue = queue
        self.relay_pins = {
            'ALARM': config.relay_monitor.alarm_pin,
            'TROUBLE': config.relay_monitor.trouble_pin,
            'SUPERVISION': config.relay_monitor.supervision_pin
        }
        self.publish_interval = config.relay_monitor.publish_interval
        self.logger = logging.getLogger(__name__)
        self.setup_gpio()

    def setup_gpio(self):
        GPIO.setmode(GPIO.BCM)
        for pin in self.relay_pins.values():
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def monitor_relays(self, shutdown_flag: threading.Event):
        while not shutdown_flag.is_set():
            telemetry = self.get_relay_states()
            self.add_telemetry_to_queue(telemetry)
            
            # Wait for the next interval or until the shutdown flag is set
            if shutdown_flag.wait(self.publish_interval):
                break

    def get_relay_states(self) -> Dict[str, int]:
        telemetry = {}
        for status, pin in self.relay_pins.items():
            current_state = GPIO.input(pin)
            relay_state = 1 if current_state == GPIO.LOW else 0  # 1 means active (closed), 0 means inactive (open)
            telemetry[status.lower() + '_relay'] = relay_state
        return telemetry

    def add_telemetry_to_queue(self, telemetry: Dict[str, int]):
        self.logger.debug(f"Adding relay telemetry to queue: {telemetry}")
        self.queue.put((PublishType.TELEMETRY, telemetry))

    def cleanup(self):
        try:
            GPIO.cleanup(list(self.relay_pins.values()))
            self.logger.info("GPIO cleanup completed for RelayMonitor")
        except Exception as e:
            self.logger.error(f"Error during GPIO cleanup in RelayMonitor: {e}")