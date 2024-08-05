import threading
from utils.file_operations import save_to_file, load_from_file
from typing import List, Any
import logging
from utils.queue_operations import SafeQueue

class QueueManager:
    def __init__(self, queue: SafeQueue, queue_file_path: str):
        self.queue = queue
        self.queue_file_path = queue_file_path

    def save_queue_periodically(self, shutdown_flag: threading.Event):
        while not shutdown_flag.is_set():
            self.save_queue()
            if shutdown_flag.wait(5):
                break

    def save_queue(self):
        save_to_file(list(self.queue.queue), self.queue_file_path)

    def load_from_file(self, file_path: str) -> None:
        with self.mutex:
            try:
                items: List[Any] = load_from_file(file_path)
                for item in items:
                    self.put(item)
            except FileNotFoundError:
                logging.warning(f"File {file_path} not found. Creating a new queue.")
            except EOFError:
                logging.debug("No pending events or reports")
            except (logging.UnpicklingError, AttributeError) as e:
                logging.error(f"Error unpickling queue data: {e}")
            except Exception as e:
                logging.error(f"Unexpected error loading queue: {e}")
                raise 