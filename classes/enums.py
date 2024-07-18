from enum import Enum, auto

class PublishType(Enum):
    EVENTO = auto()
    REPORTE = auto()
    ESTADO = auto()
    PANEL = auto()

class SeverityLevel(Enum):
    NOTIFICACION = 1
    MEDIO = 2
    SEVERO = 6

class PanelModel(Enum):
    EDWARDS_IO1000 = 10001
    EDWARDS_EST3X = 10002
    NOTIFIER_NFS320 = 10003