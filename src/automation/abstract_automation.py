import abc
import glob
import os
import shutil
import threading
from typing import List

import socks
from telethon import TelegramClient

from src.utils.logger import logger

from .telethon_wrapper import TelethonWrapper


class AbstractAutomation(threading.Thread, abc.ABC):
    def __init__(self):
        super(AbstractAutomation, self).__init__()
        self.paused = False
        self.stopped = False
        self.running = False
        self.pause_cond = threading.Condition(threading.Lock())
        self._stop_event = threading.Event()
        self._prev_url = None

    def read_file_with_property(self, path: str, filename: str):
        if os.path.exists(path + "\\" + filename + ".txt"):
            with open(path + "\\" + filename + ".txt", "r", encoding="utf-8", errors="ignore") as fh:
                return [line.replace("\n", "") for line in fh.readlines()]
        else:
            logger.exception(f"Please put {filename} file under data folder.")
            raise Exception("No file detected!")

    def write_list_to_file(self, path: str, filename: str, new_list: List[str]):
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
        proxy_dict["rdns"] = True

        return proxy_dict

    def remove_current_picture(self, path_of_file: str):
        try:
            os.remove(path_of_file)
        except Exception:
            logger.exception(f"Cannot remove profile picture under path: {path_of_file}")

    def read_all_sessions(self, path: str):
        sessions = glob.glob(rf"{path}\sessions\*.session")
        return sessions

    def delete_unsuccessful_session(self, tw_instance: TelethonWrapper, path, phone):
        if tw_instance and tw_instance.client.is_connected():
            tw_instance.client.disconnect()
        if phone:
            if os.path.isfile(f"{path}\\sessions\\{phone}.session"):
                os.remove(f"{path}\\sessions\\{phone}.session")

    def move_current_session(self, path: str, client: TelegramClient):
        if client.is_connected():
            phone = client.get_me().phone
            client.disconnect()

            session = rf"{path}\sessions\+{phone}.session"
            if not os.path.exists(session):
                session = rf"{path}\sessions\{phone}.session"
            session_filename = session.split("\\")[-1]
            if os.path.exists(session):
                shutil.move(session, rf"{path}\used_sessions\{session_filename}")
            else:
                raise Exception(f"Session file not found {session}. So it cannot be moved.")

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
