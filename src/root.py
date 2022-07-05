import configparser
import logging
import os
import platform
import threading
import tkinter as tk
from tkinter import ttk

import src.GV as GV
from src.ui.abstract_frame_ui import AbstractTab
from src.ui.add_users_ui import AddTgUsers
from src.ui.add_users_ui_mt import AddTgUsersMt
from src.ui.auto_register import AutoRegisterTg
from src.ui.discord_register_acc import AutoRegisterDiscord
from src.ui.extract_numbers_from_session_ui import ExtracNumTgSession
from src.ui.group_chat_extractor_ui import GroupTgExtractor
from src.ui.header import Header
from src.ui.info_update_ui import UpdateTgInfo
from src.ui.multiple_username_remover_ui import MultiUsernameRemoveTg
from src.utils import paths
from src.utils.logger import ConsoleUi, logger


class TelegramAccountCreator(tk.Tk):
    def __init__(self, *args, **kwargs):
        self.initial_checks()
        tk.Tk.__init__(self, *args, **kwargs)
        logging.basicConfig(level=logging.INFO)
        self.rowconfigure([1, 2], weight=1)  # type: ignore
        self.columnconfigure(0, weight=1, uniform="fred")
        self.resizable(False, False)
        self.geometry("900x550")
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

        self.title("Telegram Auto Account v0.10.1 (telethon only)")
        self.tabs_in_main_page = ttk.Notebook(self)
        self.tabs_in_main_page.grid(row=1, column=0, sticky="nsew")
        self.header = Header(parent=self)
        self.header.grid(row=0, column=0, sticky="w")

        self.header.btn_run.configure(command=self.run)
        self.header.btn_pause.configure(command=self.pause)
        self.header.btn_stop.configure(command=self.stop)

        auto_register_tg = AutoRegisterTg(self.tabs_in_main_page)
        # add_tg_users = AddTgUsers(self.tabs_in_main_page)
        update_tg_users = UpdateTgInfo(self.tabs_in_main_page)
        extract_tg_num = ExtracNumTgSession(self.tabs_in_main_page)
        multi_user_tg_remove = MultiUsernameRemoveTg(self.tabs_in_main_page)
        add_tg_mt_users = AddTgUsersMt(self.tabs_in_main_page)
        chat_extractor_tg = GroupTgExtractor(self.tabs_in_main_page)

        # Discord
        # auto_register_dc = AutoRegisterDiscord(self.tabs_in_main_page)

        auto_register_tg.pack(fill=tk.BOTH, expand=True)
        self.tabs_in_main_page.add(auto_register_tg, text="Auto Register")
        # self.tabs_in_main_page.add(add_tg_users, text="Add Users")
        self.tabs_in_main_page.add(add_tg_mt_users, text="Add Users Multi Thread")
        self.tabs_in_main_page.add(update_tg_users, text="Update Users Info")
        self.tabs_in_main_page.add(extract_tg_num, text="Extract Number From Sessions")
        self.tabs_in_main_page.add(multi_user_tg_remove, text="Multiple Username Remover")
        self.tabs_in_main_page.add(chat_extractor_tg, text="Chat Extractor")

        # Discord
        # self.tabs_in_main_page.add(auto_register_dc, text="Auto Register Discord")

        console = ConsoleUi(self)
        console.grid(row=2, column=0, sticky="nsew")
        logger.info("App starting")

    def initial_checks(self):
        # Create for auto register and add user
        if not os.path.exists(paths.AUTO_REGISTER_PATH_DIR):
            os.mkdir(paths.AUTO_REGISTER_PATH_DIR)

        for folder_name in paths.AUTO_REGISTER_SUBFOLDERS:
            folder_name = paths.AUTO_REGISTER_PATH_DIR + "\\" + folder_name
            if not os.path.exists(folder_name):
                os.mkdir(folder_name)

        for file_name in paths.AUTO_REGISTER_FILES:
            file_name = paths.AUTO_REGISTER_PATH_DIR + "\\" + file_name
            if not os.path.exists(file_name):
                with open(file_name, "a") as fh:
                    fh.close()

        # Create for update info
        if not os.path.exists(paths.USER_INFO_DIR):
            os.mkdir(paths.USER_INFO_DIR)

        for folder_name in paths.USER_INFO_SUBFOLDERS:
            folder_name = paths.USER_INFO_DIR + "\\" + folder_name
            if not os.path.exists(folder_name):
                os.mkdir(folder_name)

        for file_name in paths.USER_INFO_FILES:
            file_name = paths.USER_INFO_DIR + "\\" + file_name
            if not os.path.exists(file_name):
                with open(file_name, "a") as fh:
                    fh.close()

        # Create for get extract numbers from sessions
        if not os.path.exists(paths.NUMBER_EXTRACT_FROM_SESSIONS_DIR):
            os.mkdir(paths.NUMBER_EXTRACT_FROM_SESSIONS_DIR)

        for folder_name in paths.NUMBER_EXTRACT_FROM_SESSIONS_SUBFOLDERS:
            folder_name = paths.NUMBER_EXTRACT_FROM_SESSIONS_DIR + "\\" + folder_name
            if not os.path.exists(folder_name):
                os.mkdir(folder_name)

        for file_name in paths.NUMBER_EXTRACT_FROM_SESSIONS_FILES:
            file_name = paths.NUMBER_EXTRACT_FROM_SESSIONS_DIR + "\\" + file_name

            if not os.path.exists(file_name):
                with open(file_name, "a") as fh:
                    fh.close()

        # Multi user remover
        if not os.path.exists(paths.MULTIPLE_USERNAME_REMOVER_DIR):
            os.mkdir(paths.MULTIPLE_USERNAME_REMOVER_DIR)

        for file_name in paths.MULTIPLE_USERNAME_REMOVER_FILES:
            file_name = paths.MULTIPLE_USERNAME_REMOVER_DIR + "\\" + file_name

            if not os.path.exists(file_name):
                with open(file_name, "a") as fh:
                    fh.close()

        # Group chat extractor
        if not os.path.exists(paths.GROUP_CHAT_EXTRACTOR_DIR):
            os.mkdir(paths.GROUP_CHAT_EXTRACTOR_DIR)

        for folder_name in paths.GROUP_CHAT_EXTRACTOR_SUBFOLDERS:
            folder_name = paths.GROUP_CHAT_EXTRACTOR_DIR + "\\" + folder_name
            if not os.path.exists(folder_name):
                os.mkdir(folder_name)

        for file_name in paths.GROUP_CHAT_EXTRACTOR_FILES:
            file_name = paths.GROUP_CHAT_EXTRACTOR_DIR + "\\" + file_name

            if not os.path.exists(file_name):
                with open(file_name, "a") as fh:
                    fh.close()

        # # Discord generate accounts
        # if not os.path.exists(paths.GENERATE_DISCORD_ACCOUNT_DIR):
        #     os.mkdir(paths.GENERATE_DISCORD_ACCOUNT_DIR)

        # for file_name in paths.GENERATE_DISCORD_ACCOUNT_FILES:
        #     file_name = paths.GENERATE_DISCORD_ACCOUNT_DIR + "\\" + file_name

        #     if not os.path.exists(file_name):
        #         with open(file_name, "a") as fh:
        #             fh.close()

        # for folder_name in paths.GENERATE_DISCORD_ACCOUNT_SUBFOLDERS:
        #     folder_name = paths.GENERATE_DISCORD_ACCOUNT_DIR + "\\" + folder_name
        #     if not os.path.exists(folder_name):
        #         os.mkdir(folder_name)

        # if not os.path.exists(paths.GENERATE_DISCORD_ACCOUNT_DIR + "\\api_config.ini"):
        #     with open(paths.GENERATE_DISCORD_ACCOUNT_DIR + "\\api_config.ini", "w") as fh:
        #         config_file = configparser.ConfigParser()
        #         config_file.add_section("APIKeysForProviders")
        #         config_file.set("APIKeysForProviders", "anti_captcha_api_key", "")
        #         config_file.set("APIKeysForProviders", "5sim_api_key", "")
        #         config_file.set("APIKeysForProviders", "sms_activate_api_key", "")
        #         config_file.set("APIKeysForProviders", "kopeechka_api_key", "")
        #         config_file.write(fh)

        if not os.path.exists(paths.AUTO_REGISTER_PATH_DIR + "\\sim_provider_config.ini"):
            with open(paths.AUTO_REGISTER_PATH_DIR + "\\sim_provider_config.ini", "w") as fh:
                config_file = configparser.ConfigParser()
                config_file.add_section("SIMProviderAPIKeys")
                config_file.set("SIMProviderAPIKeys", "5sim_api_key", "")
                config_file.set("SIMProviderAPIKeys", "sms_activate_api_key", "")
                config_file.write(fh)

    def run(self):
        GV.ProgramStatus = GV.PROGRAM_STATUS["RUNNING"]
        if not self._current_running_tab:
            self._current_running_tab = self.get_tab_selected_child(self.tabs_in_main_page)
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
            self.change_status_of_tabs(tk.DISABLED)
            self.header.btn_run["text"] = "Resume"
        else:
            self._current_running_tab.run()
            self.header.btn_run["state"] = "disabled"
            self.header.btn_pause["state"] = "normal"
            self.header.btn_stop["state"] = "enabled"

    def pause(self):
        GV.ProgramStatus = GV.PROGRAM_STATUS["IDLE"]
        if self._current_running_tab:
            self.header.btn_run["state"] = "normal"
            self.header.btn_pause["state"] = "disabled"
            self.header.btn_stop["state"] = "disabled"
            self._current_running_tab.pause()

    def stop(self):
        GV.ProgramStatus = GV.PROGRAM_STATUS["STOP"]
        if self._current_running_tab:
            self._current_running_tab.stop()

    def reset_status_after_complete(self, thread: threading.Thread):
        thread.join()
        self.header.btn_run["state"] = "normal"
        self.header.btn_pause["state"] = "disabled"
        self.header.btn_stop["state"] = "disabled"
        self.change_status_of_tabs(tk.NORMAL)
        self._current_running_tab = None
        self.header.btn_run["text"] = "Run"

    @property
    def get_current_running_tab(self):
        return self._current_running_tab

    def get_tab_selected_child(self, notebook: ttk.Notebook) -> AbstractTab:
        selected_tab = self.tabs_in_main_page.select()
        return [child for child in notebook.winfo_children() if child._w == selected_tab][0]  # type: ignore

    # def change_status_of_frame(self, state):
    #     for child in self._current_running_tab.winfo_children():  # type: ignore
    #         child.configure(state=state)  # type: ignore

    def change_status_of_tabs(self, state: str):
        for i, item in enumerate(self.tabs_in_main_page.tabs()):
            self.tabs_in_main_page.tab(item, state=state)

        self.tabs_in_main_page.select(self._current_running_tab._w)  # type: ignore

    def on_closing(self):
        if self._current_running_tab and self._current_running_tab.frame_thread:
            self._current_running_tab.frame_thread.stop()
            self._current_running_tab.frame_thread.join()
            self.reset_thread.join()
            self.quit()
        else:
            self.quit()
