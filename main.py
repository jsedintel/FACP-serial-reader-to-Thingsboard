import yaml
import sys
import os
from typing import Optional, Callable
import threading
import pickle
import logging
import logging.config
import time
from classes.specific_serial_handler import *
from classes.mqtt_sender import MqttHandler
from classes.utils import SafeQueue
from classes.update_app import update_check_thread
import platform
import signal

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def setup_logging(config_path):
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logging.config.dictConfig(config)
        print(f"Logging configuration loaded from {config_path}")
    else:
        logging.basicConfig(level=logging.DEBUG,  # Changed from INFO to DEBUG
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            handlers=[
                                logging.StreamHandler(),
                                logging.FileHandler("app.log")
                            ])
        print(f"Logging configuration file not found at {config_path}. Using basic configuration.")
    
    # Ensure the root logger is set to DEBUG level
    logging.getLogger().setLevel(logging.DEBUG)

def is_platform_windows():
    return platform.system() == "Windows"

def is_platform_linux():
    return platform.system() == "Linux"

def close_program():
    if is_platform_windows():
        os._exit(1)
    if is_platform_linux():
        os.kill(os.getpid(), signal.SIGINT)

def save_queue_to_file(queue: SafeQueue, file_path: str) -> None:
    with queue.mutex:
        with open(file_path, 'wb') as file:
            pickle.dump(list(queue.queue), file)

def load_queue_from_file(file_path: str, logger: logging.Logger) -> SafeQueue:
    queue = SafeQueue()
    try:
        with open(file_path, 'rb') as file:
            items = pickle.load(file)
            for item in items:
                queue.put(item)
            return queue
    except FileNotFoundError:
        logger.warning(f"Archivo {file_path} no encontrado. Creando nuevo queue.")
        return SafeQueue()
    except EOFError:
        logger.debug(f"Cola cargada vacia. ")
        return SafeQueue()
    except Exception as e:
        logger.error(f"Error inesperado cargando el queue: {e}")
    return queue

def load_and_verify_yaml(file_name: str, verify_function: Callable[[dict], bool], logger: logging.Logger) -> Optional[dict]:
    data = {}
    try:
        with open(file_name, 'r') as yaml_file:
            data = yaml.safe_load(yaml_file)  
        missing_keys = verify_function(data)
        if missing_keys:
            logger.error(f"Error verificando el archivo: {file_name}. Faltan los siguientes valores: {missing_keys}")
            return None
        else:
            logger.debug(f"{file_name} cargado y verificado con éxito.")
            return data
    except yaml.YAMLError as e:
        logger.exception(f"Error al parsear YAML en {file_name}: {e}")
    except FileNotFoundError as e:
        logger.exception(f"El archivo {file_name} no se encontró: {e}")
    return None

def verify_config(config: dict) -> dict:
    required_structure = {
        "mqtt": {"usuario", "contrasena", "url", "puerto"},
        "serial": {"puerto", "baudrate", "bytesize", "parity", "stopbits", "xonxoff", "timeout"},
        "cliente": {"id_cliente", "id_panel", "modelo_panel", "id_modelo_panel", "coordenadas"}
    }

    missing_keys = {}

    for main_key, sub_keys in required_structure.items():
        if main_key not in config:
            missing_keys[main_key] = sub_keys
            continue

        missing_sub_keys = sub_keys - config[main_key].keys()
        if missing_sub_keys:
            missing_keys[main_key] = missing_sub_keys

    if "cliente" in config and "coordenadas" in config["cliente"]:
        coordenadas = config["cliente"]["coordenadas"]
        if not isinstance(coordenadas, dict) or "latitud" not in coordenadas or "longitud" not in coordenadas:
            missing_keys.setdefault("cliente", set()).add("coordenadas")
        else:
            latitud = coordenadas["latitud"]
            longitud = coordenadas["longitud"]
            if not isinstance(latitud, float) or not isinstance(longitud, float):
                missing_keys.setdefault("cliente", set()).add("coordenadas")

    return missing_keys

def verify_eventSeverityLevels(eventSeverityLevels: dict) -> dict:
    incorrect_entries = {}
    try:
        for FACP, events in eventSeverityLevels.items():
            if not isinstance(FACP, int):
                raise KeyError("Codigo del panel invalido")
            for event_id, severity_level in events.items():
                if not isinstance(severity_level, int) or not 0 <= severity_level <= 6:
                    incorrect_entries[event_id] = severity_level
    except Exception as e:
        incorrect_entries['Error en el formato del archivo'] = -1
        return incorrect_entries
    return incorrect_entries

def main():
    config_path = resource_path(os.path.join("config", "logging_config.yml"))
    setup_logging(config_path)
    
    logger = logging.getLogger(__name__)
    logger.info("Logging initialized")

    path = resource_path(os.path.join("config", "config.yml"))
    config = load_and_verify_yaml(path, verify_config, logger)
    if config is None:
        logger.error("Failed to load config.yml")
        sys.exit(1)

    path = resource_path(os.path.join("config", 'eventSeverityLevels.yml'))
    eventSeverityLevels = load_and_verify_yaml(path, verify_eventSeverityLevels, logger)
    if eventSeverityLevels is None:
        logger.error("Failed to load eventSeverityLevels.yml")
        sys.exit(2)
    
    momevents_queue = load_queue_from_file("queue.picke", logger)

    mqtt_handler = MqttHandler(config, momevents_queue)
    serial_handler = None

    if_eventSeverityList = config['cliente']['id_modelo_panel'] in eventSeverityLevels
    if not if_eventSeverityList:
        logger.error("No se encontró una lista de severidad de eventos asociada al modelo de panel especificado. Verifica el nombre ingresado y si el FACP está soportado.")
        close_program()

    try:
        id_modelo_panel = config['cliente']['id_modelo_panel']
        severity_list = eventSeverityLevels[id_modelo_panel]
    except Exception as e:
        logger.error("El modelo de panel especificado no fue encontrado. Verifica el nombre ingresado y si el fACP está soportado")
        close_program()

    match config['cliente']['id_modelo_panel']:
        case 10001:
            serial_handler = Edwards_iO1000(config, severity_list, momevents_queue)
        case 10002:
            serial_handler = Edwards_EST3x(config, severity_list, momevents_queue)
        case 10003:
            serial_handler = Notifier_NFS320(config, severity_list, momevents_queue)
        case _:
            logger.error("El modelo de panel especificado no fue encontrado. Verifica el nombre ingresado y si el fACP está soportado")
            close_program()

    serial_thread = threading.Thread(target=serial_handler.listening_to_serial, args=())
    mqtt_thread = threading.Thread(target=mqtt_handler.listen_to_mqtt, args=())
    updates_thread = threading.Thread(target=update_check_thread, args=())
    
    serial_thread.daemon = True
    mqtt_thread.daemon = True
    updates_thread.daemon = True

    serial_thread.start()
    mqtt_thread.start()
    updates_thread.start()

    try:
        while True:
            if not serial_thread.is_alive() or not mqtt_thread.is_alive() or not updates_thread.is_alive():
                logger.error("One of the threads has died. Terminating the application.")
                close_program()

            time.sleep(5)
            save_queue_to_file(momevents_queue, "queue.picke")
    except KeyboardInterrupt:
        logger.info("Programa terminado por el usuario")
        close_program()

if __name__ == "__main__":
    main()