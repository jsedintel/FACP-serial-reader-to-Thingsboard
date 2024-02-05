#Panel de alarma de incendios Edwards IO 1000
from collections import OrderedDict
from datetime import datetime
from numpy import random
from classes.serial_port_handler import SerialPortHandler
from classes.utils import SafeQueue
from typing import Tuple

class Specific_Serial_Handler_Template(SerialPortHandler):
    def __init__(self, config: dict, eventSeverityLevels: dict, queue: SafeQueue):
        super().__init__(config, eventSeverityLevels, queue)
        #Esto se considera, en caso de que exista un delimitador claro en cada reporte
        self.report_delimiter = "Set the delimiter"
        self.max_report_delimiter_count = 4 # configurarlo acorde a la cantidad de apariciones del delimitador por reporte 
        

    def parse_string_event(self,event: str) -> OrderedDict:
        '''
        #Extraer lo siguientes valores mediante el parseo del dato:
        ID_Event = ''
        Fecha_Panel = ''
        metadata = ''

        #El resultado que se tiene que generar:
        event_data = OrderedDict([
            ("ID_Cliente", self.config["cliente"]["id_cliente"]),
            ("ID_Panel", self.config["cliente"]["id_panel"]),
            ("Modelo_Panel", self.config["cliente"]["modelo_panel"]),
            ("ID_Modelo_Panel", self.config['cliente']['id_modelo_panel']),
            ("Mensaje", ID_Event),
            ("Tipo", "Evento"),
            ("Nivel_Severidad", self.eventSeverityLevels[ID_Event] if ID_Event in self.eventSeverityLevels else 999),
            ("Fecha_SBC", datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
            ("Fecha_Panel", Fecha_Panel),
            ("Metadata", metadata),
            ("uniq", random.rand())
        ])
        return event_data
        '''
        pass


    def parse_string_report(self, report: str) -> OrderedDict:
        '''
        #De ser posible, extraer la fecha del reporte, si no, no incluirla.
        Fecha_Panel = ''
        
        report_data = OrderedDict([
            ("ID_Cliente", self.config["cliente"]["id_cliente"]),
            ("ID_Panel", self.config["cliente"]["id_panel"]),
            ("Modelo_Panel", self.config["cliente"]["modelo_panel"]),
            ("ID_Modelo_Panel", self.config['cliente']['id_modelo_panel']),
            ("Mensaje", report),
            ("Tipo", "Reporte"),
            ("Fecha_SBC", datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
            ("Fecha_Panel", Fecha_Panel),
        ])
        
        return report_data
        '''
        pass

#Las siguientes funciones podrian o podrian no necesitar ser sobreescritas con respecto a la clase padre
'''
    def process_incoming_data(self) -> None:
        pass

    def handle_data_line(self, incoming_line: str, buffer: str, report_count: int) -> Tuple[str, int]:
        pass

    def handle_empty_line(self, buffer: str, report_count: int) -> bool:
        pass
'''

class Edwards_iO1000(SerialPortHandler):
    def __init__(self, config: dict, eventSeverityLevels: dict, queue: SafeQueue):
        super().__init__(config, eventSeverityLevels, queue)
        self.report_delimiter = "-----------------"
        self.max_report_delimiter_count = 4

    def parse_string_event(self,event: str) -> OrderedDict:
        metadata = ""
        try:
            lines = list(filter(None, event.strip().split('\n')))
            if not lines:
                self.logger.error(f"Evento inválido recibido: {event}")
                return None

            primary_data = lines[0].split('|')
            if len(primary_data) < 2:
                self.logger.error(f"Evento inválido recibido: {event}")
                return None

            ID_Event = primary_data[0].strip()
            time_date_metadata = primary_data[1].strip().split()
            Fecha_Panel = f"{time_date_metadata[0]} {time_date_metadata[1]}"

            for meta in time_date_metadata[2:]:
                metadata = metadata + meta.strip() + " | "

            if len(lines) > 1:
                for line in lines[1:]:
                    metadata = metadata + line.strip() + "\n"

        except Exception as e:
            self.logger.exception("Ocurrió un error al parsear el evento: " + event)
            return None

        event_data = OrderedDict([
            ("ID_Cliente", self.config["cliente"]["id_cliente"]),
            ("ID_Panel", self.config["cliente"]["id_panel"]),
            ("Modelo_Panel", self.config["cliente"]["modelo_panel"]),
            ("ID_Modelo_Panel", self.config['cliente']['id_modelo_panel']),
            ("Mensaje", ID_Event),
            ("Tipo", "Evento"),
            ("Nivel_Severidad", self.eventSeverityLevels[ID_Event] if ID_Event in self.eventSeverityLevels else 999),
            ("Fecha_SBC", datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
            ("Fecha_Panel", Fecha_Panel),
            ("Metadata", metadata),
            ("uniq", random.rand())
        ])
        return event_data

    def parse_string_report(self, report: str) -> OrderedDict:
        report_data = OrderedDict([
            ("ID_Cliente", self.config["cliente"]["id_cliente"]),
            ("ID_Panel", self.config["cliente"]["id_panel"]),
            ("Modelo_Panel", self.config["cliente"]["modelo_panel"]),
            ("ID_Modelo_Panel", self.config['cliente']['id_modelo_panel']),
            ("Mensaje", report),
            ("Tipo", "Reporte"),
            ("Fecha_SBC", datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        ])

        return report_data

class Edwards_EST3x(SerialPortHandler):
    def __init__(self, config: dict, eventSeverityLevels: dict, queue: SafeQueue):
        super().__init__(config, eventSeverityLevels, queue)
        #Esto se considera, en caso de que exista un delimitador claro en cada reporte
        self.report_delimiter = "-----------------" # configurarlo acorde al delimitador del reporte
        self.max_report_delimiter_count = 2 # configurarlo acorde a la cantidad de apariciones del delimitador por reporte
        self.end_report_delimiter = "**" # configurarlo acorde al delimitador del final del reporte

    def parse_string_event(self,event: str) -> OrderedDict:
        metadata = ""
        try:
            lines = list(filter(None, event.strip().split('\n')))
            if not lines:
                self.logger.error(f"Evento inválido recibido: {event}")
                return None

            primary_data = ""
            if lines[0][0] == "-":
                primary_data = lines[0][1:].split('-')
            else:
                primary_data = lines[0].split('::')
            if len(primary_data) < 2:
                self.logger.error(f"Evento inválido recibido: {event}")
                return None

            ID_Event = primary_data[0].strip()
            time_date_metadata = primary_data[1].strip().split()
            Fecha_Panel = f"{time_date_metadata[0]} {time_date_metadata[1]}"

            for meta in time_date_metadata[2:]:
                metadata = metadata + meta.strip() + " | "

            if len(lines) > 1:
                for line in lines[1:]:
                    metadata = metadata + line.strip() + "\n"

        except Exception as e:
            self.logger.exception("Ocurrió un error al parsear el evento: " + event)
            return None

        #El resultado que se tiene que generar:
        event_data = OrderedDict([
            ("ID_Cliente", self.config["cliente"]["id_cliente"]),
            ("ID_Panel", self.config["cliente"]["id_panel"]),
            ("Modelo_Panel", self.config["cliente"]["modelo_panel"]),
            ("ID_Modelo_Panel", self.config['cliente']['id_modelo_panel']),
            ("Mensaje", ID_Event),
            ("Tipo", "Evento"),
            ("Nivel_Severidad", self.eventSeverityLevels[ID_Event] if ID_Event in self.eventSeverityLevels else 999),
            ("Fecha_SBC", datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
            ("Fecha_Panel", Fecha_Panel),
            ("Metadata", metadata),
            ("uniq", random.rand())
        ])
        return event_data

    def parse_string_report(self, report: str) -> OrderedDict:
        
        report_data = OrderedDict([
            ("ID_Cliente", self.config["cliente"]["id_cliente"]),
            ("ID_Panel", self.config["cliente"]["id_panel"]),
            ("Modelo_Panel", self.config["cliente"]["modelo_panel"]),
            ("ID_Modelo_Panel", self.config['cliente']['id_modelo_panel']),
            ("Mensaje", report),
            ("Tipo", "Reporte"),
            ("Fecha_SBC", datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
        ])
        
        return report_data

    def check_last_line(self, string: str) -> bool:
        last_newline = string.rfind('\n', 0, string.rfind('\n'))
        last_line = string[last_newline+1:]
        return self.end_report_delimiter in last_line
    
    def handle_empty_line(self, buffer: str, report_count: int) -> bool:
        if report_count == 0 and buffer.strip() and self.check_last_line(buffer):
            #self.logger.debug("Reporte vacio parseado. Saltandolo.")
            return True
        if report_count == self.max_report_delimiter_count and buffer.strip() and self.check_last_line(buffer):
            #self.logger.debug("Reporte parseado.")
            self.publish_parsed_report(buffer)
            return True
        elif report_count == 0 and buffer.strip():
            #self.logger.debug("Evento parseado.")
            self.publish_parsed_event(buffer)
            return True
        else:
            return False

