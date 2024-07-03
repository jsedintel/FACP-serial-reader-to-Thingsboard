import pickle
import queue
import logging

logger = logging.getLogger(__name__)

class SafeQueue(queue.Queue):
    def __init__(self, maxsize=0):
        super().__init__(maxsize)
        self.is_serial_connected = False
    def save_to_file(self, file_path):
        with self.mutex:
            with open(file_path, 'wb') as file:
                pickle.dump(list(self.queue), file)

    def load_from_file(self, file_path):
        with self.mutex:
            try:
                with open(file_path, 'rb') as file:
                    items = pickle.load(file)
                    for item in items:
                        self.put(item)
            except FileNotFoundError:
                logger.warning(f"Archivo {file_path} no encontrado. Creando una nueva cola.")
                self.queue = queue.Queue()
            except EOFError:
                logger.debug(f"No hay eventos o reportes pendientes")
            except Exception as e:
                logger.error(f"Error desconocido cargando la cola: {e}")