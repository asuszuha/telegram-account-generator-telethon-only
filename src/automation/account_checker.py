import asyncio
import os
import shutil
import time
import tkinter.messagebox as tkmb
from datetime import datetime, timezone
from enum import Enum
from tkinter import Tk, simpledialog
from typing import List, Optional

import pytz
from dateutil.relativedelta import relativedelta
from pydantic import BaseModel
from telethon.sync import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import CheckChatInviteRequest, GetDialogsRequest, ImportChatInviteRequest
from telethon.tl.types import InputPeerEmpty

import src.GV as GV
from src.automation.telethon_wrapper import PossibleProxyIssueException, TelethonWrapper
from src.utils.logger import logger
from src.utils.paths import ACCOUNT_CHECKER_DIR

from .abstract_automation import AbstractAutomation
from .exceptions_automation import (
    CannotOpenLoadPhoneNumbers,
    ClientNotAuthorizedException,
    NoTelegramApiInfoFoundAddUserException,
    NoTelegramApiInfoFoundException,
)


class BanInfo(BaseModel):
    banned: bool
    until_date: Optional[datetime]


class AccountCheckPhrases(Enum):
    ACCOUNT_LIMTIED = "your account is now limited until"
    ACCOUNT_BANNED = "unfortunately, your account is now limited."
    ACCOUNT_GOOD = "good news"


class AccountChecker(AbstractAutomation):
    def __init__(
        self,
        client_mode: int,
        code_required: int,
        proxy_enabled: int,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.client_mode = client_mode
        self.spam_check = self.read_file_with_property(path=ACCOUNT_CHECKER_DIR, filename="spam_check_link")
        self.apis = self.read_file_with_property(path=ACCOUNT_CHECKER_DIR, filename="api")
        self.test_messages = self.read_file_with_property(path=ACCOUNT_CHECKER_DIR, filename="test_messages")
        self.sessions = self.read_all_sessions(path=ACCOUNT_CHECKER_DIR)
        self.code_required = code_required
        self.proxy_enabled = proxy_enabled
        if proxy_enabled:
            self.proxies = self.read_file_with_property(path=ACCOUNT_CHECKER_DIR, filename="proxies")
            if not self.proxies:
                logger.exception("No proxy found in proxies.txt")
                raise Exception("No proxy found in proxies.txt")
        else:
            self.proxies = []
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

                    formatted_proxy = None
                    current_proxy = None
                    if self.proxy_enabled:
                        if self.proxies:
                            current_proxy = self.proxies[0]
                            formatted_proxy = self.read_txt_proxy(current_proxy)  # type: ignore
                            logger.info(f"Proxy will be used: {formatted_proxy['addr']}")
                        else:
                            raise Exception("No more proxy left in the proxies.txt")

                    retry_count = 0
                    while retry_count < 5:
                        try:
                            telegram_client = TelegramClient(
                                rf"{ACCOUNT_CHECKER_DIR}\sessions\{phone}",
                                api_id=current_tg_api_id,
                                api_hash=current_tg_hash,
                                base_logger=logger,
                                proxy=formatted_proxy if formatted_proxy else {},
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
                        except PossibleProxyIssueException:
                            if current_proxy and self.proxies:
                                logger.info(
                                    (
                                        f"Current proxy has issues to connect: {current_proxy}. "
                                        "It will be removed from proxy list."
                                    )
                                )
                                self.proxies.remove(current_proxy)
                                self.write_list_to_file(
                                    path=ACCOUNT_CHECKER_DIR, filename="proxies", new_list=self.proxies
                                )
                                if self.proxies:
                                    current_proxy = self.proxies[0]
                                    formatted_proxy = self.read_txt_proxy(current_proxy)
                                else:
                                    raise Exception("No more proxy left in the proxies.txt")
                        finally:
                            retry_count += 1

                    # Remove api
                    self.apis.remove(self.apis[0])
                    self.write_list_to_file(path=ACCOUNT_CHECKER_DIR, filename="api", new_list=self.apis)

                    # Remove proxy
                    if current_proxy and self.proxies:
                        self.proxies.remove(current_proxy)
                        self.write_list_to_file(path=ACCOUNT_CHECKER_DIR, filename="proxies", new_list=self.proxies)

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

    def get_client_from_session(self, session) -> TelegramClient:
        with self.pause_cond:
            while self.paused:
                self.pause_cond.wait()

            if self.stopped:
                self.running = False
                return

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

                formatted_proxy = None
                current_proxy = None
                if self.proxy_enabled:
                    if self.proxies:
                        current_proxy = self.proxies[0]
                        formatted_proxy = self.read_txt_proxy(current_proxy)  # type: ignore
                        logger.info(f"Proxy will be used: {formatted_proxy['addr']}")
                    else:
                        raise Exception("No more proxy left in the proxies.txt")

                retry_count = 0
                while retry_count < 5:
                    try:
                        telegram_client = TelegramClient(
                            session=session,
                            api_id=current_tg_api_id,
                            api_hash=current_tg_hash,
                            base_logger=logger,
                            proxy=formatted_proxy if formatted_proxy else {},
                        )
                        self.tw_instance = TelethonWrapper(
                            client=telegram_client,
                            phone=self.phone,
                        )

                        if not self.tw_instance.check_client_authorized():
                            self.delete_unsuccessful_session(self.phone)
                            raise ClientNotAuthorizedException("Client not authorized")
                        break
                    except PossibleProxyIssueException:
                        if current_proxy and self.proxies:
                            logger.info(
                                (
                                    f"Current proxy has issues to connect: {current_proxy}. "
                                    "It will be removed from proxy list."
                                )
                            )
                            self.proxies.remove(current_proxy)
                            self.write_list_to_file(path=ACCOUNT_CHECKER_DIR, filename="proxies", new_list=self.proxies)
                            if self.proxies:
                                current_proxy = self.proxies[0]
                                formatted_proxy = self.read_txt_proxy(current_proxy)
                            else:
                                raise Exception("No more proxy left in the proxies.txt")
                    finally:
                        retry_count += 1

                # Remove api
                self.apis.remove(self.apis[0])
                self.write_list_to_file(path=ACCOUNT_CHECKER_DIR, filename="api", new_list=self.apis)

                # Remove proxy
                if current_proxy and self.proxies:
                    self.proxies.remove(current_proxy)
                    self.write_list_to_file(path=ACCOUNT_CHECKER_DIR, filename="proxies", new_list=self.proxies)

                return self.tw_instance.client
            except NoTelegramApiInfoFoundAddUserException as e:
                tkmb.showerror("Error Occured", "No telegram api info found.")
                raise e
            except Exception as e:
                logger.exception(f"Exception occured with {str(e)}")

    def get_client_from_phone(self, phone) -> TelegramClient:
        with self.pause_cond:
            while self.paused:
                self.pause_cond.wait()

            if self.stopped:
                self.running = False
                return

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

                formatted_proxy = None
                current_proxy = None
                if self.proxy_enabled:
                    if self.proxies:
                        current_proxy = self.proxies[0]
                        formatted_proxy = self.read_txt_proxy(current_proxy)  # type: ignore
                        logger.info(f"Proxy will be used: {formatted_proxy['addr']}")
                    else:
                        raise Exception("No more proxy left in the proxies.txt")

                retry_count = 0
                while retry_count < 5:
                    try:
                        telegram_client = TelegramClient(
                            rf"{ACCOUNT_CHECKER_DIR}\sessions\{phone}",
                            api_id=current_tg_api_id,
                            api_hash=current_tg_hash,
                            base_logger=logger,
                            proxy=formatted_proxy if formatted_proxy else {},
                        )

                        self.tw_instance = TelethonWrapper(
                            client=telegram_client,
                            phone=phone,
                        )
                        if self.code_required:
                            if not self.tw_instance.check_client_authorized(code_callback=self.code_callback_manual):
                                self.delete_unsuccessful_session(self.phone)
                                raise ClientNotAuthorizedException("Client not authorized")
                        else:
                            if not self.tw_instance.check_client_authorized(code_callback=None):
                                self.delete_unsuccessful_session(self.phone)
                                raise ClientNotAuthorizedException("Client not authorized")
                        break
                    except PossibleProxyIssueException:
                        if current_proxy and self.proxies:
                            logger.info(
                                (
                                    f"Current proxy has issues to connect: {current_proxy}. "
                                    "It will be removed from proxy list."
                                )
                            )
                            self.proxies.remove(current_proxy)
                            self.write_list_to_file(path=ACCOUNT_CHECKER_DIR, filename="proxies", new_list=self.proxies)
                            if self.proxies:
                                current_proxy = self.proxies[0]
                                formatted_proxy = self.read_txt_proxy(current_proxy)
                            else:
                                raise Exception("No more proxy left in the proxies.txt")
                    finally:
                        retry_count += 1

                # Remove api
                self.apis.remove(self.apis[0])
                self.write_list_to_file(path=ACCOUNT_CHECKER_DIR, filename="api", new_list=self.apis)

                # Remove proxy
                if current_proxy and self.proxies:
                    self.proxies.remove(current_proxy)
                    self.write_list_to_file(path=ACCOUNT_CHECKER_DIR, filename="proxies", new_list=self.proxies)

                return self.tw_instance.client

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

                    formatted_proxy = None
                    current_proxy = None
                    if self.proxy_enabled:
                        if self.proxies:
                            current_proxy = self.proxies[0]
                            formatted_proxy = self.read_txt_proxy(current_proxy)  # type: ignore
                            logger.info(f"Proxy will be used: {formatted_proxy['addr']}")
                        else:
                            raise Exception("No more proxy left in the proxies.txt")

                    retry_count = 0
                    while retry_count < 5:
                        try:
                            telegram_client = TelegramClient(
                                session=session,
                                api_id=current_tg_api_id,
                                api_hash=current_tg_hash,
                                base_logger=logger,
                                proxy=formatted_proxy if formatted_proxy else {},
                            )
                            self.tw_instance = TelethonWrapper(
                                client=telegram_client,
                                phone=self.phone,
                            )

                            if not self.tw_instance.check_client_authorized():
                                self.delete_unsuccessful_session(self.phone)
                                raise ClientNotAuthorizedException("Client not authorized")
                            break
                        except PossibleProxyIssueException:
                            if current_proxy and self.proxies:
                                logger.info(
                                    (
                                        f"Current proxy has issues to connect: {current_proxy}. "
                                        "It will be removed from proxy list."
                                    )
                                )
                                self.proxies.remove(current_proxy)
                                self.write_list_to_file(
                                    path=ACCOUNT_CHECKER_DIR, filename="proxies", new_list=self.proxies
                                )
                                if self.proxies:
                                    current_proxy = self.proxies[0]
                                    formatted_proxy = self.read_txt_proxy(current_proxy)
                                else:
                                    raise Exception("No more proxy left in the proxies.txt")
                        finally:
                            retry_count += 1

                    # Remove api
                    self.apis.remove(self.apis[0])
                    self.write_list_to_file(path=ACCOUNT_CHECKER_DIR, filename="api", new_list=self.apis)

                    # Remove proxy
                    if current_proxy and self.proxies:
                        self.proxies.remove(current_proxy)
                        self.write_list_to_file(path=ACCOUNT_CHECKER_DIR, filename="proxies", new_list=self.proxies)

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
            self.tw_instance.client.session.close()
            if os.path.isfile(f"{ACCOUNT_CHECKER_DIR}\\sessions\\{phone}.session"):
                os.remove(f"{ACCOUNT_CHECKER_DIR}\\sessions\\{phone}.session")

    def delete_unsuccessful_session_client(self, client: TelegramClient, phone: str):
        if client.is_connected():
            client.disconnect()
            client.session.close()
            if os.path.isfile(f"{ACCOUNT_CHECKER_DIR}\\sessions\\{phone}.session"):
                os.remove(f"{ACCOUNT_CHECKER_DIR}\\sessions\\{phone}.session")
        else:
            client.session.close()
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
            raise Exception(f"Exception occured during writing spam bot. {str(e)}")
        dialogs = client.get_dialogs()
        list_of_spam_bot_dialog = list(filter(lambda x: x.title.lower() == "spam info bot", dialogs))
        if list_of_spam_bot_dialog:
            spam_bot_dialog = list_of_spam_bot_dialog[0]
            messages = client.get_messages(spam_bot_dialog, limit=100)
            newest_message = messages[0]
            client_info = client.get_me()
            phone = client_info.phone
            if AccountCheckPhrases.ACCOUNT_BANNED.value in newest_message.text.lower():
                logger.info(f"{phone} account banned. It will be removed")
                return BanInfo(banned=True, until_date=datetime.now(timezone.utc) + relativedelta(years=30))
            elif AccountCheckPhrases.ACCOUNT_GOOD.value in newest_message.text.lower():
                logger.info(f"{phone} has no restrictions. It will be moved to good sessions.")
                return BanInfo(banned=False, until_date=None)
            elif AccountCheckPhrases.ACCOUNT_LIMTIED.value in newest_message.text.lower():
                pre_processed_message = (
                    newest_message.raw_text.lower()
                    .split("\n")[1]
                    .split("your account is now limited until")[-1]
                    .strip()
                )
                date_until = datetime.strptime(
                    pre_processed_message.replace(".", "").replace(",", "").replace(" ", "")[:-8], "%d%b%Y"
                )
                date_until = pytz.utc.localize(date_until)
                return BanInfo(banned=True, until_date=date_until)

        else:
            raise Exception("No spambot dialog found.")

    def check_banned_participant(self, client: TelegramClient, group, test_message: str):
        from telethon.errors.rpcerrorlist import UserBannedInChannelError

        try:
            client.send_message(group, test_message)
        except UserBannedInChannelError:
            return BanInfo(banned=True, until_date=datetime.now(timezone.utc) + relativedelta(years=20))

        return BanInfo(banned=False, until_date=None)

    def move_current_session(self, path: str, folder_to_move: str, client: TelegramClient):
        if client.is_connected():
            phone = client.get_me().phone
            client.disconnect()
            client.session.close()

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

    def bot_check_run(self, client: TelegramClient, spam_bot: bool, group_info=None, test_message=None):
        try:
            if spam_bot:
                ban_info = self.spam_bot_check(client)
                if ban_info:
                    if ban_info.banned and ban_info.until_date:
                        folder_to_move = rf"limited_sessions\{ban_info.until_date.strftime('%d%m%Y')}"
                        if (datetime.now(timezone.utc) + relativedelta(years=10)) < ban_info.until_date:
                            phone = client.get_me().phone
                            logger.info(f"{phone} banned forever. It will be moved to banned_sessions.")
                            folder_to_move = "banned_sessions"
                            self.move_current_session(
                                path=ACCOUNT_CHECKER_DIR, folder_to_move=folder_to_move, client=client
                            )
                        else:
                            self.move_current_session(
                                path=ACCOUNT_CHECKER_DIR, folder_to_move=folder_to_move, client=client
                            )
                    else:
                        folder_to_move = "good_sessions"
                        self.move_current_session(
                            path=ACCOUNT_CHECKER_DIR, folder_to_move=folder_to_move, client=client
                        )
            else:
                chats, groups, targets = self.get_necessary_info(client)
                group_filtered = list(filter(lambda x: x.id == group_info[0][0], groups))
                if group_filtered:
                    group = group_filtered[0]
                    ban_info = self.check_banned_participant(client, group, test_message=test_message)

                    if ban_info.banned and ban_info.until_date:
                        folder_to_move = rf"limited_sessions\{ban_info.until_date.strftime('%d%m%Y')}"
                        if (datetime.now(timezone.utc) + relativedelta(years=10)) < ban_info.until_date:
                            logger.info(f"{client.get_me().phone} banned forever. It will be moved to banned sessions.")
                            folder_to_move = "banned_sessions"
                            self.move_current_session(
                                path=ACCOUNT_CHECKER_DIR, folder_to_move=folder_to_move, client=client
                            )
                        else:
                            logger.info(
                                (f"{client.get_me().phone} restricted. So it will move " "to limited_sessions folder.")
                            )
                            self.move_current_session(
                                path=ACCOUNT_CHECKER_DIR, folder_to_move=folder_to_move, client=client
                            )
                    else:
                        folder_to_move = "good_sessions"
                        logger.info(f"{client.get_me().phone} has no restrictions. It will be moved to good sessions.")
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
                return

            if client.is_connected():
                client.disconnect()

        except Exception as e:
            logger.exception(f"Unexpected exception occured: {str(e)}")
            if client.is_connected():
                client.disconnect()

    def run(self):
        self.running = True
        loop = asyncio.new_event_loop()
        spam_bot = "@spambot" in self.spam_check
        asyncio.set_event_loop(loop)
        test_message_counter = 0
        try:
            if self.client_mode:
                for session in self.sessions:
                    try:
                        client = self.get_client_from_session(session)
                        if not self.test_messages:
                            raise Exception("No test messages given.")
                        test_message = self.test_messages[test_message_counter]
                        while GV.ProgramStatus == GV.PROGRAM_STATUS["IDLE"]:
                            time.sleep(1 / 30)
                            continue

                        if GV.ProgramStatus == GV.PROGRAM_STATUS["STOP"]:
                            self.running = False
                            break
                        group_info = None
                        if client:
                            if not self.spam_check:
                                raise Exception("No group or @spambot given to check user limitation.")
                            if not spam_bot:
                                group_info = self.join_group(self.spam_check[0], client)
                            self.bot_check_run(client, spam_bot, group_info, test_message)
                        else:
                            raise Exception("No client found to check access.")
                        while GV.ProgramStatus == GV.PROGRAM_STATUS["IDLE"]:
                            time.sleep(1 / 30)
                            continue

                        if GV.ProgramStatus == GV.PROGRAM_STATUS["STOP"]:
                            self.running = False
                            break

                        test_message_counter += 1
                        test_message_counter = test_message_counter % len(self.test_messages)
                    except ClientNotAuthorizedException:
                        continue
                    except NoTelegramApiInfoFoundException:
                        break
                    except NoTelegramApiInfoFoundAddUserException:
                        break
                    except Exception as e:
                        logger.exception(f"Exception occured for current session with: {str(e)}")
            else:
                self.phones_copy = self.phones.copy()
                for phone in self.phones:
                    try:
                        client = self.get_client_from_phone(phone)
                        while GV.ProgramStatus == GV.PROGRAM_STATUS["IDLE"]:
                            time.sleep(1 / 30)
                            continue

                        if GV.ProgramStatus == GV.PROGRAM_STATUS["STOP"]:
                            self.running = False
                            break
                        group_info = None
                        if client:
                            if not self.spam_check:
                                raise Exception("No group or @spambot given to check user limitation.")
                            if not spam_bot:
                                group_info = self.join_group(self.spam_check[0], client)
                            self.bot_check_run(client, spam_bot, group_info)
                        else:
                            raise Exception("No client found to check access.")
                        while GV.ProgramStatus == GV.PROGRAM_STATUS["IDLE"]:
                            time.sleep(1 / 30)
                            continue

                        if GV.ProgramStatus == GV.PROGRAM_STATUS["STOP"]:
                            self.running = False
                            break
                    except ClientNotAuthorizedException:
                        continue
                    except NoTelegramApiInfoFoundException:
                        break
                    except NoTelegramApiInfoFoundAddUserException:
                        break
                    except Exception as e:
                        logger.exception(f"Exception occured for current session with: {str(e)}")

            logger.info("Account checks completed.")
        except Exception as e:
            logger.exception(f"Unexpected exception occured: {str(e)}")
