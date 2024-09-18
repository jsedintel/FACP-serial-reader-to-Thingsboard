import RPi.GPIO as GPIO
import threading
from typing import Dict
from app_utils.queue_operations import SafeQueue
from classes.enums import PublishType
import logging
from config.schema import ConfigSchema

class RelayMonitor:
    def __init__(self, config: ConfigSchema, queue: SafeQueue):
        self.config = config
        self.queue = queue
        self.relay_pins = self._get_relay_pins()
        self.active_states = self._get_active_states()
        self.publish_interval = config.relay_monitor.publish_interval
        self.logger = logging.getLogger(__name__)
        self._setup_gpio()

    def _get_relay_pins(self) -> Dict[str, int]:
        return {
            'ALARM': self.config.relay_monitor.alarm_pin,
            'TROUBLE': self.config.relay_monitor.trouble_pin
        }

    def _get_active_states(self) -> Dict[str, int]:
        return {
            'ALARM': GPIO.HIGH if self.config.relay_monitor.alarm_active_high else GPIO.LOW,
            'TROUBLE': GPIO.HIGH if self.config.relay_monitor.trouble_active_high else GPIO.LOW
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
        states = {}
        for status, pin in self.relay_pins.items():
            gpio_state = GPIO.input(pin)
            active_state = self.active_states[status]
            is_active = gpio_state == active_state
            states[f"{status.lower()}_relay"] = is_active
            #self.logger.debug(f"{status} relay: GPIO state = {gpio_state}, Active state = {active_state}, Is active = {is_active}")
        return states

    def _add_telemetry_to_queue(self, telemetry: Dict[str, bool]):
        #self.logger.info(f'Relay states: {telemetry}')
        self.queue.put((PublishType.TELEMETRY, telemetry))

    def cleanup(self):
        try:
            self._cleanup_gpio()
            self.logger.info("GPIO cleanup completed for RelayMonitor")
        except Exception as e:
            self.logger.error(f"Error during GPIO cleanup in RelayMonitor: {e}")

    def _cleanup_gpio(self):
        GPIO.cleanup(list(self.relay_pins.values()))