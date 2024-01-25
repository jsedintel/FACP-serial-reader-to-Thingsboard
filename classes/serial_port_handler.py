import serial
from classes.utils import SafeQueue
from typing import Tuple
from classes.enums import PublishType
from collections import OrderedDict
import time
import json
import logging


class SerialPortHandler:
    def __init__(self, config: dict, eventSeverityLevels: dict, queue: SafeQueue):
        self.config = config
        self.queue = queue
        self.eventSeverityLevels = eventSeverityLevels
        self.ser = None
        self.logger = logging.getLogger(__name__)
        self.report_delimiter = ""
        self.max_report_delimiter_count = -1

    def init_serial_port(self) -> None:
        # Inicializa el puerto serial
        self.ser = serial.Serial()
        self.ser.port=self.config["serial"]["puerto"]
        self.ser.baudrate=self.config["serial"]["baudrate"]
        self.ser.bytesize=self.config["serial"]["bytesize"]
        self.ser.parity=self.config["serial"]["parity"]
        self.ser.stopbits=self.config["serial"]["stopbits"]
        self.ser.xonxoff=self.config["serial"]["xonxoff"]
        self.ser.timeout=self.config["serial"]["timeout"]

    def open_serial_port(self) -> None:
        if self.ser is None:
                self.init_serial_port()
                #self.logger.debug("Se inicializa los datos del serial")
        try:
            if not self.ser.is_open:
                #self.logger.debug("Se intenta abrir el puerto serial")
                self.ser.open()
            message = OrderedDict([
                ("ID_Cliente", self.config["cliente"]["id_cliente"]),
                ("ID_Panel", self.config["cliente"]["id_panel"]),
                ("Modelo_Panel", self.config["cliente"]["modelo_panel"]),
                ("Mensaje", "Conectado"),
                ("Tipo", "Estado")
            ])
            self.queue.put((PublishType.ESTADO, json.dumps(message)))
            self.logger.debug("Serial conectado")
                
        except Exception as e:
            #self.logger.exception("Ocurrió un error inesperado abriendo el puerto especificado.")
            raise serial.SerialException(str(e))
        
    def publish_parsed_report(self, buffer: dict) -> None:
        parsed_data = self.parse_string_report(buffer)
        if parsed_data is not None:
            #self.logger.debug("Reporte parseado")
            self.queue.put((PublishType.REPORTE, json.dumps(parsed_data)))
        else:
            self.logger.warning("Reporte en blanco parseado")

    def publish_parsed_event(self, buffer: str) -> None:
        parsed_data = self.parse_string_event(buffer)
        if parsed_data is not None:
            #self.logger.debug("Evento parseado")
            self.queue.put((PublishType.EVENTO, json.dumps(parsed_data)))
        else:
            self.logger.debug("La información parseada para el evento está vacía, saltanto publicar a MQTT.")

    def attempt_reconnection(self) -> None:
        while True:
            try:
                self.open_serial_port()
                if self.ser.is_open:
                    break
            except Exception as e:
                #self.logger.debug("Intentando reconectar serial...")
                message = OrderedDict([
                ("ID_Cliente", self.config["cliente"]["id_cliente"]),
                ("ID_Panel", self.config["cliente"]["id_panel"]),
                ("Modelo_Panel", self.config["cliente"]["modelo_panel"]),
                ("ID_Modelo_Panel", self.config['cliente']['id_modelo_panel']),
                ("Mensaje", "Fallo serial"),
                ("Tipo", "Estado")
                ])
                self.queue.put((PublishType.ESTADO, json.dumps(message)))
                time.sleep(60)
                #self.logger.exception("Error encontrado intentando abrir el serial: ")

    def close_serial_port(self) -> None:
        if self.ser and self.ser.is_open:
            self.ser.close()
            #self.logger.debug("Puerto serial cerrado.")

    def process_incoming_data(self) -> None:
        buffer = ""
        report_count = 0

        try:
            while True:
                if self.ser.in_waiting > 0:
                    incoming_line = self.ser.readline().decode('utf-8').strip()

                    if not incoming_line:
                        if_eof = self.handle_empty_line(buffer, report_count)
                        if if_eof:
                            buffer = ""
                            report_count = 0
                    else:
                        buffer, report_count = self.handle_data_line(incoming_line, buffer, report_count)
                else:
                    time.sleep(0.1)
        except (serial.SerialException, serial.SerialTimeoutException) as e:
            raise serial.Exception(str(e))
        except (TypeError, UnicodeDecodeError) as e:
            if buffer != "":
                if report_count > 0:
                    self.publish_parsed_report(buffer)
                else:
                    self.publish_parsed_event(buffer)
            raise TypeError(str(e))
        except Exception as e:
            #self.logger.exception("Fallo inesperado ocurrido: ")
            raise Exception(str(e))

    def handle_data_line(self, incoming_line: str, buffer: str, report_count: int) -> Tuple[str, int]:
        if self.report_delimiter in incoming_line:
            report_count += 1
        buffer += incoming_line + "\n"
        return buffer, report_count

    def handle_empty_line(self, buffer: str, report_count: int) -> bool:
        if report_count == self.max_report_delimiter_count and buffer.strip():
            self.publish_parsed_report(buffer)
            return True
        elif report_count == 0 and buffer.strip():
            self.publish_parsed_event(buffer)
            return True
        else:
            return False

    def parse_string_event(self,event: str) -> OrderedDict:
        "Se implementa el parseo de los eventos"
        self.logger.error("La funcion 'parse_string_event' se debe implementar!")
        pass

    def parse_string_report(self, report: str) -> OrderedDict:
        "Se implementa el parseo de los eventos"
        self.logger.error("La funcion 'parse_string_report' se debe implementar!")
        pass

    def listening_to_serial(self) -> None:
        while True:
            try:
                self.open_serial_port()
                #logger.debug("Se abrio el puerto exitosamente")
                self.process_incoming_data()
            except (serial.SerialException, serial.SerialTimeoutException) as e:
                self.logger.error("Perdida de la conexion serial.")
                self.attempt_reconnection()
            except (TypeError, UnicodeDecodeError) as e:
                self.logger.error("Error ocurrido, caracter extranio encontrado. Reiniciando el serial")
                self.ser = None
            except Exception as e:
                self.close_serial_port()
                self.logger.error(f"Ha ocurrido un error inesperado: {str(e)}")
                time.sleep(1)