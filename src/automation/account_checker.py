import asyncio
import os
import shutil
import time
import tkinter.messagebox as tkmb
from datetime import datetime, timezone
from tkinter import Tk, simpledialog
from typing import List, Optional

from dateutil.relativedelta import relativedelta
from pydantic import BaseModel
from telethon.sync import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import CheckChatInviteRequest, GetDialogsRequest, ImportChatInviteRequest
from telethon.tl.types import ChannelParticipantBanned, InputPeerEmpty

import src.GV as GV
from src.automation.telethon_wrapper import TelethonWrapper
from src.utils.logger import logger
from src.utils.paths import ACCOUNT_CHECKER_DIR

from .abstract_automation import AbstractAutomation
from .exceptions_automation import (
    CannotOpenLoadPhoneNumbers,
    ClientNotAuthorizedException,
    NoTelegramApiInfoFoundAddUserException,
)


class BanInfo(BaseModel):
    banned: bool
    until_date: Optional[datetime]


class AccountChecker(AbstractAutomation):
    def __init__(
        self,
        client_mode: int,
        code_required: int,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.client_mode = client_mode
        self.spam_check = self.read_file_with_property(path=ACCOUNT_CHECKER_DIR, filename="spam_check_link")
        self.apis = self.read_file_with_property(path=ACCOUNT_CHECKER_DIR, filename="api")
        self.sessions = self.read_all_sessions(path=ACCOUNT_CHECKER_DIR)
        self.code_required = code_required

        if self.client_mode == 0:
            self.phones = self.load_phone_numbers()

    def load_phone_numbers(self):
        try:
            with open(rf"{ACCOUNT_CHECKER_DIR}\sessions\phones.txt", "r") as phone_file:
                phone_list = phone_file.read().split("\n")
                logger.info(f"Got {str(len(phone_list))} phone number")
                return phone_list
        except Exception as e:
            raise CannotOpenLoadPhoneNumbers(f"Cannot load phone numbers from phones.txt due to : {str(e)}")

    def code_callback_manual(self):
        new_win = Tk()
        new_win.withdraw()

        answer = simpledialog.askinteger("Enter code", f"Enter the code {self.phone}.", parent=new_win, initialvalue=0)

        new_win.destroy()

        return answer

    async def disconnect_all_clients(self, clients: List[TelegramClient]):
        for client in clients:
            try:
                if client.is_connected():
                    await client.disconnect()
            except Exception:
                pass

    def join_group(self, group, client: TelegramClient):
        cid = []
        ah = []
        if "/" in group:
            group_link = group.split("/")[-1]
            try:
                try:
                    updates = client(ImportChatInviteRequest(group_link))
                    cid.append(updates.chats[0].id)
                    ah.append(updates.chats[0].access_hash)
                except Exception as e:
                    chatinvite = client(CheckChatInviteRequest(group_link))
                    cid.append(chatinvite.chat.id)
                    ah.append(chatinvite.chat.access_hash)
                    print(e)
                    pass
            except Exception as e:
                logger.error(f"Error occured: {str(e)}")
        else:
            client_me = client.get_me()
            print(client_me.phone, "joined group", group)
            group_entity_scrapped = client.get_entity(group)
            updates = client(JoinChannelRequest(group_entity_scrapped))
            cid.append(updates.chats[0].id)
            ah.append(updates.chats[0].access_hash)
        res = [cid, ah]
        return res

    def get_clients_from_phones(self) -> TelegramClient:
        self.phones_copy = self.phones.copy()
        clients = []
        for phone in self.phones:
            with self.pause_cond:
                while self.paused:
                    self.pause_cond.wait()

                if self.stopped:
                    self.running = False
                    break

                try:
                    self.phone = phone
                    current_tg_api_id = None
                    current_tg_hash = None
                    if self.apis:
                        splitted_api_info = self.apis[0].split("-")
                        current_tg_api_id = splitted_api_info[0]
                        current_tg_hash = splitted_api_info[1]
                    else:
                        raise NoTelegramApiInfoFoundAddUserException("No telegram api info found.")
                    logger.info(f"API_ID: {current_tg_api_id} | API_HASH: {current_tg_hash} Phone: {phone}")

                    retry_count = 0
                    while retry_count < 5:
                        try:
                            telegram_client = TelegramClient(
                                rf"{ACCOUNT_CHECKER_DIR}\sessions\{phone}",
                                api_id=current_tg_api_id,
                                api_hash=current_tg_hash,
                                base_logger=logger,
                            )

                            self.tw_instance = TelethonWrapper(
                                client=telegram_client,
                                phone=phone,
                            )
                            if self.code_required:
                                if not self.tw_instance.check_client_authorized(
                                    code_callback=self.code_callback_manual
                                ):
                                    self.delete_unsuccessful_session(self.phone)
                                    raise ClientNotAuthorizedException("Client not authorized")
                            else:
                                if not self.tw_instance.check_client_authorized(code_callback=None):
                                    self.delete_unsuccessful_session(self.phone)
                                    raise ClientNotAuthorizedException("Client not authorized")
                            break
                        finally:
                            retry_count += 1

                    # Remove api
                    self.apis.remove(self.apis[0])
                    self.write_list_to_file(path=ACCOUNT_CHECKER_DIR, filename="api", new_list=self.apis)

                    clients.append(self.tw_instance.client)

                except NoTelegramApiInfoFoundAddUserException as e:
                    self.write_list_to_file(
                        path=rf"{ACCOUNT_CHECKER_DIR}\sessions", filename="phones", new_list=self.phones_copy
                    )
                    tkmb.showerror("Error Occured", "No telegram api info found.")
                    raise e
                except Exception as e:
                    # Clean up
                    self.phones_copy.remove(phone)
                    self.write_list_to_file(
                        path=rf"{ACCOUNT_CHECKER_DIR}\sessions", filename="phones", new_list=self.phones_copy
                    )
                    self.delete_unsuccessful_session(phone)
                    logger.exception(f"Exception occured with {str(e)}")

        return clients

    def get_clients_from_sessions(self) -> TelegramClient:
        clients = []
        for session in self.sessions:
            with self.pause_cond:
                while self.paused:
                    self.pause_cond.wait()

                if self.stopped:
                    self.running = False
                    break

                try:
                    # Move session
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

                    retry_count = 0
                    while retry_count < 5:
                        try:
                            telegram_client = TelegramClient(
                                session=session,
                                api_id=current_tg_api_id,
                                api_hash=current_tg_hash,
                                base_logger=logger,
                            )
                            self.tw_instance = TelethonWrapper(
                                client=telegram_client,
                                phone=self.phone,
                            )

                            if not self.tw_instance.check_client_authorized():
                                self.delete_unsuccessful_session(self.phone)
                                raise ClientNotAuthorizedException("Client not authorized")
                            break
                        finally:
                            retry_count += 1

                    # Remove api
                    self.apis.remove(self.apis[0])
                    self.write_list_to_file(path=ACCOUNT_CHECKER_DIR, filename="api", new_list=self.apis)

                    clients.append(self.tw_instance.client)
                except NoTelegramApiInfoFoundAddUserException as e:
                    tkmb.showerror("Error Occured", "No telegram api info found.")
                    raise e
                except Exception as e:
                    logger.exception(f"Exception occured with {str(e)}")
        return clients

    def delete_unsuccessful_session(self, phone: str):
        if self.tw_instance and self.tw_instance.client:
            self.tw_instance.client.disconnect()
            if os.path.isfile(f"{ACCOUNT_CHECKER_DIR}\\sessions\\{phone}.session"):
                os.remove(f"{ACCOUNT_CHECKER_DIR}\\sessions\\{phone}.session")

    def get_necessary_info(self, client: TelegramClient):
        chats = []
        last_date = None
        chunk_size = 100
        i = 0
        groups = []
        targets = []
        while True:
            with self.pause_cond:
                while self.paused:
                    self.pause_cond.wait()

                if self.stopped:
                    # if self.tw_instance and self.tw_instance.client:
                    #     self.tw_instance.client.loop.stop()
                    self.running = False
                    break
                if i >= 1:
                    break
                result = client(
                    GetDialogsRequest(
                        offset_date=last_date, offset_id=0, offset_peer=InputPeerEmpty(), limit=chunk_size, hash=0
                    )
                )
                chats.extend(result.chats)
                if not result.messages:
                    break
                for msg in chats:
                    try:
                        mgg = msg.megagroup  # type: ignore # noqa
                    except Exception:
                        continue
                    if msg.megagroup == True:
                        groups.append(msg)
                    try:
                        if msg.access_hash is not None:
                            targets.append(msg)
                    except Exception:
                        pass
                i += 1
                time.sleep(1)

        return chats, groups, targets

    def get_group_to_scrape(self, list_of_groups: List[str]):
        text = r"Please enter number of group to check user access: \n"
        i = 0
        for g in list_of_groups:
            text += f"{str(i)} -  {g.title} \n"
            i += 1

        new_win = Tk()
        new_win.withdraw()
        group_no = simpledialog.askinteger(
            "Group to Check Access", text, parent=new_win, minvalue=0, maxvalue=(len(list_of_groups) - 1)
        )

        new_win.destroy()

        return list_of_groups[group_no]

    def spam_bot_check(self, client: TelegramClient):
        try:
            client.send_message("@spambot", "/start")
        except Exception as e:
            print(str(e))

    def check_banned_participant(self, client: TelegramClient, group):
        ban_info = {}
        participant_info = client.get_permissions(group, client.get_me()).participant
        if isinstance(participant_info, ChannelParticipantBanned):
            ban_info = BanInfo(banned=True, until_date=participant_info.banned_rights.until_date)
        else:
            ban_info = BanInfo(banned=False, until_date=None)

        return ban_info

    def move_current_session(self, path: str, folder_to_move: str, client: TelegramClient):
        if client.is_connected():
            phone = client.get_me().phone
            client.disconnect()

            session = rf"{path}\sessions\+{phone}.session"
            if not os.path.exists(session):
                session = rf"{path}\sessions\{phone}.session"
            session_filename = session.split("\\")[-1]
            if os.path.exists(session):
                if not os.path.exists(ACCOUNT_CHECKER_DIR + "\\" + folder_to_move):
                    os.mkdir(ACCOUNT_CHECKER_DIR + "\\" + folder_to_move)
                shutil.move(session, rf"{path}\{folder_to_move}\{session_filename}")
            else:
                raise Exception(f"Session file not found {session}. So it cannot be moved.")

    def run(self):
        self.running = True
        loop = asyncio.new_event_loop()
        spam_bot = "@spambot" in self.spam_check
        asyncio.set_event_loop(loop)
        try:
            if self.client_mode:
                clients = self.get_clients_from_sessions()
            else:
                clients = self.get_clients_from_phones()

            if clients:
                if not self.spam_check:
                    raise Exception("No group or @spambot given to check user limitation.")
                if not spam_bot:
                    for client in clients:
                        group_info = self.join_group(self.spam_check[0], client)
            else:
                raise Exception("No client found to check access.")

            for client in clients:
                try:
                    if spam_bot:
                        self.spam_bot_check(client)
                    else:
                        chats, groups, targets = self.get_necessary_info(client)
                        group_filtered = list(filter(lambda x: x.id == group_info[0][0], groups))
                        if group_filtered:
                            group = group_filtered[0]
                            ban_info = self.check_banned_participant(client, group)

                            if ban_info.banned and ban_info.until_date:
                                folder_to_move = rf"limited_sessions\{ban_info.until_date.strftime('%d%m%Y_%H%M%S')}"
                                if (datetime.now(timezone.utc) + relativedelta(years=10)) < ban_info.until_date:
                                    logger.info(
                                        f"{client.get_me().phone} banned forever. It will be removed from sessions."
                                    )
                                    self.delete_unsuccessful_session("+" + client.get_me().phone)
                                else:
                                    logger.info(
                                        (
                                            f"{client.get_me().phone} restricted. So it will move "
                                            "to limited_sessions folder."
                                        )
                                    )
                                    self.move_current_session(
                                        path=ACCOUNT_CHECKER_DIR, folder_to_move=folder_to_move, client=client
                                    )
                            else:
                                folder_to_move = "good_sessions"
                                logger.info(
                                    f"{client.get_me().phone} has no restrictions. It will be moved to good sessions."
                                )
                                self.move_current_session(
                                    path=ACCOUNT_CHECKER_DIR, folder_to_move=folder_to_move, client=client
                                )
                        else:
                            logger.info("No group found to check.")

                    while GV.ProgramStatus == GV.PROGRAM_STATUS["IDLE"]:
                        time.sleep(1 / 30)
                        continue

                    if GV.ProgramStatus == GV.PROGRAM_STATUS["STOP"]:
                        self.running = False
                        break

                    if client.is_connected:
                        client.disconnect()

                except Exception as e:
                    logger.exception(f"Unexpected exception occured: {str(e)}")
                    if client.is_connected():
                        client.disconnect()

            logger.info("Account checks completed.")
        except Exception as e:
            logger.exception(f"Unexpected exception occured: {str(e)}")
