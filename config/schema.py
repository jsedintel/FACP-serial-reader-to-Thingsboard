from pydantic import BaseModel

class ThingsboardConfig(BaseModel):
    device_token: str
    host: str
    port: int

class SerialConfig(BaseModel):
    puerto: str
    baudrate: int
    bytesize: int
    parity: str
    stopbits: int
    xonxoff: bool
    timeout: int

class ClientConfig(BaseModel):
    RPi: str
    id_panel: str
    modelo_panel: str
    id_modelo_panel: int

class RelayConfig(BaseModel):
    pin: int
    high_time: int
    low_time: int
    publish_interval: int

class RelayMonitorConfig(BaseModel):
    alarm_pin: int
    trouble_pin: int
    supervision_pin: int
    publish_interval: int

class TestingConfig(BaseModel):
    use_mock_gpio: bool

class ConfigSchema(BaseModel):
    thingsboard: ThingsboardConfig
    serial: SerialConfig
    cliente: ClientConfig
    relay: RelayConfig
    relay_monitor: RelayMonitorConfig
    testing: TestingConfig