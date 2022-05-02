import abc
import os
import threading
from typing import List

from src.utils.logger import logger


class AbstractAutomation(threading.Thread, abc.ABC):
    def __init__(self):
        super(AbstractAutomation, self).__init__()
        self.paused = False
        self.stopped = False
        self.running = False
        self.pause_cond = threading.Condition(threading.Lock())
        self._stop_event = threading.Event()
        self._prev_url = None

    def read_file_with_property(self, filename: str):
        if os.path.exists(f"data\\{filename}.txt"):
            with open(f"data\\{filename}.txt", "r", encoding="utf-8") as fh:
                return [line.replace("\n", "") for line in fh.readlines()]
        else:
            logger.exception(f"Please put {filename} file under data folder.")
            raise Exception("No names file detected!")

    def write_list_to_file(self, filename: str, new_list: List[str]):
        new_list = [elem + "\n" for elem in new_list]  # type: ignore
        with open(f"data\\{filename}.txt", "w") as fh:
            fh.writelines(new_list)

    @abc.abstractmethod
    def run(self):
        # Example implementation
        self.running = True
        while True:
            with self.pause_cond:
                while self.paused:
                    self.pause_cond.wait()
                if self.stopped:
                    break

                # Add your loop here

    def pause(self):
        self.paused = True
        self.pause_cond.acquire()

    def resume(self):
        self.paused = False
        self.pause_cond.notify()
        self.pause_cond.release()

    def stop(self):
        self._stop_event.set()
        self.stopped = True
