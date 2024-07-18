import RPi.GPIO as GPIO
import threading
import time
from typing import Dict
from utils.queue_operations import SafeQueue
from classes.enums import PublishType
from collections import OrderedDict
import json
from datetime import datetime

class RelayMonitor:
    def __init__(self, config: Dict, queue: SafeQueue):
        self.config = config
        self.queue = queue
        self.relay_pins = {
            'ALARM': config['relay_monitor']['alarm_pin'],
            'TROUBLE': config['relay_monitor']['trouble_pin'],
            'SUPERVISION': config['relay_monitor']['supervision_pin']
        }
        self.relay_states = {pin: None for pin in self.relay_pins.values()}
        self.setup_gpio()

    def setup_gpio(self):
        GPIO.setmode(GPIO.BCM)
        for pin in self.relay_pins.values():
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def monitor_relays(self, shutdown_flag: threading.Event):
        self.send_initial_states()
        
        while not shutdown_flag.is_set():
            for status, pin in self.relay_pins.items():
                current_state = GPIO.input(pin)
                if self.relay_states[pin] != current_state:
                    self.relay_states[pin] = current_state
                    self.add_status_to_queue(status, current_state)
            time.sleep(5)

    def send_initial_states(self):
        for status, pin in self.relay_pins.items():
            initial_state = GPIO.input(pin)
            self.relay_states[pin] = initial_state
            self.add_status_to_queue(status, initial_state, is_initial=True)

    def add_status_to_queue(self, status: str, state: int, is_initial: bool = False):
        state_str = 'ACTIVE' if state == 0 else 'RESTORE'
        message = OrderedDict([
            ("ID_Cliente", self.config["cliente"]["id_cliente"]),
            ("ID_Panel", self.config["cliente"]["id_panel"]),
            ("Modelo_Panel", self.config["cliente"]["modelo_panel"]),
            ("ID_Modelo_Panel", self.config['cliente']['id_modelo_panel']),
            ("Mensaje", f"{status}_{state_str}"),
            ("Tipo", "Evento"),
            ("Nivel_Severidad", 1 if state == 0 else 6 if status == 'ALARM' else 2),
            ("Fecha_SBC", datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
            ("Metadata", f"{'Initial' if is_initial else 'Relay'} status: {status} is {state_str}"),
        ])
        self.queue.put((PublishType.PANEL, json.dumps(message)))

    def cleanup(self):
        GPIO.cleanup(list(self.relay_pins.values()))