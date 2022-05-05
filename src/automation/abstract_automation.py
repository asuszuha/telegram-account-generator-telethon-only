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
        if new_list:
            new_list[-1] = new_list[-1].replace("\n", "")  # last element no new line
        with open(f"data\\{filename}.txt", "w") as fh:
            fh.writelines(new_list)

    def write_list_to_file_with_path(self, path: str, filename: str, new_list: List[str]):
        new_list = [elem + "\n" for elem in new_list]  # type: ignore
        if new_list:
            new_list[-1] = new_list[-1].replace("\n", "")  # last element no new line
        with open(f"{path}\\{filename}.txt", "w") as fh:
            fh.writelines(new_list)

    def read_txt_proxy(self, proxy: str):
        splitted_line = proxy.split(":")
        proxy_dict = {}
        proxy_dict["addr"] = splitted_line[0]
        proxy_dict["port"] = int(splitted_line[1])
        proxy_dict["username"] = splitted_line[2]
        proxy_dict["password"] = splitted_line[3]
        proxy_dict["proxy_type"] = "socks5"

        return proxy_dict

    def remove_current_picture(self, path_of_file: str):
        try:
            os.remove(path_of_file)
        except Exception:
            logger.exception(f"Cannot remove profile picture under path: {path_of_file}")

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
