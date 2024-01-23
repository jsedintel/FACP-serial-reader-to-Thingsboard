#Panel de alarma de incendios Edwards IO 1000
from collections import OrderedDict
from datetime import datetime
from numpy import random
from classes.serial_port_handler import SerialPortHandler
from classes.utils import SafeQueue


class SpecificSerialHandler(SerialPortHandler):
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

        # Create an ordered dictionary with fields in the desired order
        event_data = OrderedDict([
            ("ID_Cliente", self.config["cliente"]["id_cliente"]),
            ("ID_Panel", self.config["cliente"]["id_facp"]),
            ("Modelo_Panel", self.config["cliente"]["modelo_panel"]),
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

        # Create an ordered dictionary with fields in the desired order
        report_data = OrderedDict([
            ("ID_Cliente", self.config["cliente"]["id_cliente"]),
            ("ID_Panel", self.config["cliente"]["id_facp"]),
            ("Modelo_Panel", self.config["cliente"]["modelo_panel"]),
            ("Mensaje", report),
            ("Tipo", "Reporte"),
            ("Fecha_SBC", datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
            ("Fecha_Panel", Fecha_Panel),
        ])

        return report_data