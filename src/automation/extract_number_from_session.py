import asyncio
import tkinter.messagebox as tkmb

from telethon import TelegramClient

from src.utils.logger import logger
from src.utils.paths import NUMBER_EXTRACT_FROM_SESSIONS_DIR

from .abstract_automation import AbstractAutomation
from .exceptions_automation import (
    ClientNotAuthorizedException,
    NoTelegramApiInfoFoundAddUserException,
    PhoneNumberAndFileNameDifferentException,
)
from .telethon_wrapper import TelethonWrapper


class ExtractNumberFromSessions(AbstractAutomation):
    def __init__(
        self,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.apis = self.read_file_with_property(path=NUMBER_EXTRACT_FROM_SESSIONS_DIR, filename="api")
        self.sessions = self.read_all_sessions(path=NUMBER_EXTRACT_FROM_SESSIONS_DIR)
        self.phones = []

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.running = True
        for session in self.sessions:
            with self.pause_cond:
                while self.paused:
                    self.pause_cond.wait()

                if self.stopped:
                    if self.tw_instance and self.tw_instance.client:
                        self.tw_instance.client.loop.stop()
                    self.running = False
                    break

                try:
                    self.tw_instance = None
                    self.phone = session.split("\\")[-1].replace(".session", "")
                    current_tg_api_id = None
                    current_tg_hash = None
                    if self.apis:
                        splitted_api_info = self.apis[0].split("-")
                        current_tg_api_id = splitted_api_info[0]
                        current_tg_hash = splitted_api_info[1]
                    else:
                        raise NoTelegramApiInfoFoundAddUserException("No telegram api info found.")

                    logger.info(f"API_ID: {current_tg_api_id} | API_HASH: {current_tg_hash} Phone: {self.phone}")

                    telegram_client = TelegramClient(
                        session=session,
                        api_id=current_tg_api_id,
                        api_hash=current_tg_hash,
                        # base_logger=logger,
                    )
                    self.tw_instance = TelethonWrapper(
                        client=telegram_client,
                        phone=self.phone,
                    )

                    if not self.tw_instance.check_client_authorized():
                        self.delete_unsuccessful_session(
                            tw_instance=self.tw_instance, path=NUMBER_EXTRACT_FROM_SESSIONS_DIR, phone=self.phone
                        )
                        raise ClientNotAuthorizedException("Client not authorized")

                    if self.phone.replace("+", "") != self.tw_instance.client.get_me().phone:
                        logger.exception(
                            f"Phone number: {self.tw_instance.client.get_me().phone} | Filename: {self.phone}.session"
                        )
                        raise PhoneNumberAndFileNameDifferentException("Phone number and filename is different.")

                    self.phones.append(self.phone)

                    # Write phone
                    self.write_list_to_file(
                        path=rf"{NUMBER_EXTRACT_FROM_SESSIONS_DIR}\sessions",
                        filename="phones",
                        new_list=self.phones,
                    )

                    # Remove api
                    self.apis.remove(self.apis[0])
                    self.write_list_to_file(path=NUMBER_EXTRACT_FROM_SESSIONS_DIR, filename="api", new_list=self.apis)

                    self.move_current_session(path=NUMBER_EXTRACT_FROM_SESSIONS_DIR, client=self.tw_instance.client)

                    if self.tw_instance.client.is_connected():
                        self.tw_instance.client.disconnect()

                except NoTelegramApiInfoFoundAddUserException as e:
                    tkmb.showerror("Error Occured", "No telegram api info found.")
                    raise e
                except Exception as e:
                    self.delete_unsuccessful_session(
                        tw_instance=self.tw_instance, path=NUMBER_EXTRACT_FROM_SESSIONS_DIR, phone=self.phone
                    )
                    logger.exception(f"Exception occured with {str(e)}")
