import RPi.GPIO as GPIO
import threading
from typing import Dict
from utils.queue_operations import SafeQueue
from classes.enums import PublishType
import json
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
        self.setup_gpio()
        self.publish_interval = config.relay_monitor.publish_interval

    def setup_gpio(self):
        GPIO.setmode(GPIO.BCM)
        for pin in self.relay_pins.values():
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def monitor_relays(self, shutdown_flag: threading.Event):
        while not shutdown_flag.is_set():
            telemetry = {}
            for status, pin in self.relay_pins.items():
                current_state = GPIO.input(pin)
                telemetry[status.lower() + '_relay'] = 1 if current_state == 0 else 0
            
            self.add_telemetry_to_queue(telemetry)
            
            if shutdown_flag.wait(self.publish_interval):
                break

    def add_telemetry_to_queue(self, telemetry: Dict[str, int]):
        self.queue.put((PublishType.TELEMETRY, json.dumps(telemetry)))

    def cleanup(self):
        if self.is_raspberry_pi and self.GPIO:
            try:
                self.GPIO.cleanup(list(self.relay_pins.values()))
            except Exception as e:
                self.logger.error(f"Error during GPIO cleanup: {e}")