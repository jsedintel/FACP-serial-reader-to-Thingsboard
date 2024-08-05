import logging
import time
import threading
from typing import List 

class ThreadManager:
    def __init__(self, shutdown_flag: threading.Event):
        self.threads: List[threading.Thread] = []
        self.shutdown_flag = shutdown_flag

    def start_threads(self, threads):
        self.threads = threads
        for thread in self.threads:
            thread.daemon = True
            thread.start()

    def stop_threads(self):
        self.shutdown_flag.set()
        for thread in self.threads:
            thread.join(timeout=20)
        
        # Force terminate any threads that didn't stop gracefully
        for thread in self.threads:
            if thread.is_alive():
                logging.warning(f"Thread {thread.name} did not stop gracefully. Attempting to terminate.")
                try:
                    if hasattr(thread, '_stop'):
                        thread._stop()
                except:
                    logging.error(f"Failed to forcefully terminate thread {thread.name}")

    def monitor_threads(self):
        while not self.shutdown_flag.is_set():
            if not all(thread.is_alive() for thread in self.threads):
                logging.error("One of the threads has died. Initiating graceful shutdown.")
                self.shutdown_flag.set()
                break
            time.sleep(5)