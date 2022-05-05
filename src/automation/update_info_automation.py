import asyncio
import glob
import os
import shutil
import tkinter.messagebox as tkmb
from tkinter import Tk, simpledialog

from telethon import TelegramClient

from src.utils.logger import logger

from .abstract_automation import AbstractAutomation
from .exceptions_automation import ClientNotAuthorizedException, NoTelegramApiInfoFoundException
from .telethon_wrapper import TelethonWrapper


class UpdateInfo(AbstractAutomation):
    def __init__(
        self,
        client_mode: int,
        max_session: str,
        code_required: int,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.client_mode = client_mode
        self.code_required = code_required
        self.names_to_change = self.read_file_with_property("name_change")
        self.username_to_change = self.read_file_with_property("username_change")
        self.abouts = self.read_file_with_property("about")
        self.apis = self.read_file_with_property("api")
        self.profile_pics_path = "profile_pics"
        self._list_of_profile_pics_path = os.listdir(self.profile_pics_path)
        self.sessions = self.read_all_sessions()
        if self.client_mode == 1 and int(max_session):
            self.max_sessions = int(max_session)
            self.sessions = self.sessions[: self.max_sessions]

        if self.client_mode == 0:
            self.phones = self.load_phone_numbers()

    def read_all_sessions(self):
        sessions = glob.glob(r"sessions\*.session")
        return sessions

    def load_phone_numbers(self):
        try:
            with open(r"sessions\phones.txt", "r") as phone_file:
                phone_list = phone_file.read().split("\n")
                logger.info(f"Got {str(len(phone_list))} phone number")
                return phone_list
        except Exception as e:
            raise Exception(f"Cannot load phone numbers from phones.txt due to : {str(e)}")

    def generate_username(self, name: str):
        numeric_elems = [elem for elem in name if elem.isnumeric()]
        numeric_part = str.join("", numeric_elems)
        name = name.replace("_", "")
        name = name.lower()
        char_elems = [elem for elem in name if not elem.isnumeric()]
        return str.join("", char_elems)[::-1] + str.join("", char_elems)[::-1][-1] + numeric_part

    def code_callback_manual(self):
        new_win = Tk()
        new_win.withdraw()

        answer = simpledialog.askinteger("Enter code", f"Enter the code {self.phone}.", parent=new_win, initialvalue=0)

        new_win.destroy()

        return answer

    def delete_unsuccessful_session(self, phone: str):
        if self.tw_instance and self.tw_instance.client:
            self.tw_instance.client.disconnect()
            if os.path.isfile(f"sessions\\{phone}.session"):
                os.remove(f"sessions\\{phone}.session")

    def move_current_session(self, client: TelegramClient):
        if client.is_connected():
            phone = client.get_me().phone
            client.disconnect()
            session = rf"sessions\+{phone}.session"
            session_filename = session.split("\\")[1]
            if os.path.exists(session):
                shutil.move(session, rf"used_sessions\{session_filename}")

    def update_info_session_based(self):
        for session in self.sessions:
            with self.pause_cond:
                while self.paused:
                    self.pause_cond.wait()
                if self.stopped:
                    self.running = False
                    break
                try:
                    self.phone = session.split("\\")[1].replace(".session", "")
                    logger.info(f"Starting updating info of number {self.phone}")

                    current_tg_api_id = None
                    current_tg_hash = None
                    if self.apis:
                        splitted_api_info = self.apis[0].split("-")
                        current_tg_api_id = splitted_api_info[0]
                        current_tg_hash = splitted_api_info[1]
                    else:
                        raise NoTelegramApiInfoFoundException("No telegram api info found.")

                    current_first_name = None
                    current_last_name = None
                    current_name = None
                    if self.names_to_change:
                        current_name = self.names_to_change[0]
                        current_first_name = current_name.split(" ")[0]
                        current_last_name = current_name.split(" ")[1]
                        logger.info(f"First name: {current_first_name} | Last name: {current_last_name}")

                    current_image = None
                    if self._list_of_profile_pics_path and self.profile_pics_path:
                        logger.info(f"Profile image will used: {self._list_of_profile_pics_path[0]}")
                        current_image = self.profile_pics_path + "\\" + self._list_of_profile_pics_path[0]

                    current_about = None
                    if self.abouts:
                        current_about = self.abouts[0]
                        logger.info(f"About info will set: {current_about}")

                    current_username = None
                    if self.username_to_change:
                        current_username = self.username_to_change[0]
                        current_username = self.generate_username(current_username)
                        logger.info(f"Username: {current_username}")

                    telegram_client = TelegramClient(
                        session=session,
                        api_id=current_tg_api_id,
                        api_hash=current_tg_hash,
                        base_logger=logger,
                    )

                    self.tw_instance = TelethonWrapper(client=telegram_client, phone=self.phone)
                    if not self.tw_instance.check_client_authorized(code_callback=None):
                        self.delete_unsuccessful_session(self.phone)
                        raise ClientNotAuthorizedException("Client not authorized")

                    self.tw_instance.client.loop.run_until_complete(self.tw_instance.set_other_user_settings())
                    self.tw_instance.client.loop.run_until_complete(
                        self.tw_instance.set_other_user_settings(
                            username=current_username,
                            profile_image_path=current_image,
                            about=current_about[:70]
                            if current_about and len(current_about) > 70
                            else current_about
                            if current_about
                            else "",  # max char limit
                            first_name=current_first_name,
                            last_name=current_last_name,
                        )
                    )

                    self.move_current_session(self.tw_instance.client)

                    # Remove image
                    if current_image and self._list_of_profile_pics_path:
                        self.remove_current_picture(current_image)
                        del self._list_of_profile_pics_path[0]

                    # Remove about
                    if current_about and self.abouts:
                        self.abouts.remove(current_about)
                        self.write_list_to_file("about", self.abouts)

                    # Remove username
                    if current_username and self.username_to_change:
                        self.username_to_change.remove(self.username_to_change[0])
                        self.write_list_to_file("username_change", self.username_to_change)

                    # Remove name
                    if current_name and self.names_to_change:
                        self.names_to_change.remove(self.names_to_change[0])
                        self.write_list_to_file("name_change", self.names_to_change)

                except NoTelegramApiInfoFoundException as e:
                    tkmb.showerror("Error Occured", "No telegram api info found.")
                    raise e
                except Exception as e:
                    logger.info(f"Exception occured with {str(e)}")

    def update_info_phones_based(self):
        self.phones_copy = self.phones.copy()
        for phone in self.phones:
            with self.pause_cond:
                while self.paused:
                    self.pause_cond.wait()
                if self.stopped:
                    self.running = False
                    break
                try:
                    self.phone = phone
                    logger.info(f"Starting updating info of number {self.phone}")

                    current_tg_api_id = None
                    current_tg_hash = None
                    if self.apis:
                        splitted_api_info = self.apis[0].split("-")
                        current_tg_api_id = splitted_api_info[0]
                        current_tg_hash = splitted_api_info[1]
                    else:
                        raise NoTelegramApiInfoFoundException("No telegram api info found.")

                    current_first_name = None
                    current_last_name = None
                    current_name = None
                    if self.names_to_change:
                        current_name = self.names_to_change[0]
                        current_first_name = current_name.split(" ")[0]
                        current_last_name = current_name.split(" ")[1]
                        logger.info(f"First name: {current_first_name} | Last name: {current_last_name}")

                    current_image = None
                    if self._list_of_profile_pics_path and self.profile_pics_path:
                        logger.info(f"Profile image will used: {self._list_of_profile_pics_path[0]}")
                        current_image = self.profile_pics_path + "\\" + self._list_of_profile_pics_path[0]

                    current_about = None
                    if self.abouts:
                        current_about = self.abouts[0]
                        logger.info(f"About info will set: {current_about}")

                    current_username = None
                    if self.username_to_change:
                        current_username = self.username_to_change[0]
                        current_username = self.generate_username(current_username)
                        logger.info(f"Username: {current_username}")

                    telegram_client = TelegramClient(
                        session=rf"sessions\{self.phone}",
                        api_id=current_tg_api_id,
                        api_hash=current_tg_hash,
                        base_logger=logger,
                    )

                    self.tw_instance = TelethonWrapper(
                        client=telegram_client,
                        phone=self.phone,
                    )

                    if self.code_required:
                        if not self.tw_instance.check_client_authorized(code_callback=self.code_callback_manual):
                            raise ClientNotAuthorizedException("Client not authorized")
                    else:
                        if not self.tw_instance.check_client_authorized(code_callback=None):
                            raise ClientNotAuthorizedException("Client not authorized")

                    self.tw_instance.client.loop.run_until_complete(self.tw_instance.set_other_user_settings())
                    self.tw_instance.client.loop.run_until_complete(
                        self.tw_instance.set_other_user_settings(
                            username=current_username,
                            profile_image_path=current_image,
                            about=current_about[:70]
                            if current_about and len(current_about) > 70
                            else current_about
                            if current_about
                            else "",  # max char limit
                            first_name=current_first_name,
                            last_name=current_last_name,
                        )
                    )

                    self.move_current_session(self.tw_instance.client)

                    # Remove image
                    if current_image and self._list_of_profile_pics_path:
                        self.remove_current_picture(current_image)
                        del self._list_of_profile_pics_path[0]

                    # Remove about
                    if current_about and self.abouts:
                        self.abouts.remove(current_about)
                        self.write_list_to_file("about", self.abouts)

                    # Remove username
                    if current_username and self.username_to_change:
                        self.username_to_change.remove(current_username)
                        self.write_list_to_file("username_change", self.username_to_change)

                    # Remove name
                    if current_name and self.names_to_change:
                        self.names_to_change.remove(current_name)
                        self.write_list_to_file("name_change", self.names_to_change)

                    # Remove phones
                    self.phones_copy.remove(phone)
                    self.write_list_to_file_with_path(path="sessions", filename="phones", new_list=self.phones_copy)

                except NoTelegramApiInfoFoundException as e:
                    if self.tw_instance and self.tw_instance.client.is_connected():
                        self.tw_instance.client.disconnect()
                    tkmb.showerror("Error Occured", "No telegram api info found.")
                    raise e
                except Exception as e:
                    self.phones_copy.remove(phone)
                    self.write_list_to_file_with_path(path="sessions", filename="phones", new_list=self.phones_copy)
                    self.delete_unsuccessful_session(phone)

                    logger.info(f"Exception occured with {str(e)}")

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.running = True
        if not self.apis:
            tkmb.showerror("No Names Given", "There are no names given to process. Please fill names.txt file.")
        if self.client_mode:
            self.update_info_session_based()
        else:
            self.update_info_phones_based()
