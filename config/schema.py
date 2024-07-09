from pydantic import BaseModel

class MqttConfig(BaseModel):
    usuario: str
    contrasena: str
    url: str
    puerto: int

class SerialConfig(BaseModel):
    puerto: str
    baudrate: int
    bytesize: int
    parity: str
    stopbits: int
    xonxoff: bool
    timeout: int

class Coordinates(BaseModel):
    latitud: float
    longitud: float

class ClientConfig(BaseModel):
    id_cliente: str
    id_panel: int
    modelo_panel: str
    id_modelo_panel: int
    coordenadas: Coordinates

class RelayConfig(BaseModel):
    pin: int
    high_time: int
    low_time: int

class ConfigSchema(BaseModel):
    mqtt: MqttConfig
    serial: SerialConfig
    cliente: ClientConfig
    relay: RelayConfig