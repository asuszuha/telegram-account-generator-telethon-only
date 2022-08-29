import asyncio
import glob
import os
import shutil
import time
import tkinter.messagebox as tkmb
from sys import exit
from time import sleep
from tkinter import Tk, simpledialog
from typing import List

from telethon.sync import TelegramClient
from telethon.tl.functions.channels import GetParticipantsRequest, InviteToChannelRequest, JoinChannelRequest
from telethon.tl.functions.messages import CheckChatInviteRequest, GetDialogsRequest, ImportChatInviteRequest
from telethon.tl.types import ChannelParticipantsSearch, InputChannel, InputPeerChannel, InputPeerEmpty

from src.automation.telethon_wrapper import PossibleProxyIssueException, TelethonWrapper
from src.utils.logger import logger
from src.utils.paths import RETRIEVE_MANUAL_DIR

from .abstract_automation import AbstractAutomation
from .exceptions_automation import (
    CannotOpenLoadPhoneNumbers,
    ClientNotAuthorizedException,
    NoTelegramApiInfoFoundException,
)


class RetrieveCode(AbstractAutomation):
    def __init__(
        self,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.apis = self.read_file_with_property(path=RETRIEVE_MANUAL_DIR, filename="api")
        self.phones = self.load_phone_numbers()

    def load_phone_numbers(self):
        try:
            with open(rf"{RETRIEVE_MANUAL_DIR}\sessions\phones.txt", "r") as phone_file:
                phone_list = phone_file.read().split("\n")
                logger.info(f"Got {str(len(phone_list))} phone number")
                return phone_list
        except Exception as e:
            raise CannotOpenLoadPhoneNumbers(f"Cannot load phone numbers from phones.txt due to : {str(e)}")

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.phones_copy = self.phones.copy()
        self.running = True
        if not self.phones:
            tkmb.showerror("No Names Given", "There are no names given to process. Please fill names.txt file.")

        for phone in self.phones:
            with self.pause_cond:
                while self.paused:
                    self.pause_cond.wait()
                try:
                    if self.stopped:
                        if self.tw_instance and self.tw_instance.client:
                            self.tw_instance.client.loop.stop()
                        self.running = False
                        break

                    current_tg_api_id = None
                    current_tg_hash = None
                    if self.apis:
                        splitted_api_info = self.apis[0].split("-")
                        current_tg_api_id = splitted_api_info[0]
                        current_tg_hash = splitted_api_info[1]
                    else:
                        raise NoTelegramApiInfoFoundException("No telegram api info found.")

                    telegram_client = TelegramClient(
                        rf"{RETRIEVE_MANUAL_DIR}\sessions\{phone}",
                        api_id=current_tg_api_id,
                        api_hash=current_tg_hash,
                        base_logger=logger,
                    )

                    self.tw_instance = TelethonWrapper(client=telegram_client, phone=phone)
                    code = self.tw_instance.retrieve_code()
                    self.tw_instance.client.disconnect()

                    success = True
                    logger.info(f"Code retrieved {code}.")

                except NoTelegramApiInfoFoundException:
                    tkmb.showerror("Error Occured", "No telegram api info found.")
                    break
                except Exception as e:
                    logger.info(f"Exception occured with {str(e)}")
