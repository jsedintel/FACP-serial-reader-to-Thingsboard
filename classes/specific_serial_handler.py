#Panel de alarma de incendios Edwards IO 1000
from collections import OrderedDict
from datetime import datetime
from numpy import random
from classes.serial_port_handler import SerialPortHandler
from classes.utils import SafeQueue

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
                if len(meta.split(':')) < 2:
                    self.logger.error(f"Evento inválido recibido: {event}")
                    return None
                key, value = meta.split(':')
                metadata = metadata + key.strip()+ ": " + value.strip() + " | "

            if len(lines) > 1:
                metadata = metadata + 'Additional_Metadata: ' + lines[1].strip()

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
        try:
            lines = list(filter(None, report.strip().split('\n')))
            if not lines:
                return None

            primary_data = lines[1:4]
            Fecha_Panel = ""

            if self.report_delimiter in primary_data[2]:
                time_date = primary_data[1].strip().split()
                Fecha_Panel = f"{time_date[0]} {time_date[1]}"
            else:
                time_date = primary_data[2].strip().split()
                Fecha_Panel = f"{time_date[0]} {time_date[1]}"

        except Exception as e:
            self.logger.exception("Ocurrió un error al parsear el reporte: " + report)
            return None

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

