import configparser
import logging
import os
import platform
import threading
import tkinter as tk
from tkinter import ttk

from src.ui.body import BodyTelegramBot
from src.ui.header import Header
from src.utils.logger import ConsoleUi, logger


class TelegramAccountCreator(tk.Tk):
    def __init__(self, *args, **kwargs):
        self.initial_checks()
        tk.Tk.__init__(self, *args, **kwargs)
        logging.basicConfig(level=logging.INFO)
        self.rowconfigure([1, 2], weight=1)  # type: ignore
        self.columnconfigure(0, weight=1, uniform="fred")
        self.resizable(False, False)
        self.geometry("700x450")
        self._current_running_tab = None
        style_cbox = ttk.Style()
        style_cbox.map("BW.TCombobox", fieldbackground=[("readonly", "white")])
        current_os = platform.system().lower()
        if current_os == "linux":
            icon = tk.PhotoImage(file="src/icons/linux/telegram.png")
            self.call("wm", "iconphoto", self._w, icon)  # type: ignore
        elif platform.system().lower() == "windows":
            self.iconbitmap(default=f"src/icons/{current_os}/telegram.ico")
        else:
            print("Not recognized platform. No icon will be set.")
            raise Exception("Not recognized platform.")

        self.title("Telegram Auto Account v0.4.2 (telethon only)")
        self.header = Header(parent=self)
        self.header.grid(row=0, column=0, sticky="w")

        self.ui_body = BodyTelegramBot(self)
        self.ui_body.grid(row=1, column=0, sticky="nsew")

        self.header.btn_run.configure(command=self.run)
        self.header.btn_pause.configure(command=self.pause)
        self.header.btn_stop.configure(command=self.stop)

        console = ConsoleUi(self)
        console.grid(row=2, column=0, sticky="nsew")
        logger.info("App starting")

    def initial_checks(self):
        if not os.path.exists("data"):
            os.mkdir("data")

        if not os.path.exists("profile_pics"):
            os.mkdir("profile_pics")

        if not os.path.exists(r"data\names.txt"):
            with open(r"data\names.txt", "a") as fh:
                fh.close()

        if not os.path.exists(r"data\devices.txt"):
            with open(r"data\devices.txt", "a") as fh:
                fh.close()

        if not os.path.exists(r"data\about.txt"):
            with open(r"data\about.txt", "a") as fh:
                fh.close()

        if not os.path.exists(r"data\passwords.txt"):
            with open(r"data\passwords.txt", "a") as fh:
                fh.close()

        if not os.path.exists(r"data\proxies.txt"):
            with open(r"data\proxies.txt", "a") as fh:
                fh.close()

        if not os.path.exists(r"data\api.txt"):
            with open(r"data\api.txt", "a") as fh:
                fh.close()

        if not os.path.exists(r"sim_provider_config.ini"):
            with open(r"sim_provider_config.ini", "w") as fh:
                config_file = configparser.ConfigParser()
                config_file.add_section("SIMProviderAPIKeys")
                config_file.set("SIMProviderAPIKeys", "5sim_api_key", "")
                config_file.set("SIMProviderAPIKeys", "sms_activate_api_key", "")
                config_file.write(fh)

        if not os.path.exists("sessions"):
            os.mkdir("sessions")

    def run(self):

        if not self._current_running_tab:
            self._current_running_tab = self.ui_body
            self._current_running_tab.run()
            if self._current_running_tab.frame_thread:
                self.reset_thread = threading.Thread(
                    target=self.reset_status_after_complete, args=[self._current_running_tab.frame_thread]
                )
                self.reset_thread.start()
            else:
                self._current_running_tab = None
                return

            self.header.btn_run["state"] = "disabled"
            self.header.btn_pause["state"] = "normal"
            self.header.btn_stop["state"] = "enabled"
            self.change_status_of_frame(tk.DISABLED)
            self.header.btn_run["text"] = "Resume"
        else:
            self._current_running_tab.run()

    def pause(self):
        if self._current_running_tab:
            self.header.btn_run["state"] = "normal"
            self.header.btn_pause["state"] = "disabled"
            self.header.btn_stop["state"] = "disabled"
            self._current_running_tab.pause()

    def stop(self):
        if self._current_running_tab:
            self._current_running_tab.stop()

    def reset_status_after_complete(self, thread: threading.Thread):
        thread.join()
        self.header.btn_run["state"] = "normal"
        self.header.btn_pause["state"] = "disabled"
        self.header.btn_stop["state"] = "disabled"
        self.change_status_of_frame(tk.NORMAL)
        self._current_running_tab = None
        self.header.btn_run["text"] = "Run"

    @property
    def get_current_running_tab(self):
        return self._current_running_tab

    def change_status_of_frame(self, state):
        for child in self._current_running_tab.winfo_children():  # type: ignore
            child.configure(state=state)  # type: ignore

    def on_closing(self):
        if self._current_running_tab:
            if (
                self._current_running_tab.frame_thread.tw_instance
                and self._current_running_tab.frame_thread.tw_instance.client
            ):
                self._current_running_tab.frame_thread.tw_instance.client.loop.close()
            self._current_running_tab.frame_thread.stop()
            self._current_running_tab.frame_thread.join()
            self.reset_thread.join()
            self.quit()
        else:
            self.quit()


# def main():
#     nft_app = TelegramAccountCreator()
#     nft_app.protocol("WM_DELETE_WINDOW", on_closing)
#     nft_app.mainloop()


if __name__ == "__main__":
    nft_app = TelegramAccountCreator()
    nft_app.protocol("WM_DELETE_WINDOW", nft_app.on_closing)
    nft_app.mainloop()
