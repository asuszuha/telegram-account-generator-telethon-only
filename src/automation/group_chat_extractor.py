import asyncio
import os
import re
import shutil
import time
import tkinter.messagebox as tkmb
from cgitb import reset
from datetime import datetime
from email import message
from re import I, T
from sys import exit
from time import sleep
from tkinter import Tk, simpledialog
from tokenize import group
from typing import List

import aiofiles
import emoji
import pytz
from dateutil.relativedelta import relativedelta
from telethon import errors
from telethon.sync import TelegramClient
from telethon.tl.functions.channels import GetParticipantsRequest, InviteToChannelRequest, JoinChannelRequest
from telethon.tl.functions.messages import CheckChatInviteRequest, GetDialogsRequest, ImportChatInviteRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import (
    ChannelParticipantsAdmins,
    ChannelParticipantsSearch,
    InputChannel,
    InputPeerChannel,
    InputPeerEmpty,
    InputUser,
    User,
    UserEmpty,
    UserStatusEmpty,
    UserStatusLastMonth,
    UserStatusLastWeek,
    UserStatusOffline,
    UserStatusOnline,
    UserStatusRecently,
)

import src.GV as GV
from src.automation.telethon_wrapper import PossibleProxyIssueException, TelethonWrapper
from src.utils.logger import logger
from src.utils.paths import GROUP_CHAT_EXTRACTOR_DIR

from .abstract_automation import AbstractAutomation
from .exceptions_automation import (
    CannotOpenLoadPhoneNumbers,
    ClientNotAuthorizedException,
    NoTelegramApiInfoFoundAddUserException,
)


class GroupChatScraper(AbstractAutomation):
    def __init__(
        self,
        # run_mode: int,
        client_mode: int,
        # max_session: str,
        code_required: int,
        # user_delay: str,
        # proxy_enabled: int,
        # threading_option: int,
        message_scrape_option: int,
        # user_add_option: int,
        start_date_user_filter: datetime,
        end_date_user_filter: datetime,
        **kwargs,
    ):
        super().__init__(**kwargs)

        # self.run_mode = run_mode
        self.client_mode = client_mode
        self.message_scrape_option = message_scrape_option
        self.group = self.read_file_with_property(path=GROUP_CHAT_EXTRACTOR_DIR, filename="group")
        self.apis = self.read_file_with_property(path=GROUP_CHAT_EXTRACTOR_DIR, filename="api")
        self.bad_words = self.read_file_with_property(path=GROUP_CHAT_EXTRACTOR_DIR, filename="bad_words")
        # self.added_user_ids = self.read_file_with_property(path=GROUP_CHAT_EXTRACTOR_DIR, filename="added_user_ids")
        # self.group_to_scrape = self.read_file_with_property(path=GROUP_CHAT_EXTRACTOR_DIR, filename="group_to_scrape")

        self.sessions = self.read_all_sessions(path=GROUP_CHAT_EXTRACTOR_DIR)
        self.code_required = code_required
        # if self.client_mode == 1 and int(max_session):
        #     self.max_sessions = int(max_session)
        #     self.sessions = self.sessions[: self.max_sessions]

        if self.client_mode == 0:
            self.phones = self.load_phone_numbers()

        # if proxy_enabled:
        #     self.proxies = self.read_file_with_property(path=AUTO_REGISTER_PATH_DIR, filename="proxies")
        # else:
        #     self.proxies = []
        # self.threading_option = threading_option
        # self.user_scrape_option = user_scrape_option
        # self.user_add_option = user_add_option
        self.start_date_user_filter = start_date_user_filter
        self.end_date_user_filter = end_date_user_filter
        if end_date_user_filter < start_date_user_filter and self.user_scrape_option:
            logger.error("Start date should be smaller than end date.")
            raise Exception("Start date should be smaller than end date.")

    def load_phone_numbers(self):
        try:
            with open(rf"{GROUP_CHAT_EXTRACTOR_DIR}\sessions\phones.txt", "r") as phone_file:
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

    def get_client_from_phone(self) -> TelegramClient:
        self.phones_copy = self.phones.copy()

        for phone in self.phones:
            with self.pause_cond:
                while self.paused:
                    self.pause_cond.wait()

                if self.stopped:
                    # if self.tw_instance and self.tw_instance.client:
                    #     self.tw_instance.client.loop.stop()
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

                    # formatted_proxy = None
                    # current_proxy = None
                    # if self.proxies:
                    #     current_proxy = self.proxies[0]
                    #     formatted_proxy = self.read_txt_proxy(current_proxy)  # type: ignore
                    #     logger.info(f"Proxy will be used: {formatted_proxy['addr']}")
                    retry_count = 0
                    while retry_count < 5:
                        try:
                            telegram_client = TelegramClient(
                                rf"{GROUP_CHAT_EXTRACTOR_DIR}\sessions\{phone}",
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
                        # except PossibleProxyIssueException:
                        #     if current_proxy and self.proxies:
                        #         logger.info(
                        #             (
                        #                 f"Current proxy has issues to connect: {current_proxy}. "
                        #                 "It will be removed from proxy list."
                        #             )
                        #         )
                        #         self.proxies.remove(current_proxy)
                        #         self.write_list_to_file(
                        #             path=GROUP_CHAT_EXTRACTOR_DIR, filename="proxies", new_list=self.proxies
                        #         )
                        #         current_proxy = self.proxies[0]
                        #         formatted_proxy = self.read_txt_proxy(current_proxy)  # type: ignore
                        #         if self.tw_instance and self.tw_instance.client:
                        #             if self.tw_instance.client.is_connected():
                        #                 self.tw_instance.client.disconnect()
                        finally:
                            retry_count += 1

                    # Remove api
                    self.apis.remove(self.apis[0])
                    self.write_list_to_file(path=GROUP_CHAT_EXTRACTOR_DIR, filename="api", new_list=self.apis)

                    # Remove proxy
                    # if current_proxy and self.proxies:
                    #     self.proxies.remove(current_proxy)
                    #     self.write_list_to_file(path=AUTO_REGISTER_PATH_DIR, filename="proxies", new_list=self.proxies)
                    return self.tw_instance.client

                except NoTelegramApiInfoFoundAddUserException as e:
                    self.write_list_to_file(
                        path=rf"{GROUP_CHAT_EXTRACTOR_DIR}\sessions", filename="phones", new_list=self.phones_copy
                    )
                    tkmb.showerror("Error Occured", "No telegram api info found.")
                    raise e
                except Exception as e:
                    # Clean up
                    self.phones_copy.remove(phone)
                    self.write_list_to_file(
                        path=rf"{GROUP_CHAT_EXTRACTOR_DIR}\sessions", filename="phones", new_list=self.phones_copy
                    )
                    self.delete_unsuccessful_session(phone)
                    logger.exception(f"Exception occured with {str(e)}")

    def get_client_from_session(self) -> TelegramClient:
        for session in self.sessions:
            with self.pause_cond:
                while self.paused:
                    self.pause_cond.wait()

                if self.stopped:
                    # if self.tw_instance and self.tw_instance.client:
                    #     self.tw_instance.client.loop.stop()
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

                    # formatted_proxy = None
                    # current_proxy = None
                    # if self.proxies:
                    #     current_proxy = self.proxies[0]
                    #     formatted_proxy = self.read_txt_proxy(current_proxy)  # type: ignore
                    #     logger.info(f"Proxy will be used: {formatted_proxy['addr']}")
                    retry_count = 0
                    while retry_count < 5:
                        try:
                            telegram_client = TelegramClient(
                                session=session,
                                api_id=current_tg_api_id,
                                api_hash=current_tg_hash,
                                base_logger=logger,
                                # proxy=formatted_proxy if formatted_proxy else {},
                            )
                            self.tw_instance = TelethonWrapper(
                                client=telegram_client,
                                phone=self.phone,
                            )

                            if not self.tw_instance.check_client_authorized():
                                self.delete_unsuccessful_session(self.phone)
                                raise ClientNotAuthorizedException("Client not authorized")
                            break
                        # except PossibleProxyIssueException:
                        #     if current_proxy and self.proxies:
                        #         logger.info(
                        #             (
                        #                 f"Current proxy has issues to connect: {current_proxy}. "
                        #                 "It will be removed from proxy list."
                        #             )
                        #         )
                        #         self.proxies.remove(current_proxy)
                        #         self.write_list_to_file(
                        #             path=GROUP_CHAT_EXTRACTOR_DIR, filename="proxies", new_list=self.proxies
                        #         )
                        #         current_proxy = self.proxies[0]
                        #         if (
                        #             self.tw_instance
                        #             and self.tw_instance.client
                        #             and self.tw_instance.client.is_connected()
                        #         ):
                        #             self.tw_instance.client.disconnect()
                        finally:
                            retry_count += 1

                    # self.tw_instance.client.flood_sleep_threshold = 0
                    # clients.append(self.tw_instance.client)

                    # Remove api
                    self.apis.remove(self.apis[0])
                    self.write_list_to_file(path=GROUP_CHAT_EXTRACTOR_DIR, filename="api", new_list=self.apis)

                    # Remove proxy
                    # if current_proxy and self.proxies:
                    #     self.proxies.remove(current_proxy)
                    #     self.write_list_to_file(path=AUTO_REGISTER_PATH_DIR, filename="proxies", new_list=self.proxies)

                    return self.tw_instance.client
                except NoTelegramApiInfoFoundAddUserException as e:
                    tkmb.showerror("Error Occured", "No telegram api info found.")
                    raise e
                except Exception as e:
                    logger.exception(f"Exception occured with {str(e)}")

    def delete_unsuccessful_session(self, phone: str):
        if self.tw_instance and self.tw_instance.client:
            self.tw_instance.client.disconnect()
            if os.path.isfile(f"{GROUP_CHAT_EXTRACTOR_DIR}\\sessions\\{phone}.session"):
                os.remove(f"{GROUP_CHAT_EXTRACTOR_DIR}\\sessions\\{phone}.session")

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
                sleep(1)

        return chats, groups, targets

    def scrape_admins_from_group(self, client: TelegramClient, group):
        admins = client(
            GetParticipantsRequest(
                channel=InputPeerChannel(group.id, group.access_hash),
                filter=ChannelParticipantsAdmins(),
                offset=0,
                limit=1000,
                hash=0,
            )
        )

        return admins

    async def save_scraped_list(self, all_participants: List):
        try:
            logger.info("Saving user list...")
            if self.user_add_option:
                async with aiofiles.open(
                    rf"{AUTO_REGISTER_PATH_DIR}\user_ids.txt", "a", encoding="utf-8", errors="ignore"
                ) as f:
                    for item in all_participants:
                        if item.id and item.access_hash:
                            await f.write("%s\n" % (item.id))
            else:
                async with aiofiles.open(
                    rf"{AUTO_REGISTER_PATH_DIR}\usernames.txt", "a", encoding="utf-8", errors="ignore"
                ) as f:
                    for item in all_participants:
                        if item.username is not None:
                            await f.write("%s\n" % (item.username))

            logger.info("Saving Done...")
        except Exception as e:
            logger.exception("Error occured during saving...")
            logger.exception(e)

    async def filter_users_with_date(self, client: TelegramClient, user_list: List, start_date: datetime):
        users = []
        for user in user_list:
            user = await client(GetFullUserRequest(user))
            last_online_date = user.user.status.was_online.date()
            if last_online_date >= start_date:
                users.append(user)

        return users

    async def move_current_session(self, client: TelegramClient):
        if client.is_connected():
            client_me = await client.get_me()
            phone = client_me.phone
            await client.disconnect()
            await asyncio.sleep(5)

        session = rf"{AUTO_REGISTER_PATH_DIR}\sessions\+{phone}.session"
        if not os.path.exists(session):
            session = rf"{AUTO_REGISTER_PATH_DIR}\sessions\{phone}.session"
        session_filename = session.split("\\")[-1]
        if os.path.exists(session):
            shutil.move(session, rf"{AUTO_REGISTER_PATH_DIR}\used_sessions\{session_filename}")
        else:
            raise Exception(f"Session file not found {session}. So it cannot be moved.")

    async def add_users_to_groups(self, client: TelegramClient, userlist: List, group_info: List, counter: int):
        peer_flooded = []
        too_many_request = []
        wait_seconds = []
        other_exceptions = []
        try:
            [cid, ah] = group_info
        except Exception as e:
            print(str(e))
            await self.move_current_session(client)
            return (userlist, {client: False})
        client_reusable = True
        client_me = await client.get_me()
        phone = client_me.phone
        for index, user in enumerate(userlist, 1):
            while GV.ProgramStatus == GV.PROGRAM_STATUS["IDLE"]:
                await asyncio.sleep(1 / 30)
                continue

            if GV.ProgramStatus == GV.PROGRAM_STATUS["STOP"]:
                self.running = False
                break

            try:
                if self.user_add_option:
                    __user = await client.get_entity(int(user))
                else:
                    __user = await client.get_entity(user)

                logger.info(f"Adding user : {user} by {str(phone)}")
                await client(
                    InviteToChannelRequest(
                        InputChannel(cid[counter], ah[counter]),
                        [__user],
                    )
                )
                peer_flooded = []
                too_many_request = []
                wait_seconds = []
                other_exceptions = []
                await asyncio.sleep(self.user_delay)
            except errors.FloodWaitError as e:
                if e.seconds > 100:
                    print("Flood for", e.seconds)
                    if self.client_mode:
                        try:
                            await self.move_current_session(client)
                        except Exception:
                            logger.exception("Cannot move to session.")
                    await self.disconnect_all_clients(clients=[client])
                    client_reusable = False
                    break
                await asyncio.sleep(e.seconds)
            except errors.UserPrivacyRestrictedError as e:
                await asyncio.sleep(self.user_delay)
                logger.info(str(e))
                continue
            except errors.UserIdInvalidError as e:
                await asyncio.sleep(self.user_delay)
                logger.info(str(e))
                continue
            except Exception as e:
                await asyncio.sleep(self.user_delay)
                if "PEER_FLOOD" in str(e):
                    peer_flooded.append(user)
                    if len(peer_flooded) > 7:
                        logger.info(f"Account {str(phone)} peer flooded {str(len(peer_flooded))} times")
                        client_reusable = False
                        if self.client_mode:
                            try:
                                await self.move_current_session(client)
                            except Exception:
                                logger.exception("Cannot move to session.")
                        peer_flooded = []
                        await self.disconnect_all_clients(clients=[client])
                        break
                elif "privacy" in str(e):
                    await asyncio.sleep(self.user_delay)
                elif "Too many requests" in str(e):
                    await asyncio.sleep(self.user_delay)
                    too_many_request.append(user)
                    if len(too_many_request) > 7:
                        logger.info(f"Account {str(phone)} Too many request {str(len(too_many_request))} times")
                        if self.client_mode:
                            try:
                                await self.move_current_session(client)
                            except Exception:
                                logger.exception("Cannot move to session.")
                        too_many_request = []
                        await self.disconnect_all_clients(clients=[client])
                        client_reusable = False
                        break
                elif "wait" in str(e):
                    await asyncio.sleep(self.user_delay)
                    wait_seconds.append(user)
                    if len(wait_seconds) > 7:
                        logger.info(
                            f"Account {str(phone)} after wait seconds is required {str(len(wait_seconds))} times"
                        )
                        if self.client_mode:
                            try:
                                await self.move_current_session(client)
                            except Exception:
                                logger.exception("Cannot move to session.")
                        await self.disconnect_all_clients(clients=[client])
                        client_reusable = False
                        break
                elif "entity for PeerUser" in str(e):
                    await asyncio.sleep(self.user_delay)
                elif "privacy" not in str(e):
                    await asyncio.sleep(self.user_delay)
                    other_exceptions.append(user)
                    if len(other_exceptions) > 7:
                        logger.info(f"Account {str(phone)} after other errors {str(len(other_exceptions))} times")
                        if self.client_mode:
                            try:
                                await self.move_current_session(client)
                            except Exception:
                                logger.exception("Cannot move to session.")
                        other_exceptions = []
                        await self.disconnect_all_clients(clients=[client])
                        logger.info("all accounts other error occurs")
                        client_reusable = False
                        break
                elif "Keyboard" in str(e):
                    await asyncio.sleep(self.user_delay)
                    if self.client_mode:
                        try:
                            await self.move_current_session(client)
                        except Exception:
                            logger.exception("Cannot move to session.")
                    client_reusable = False
                    break
                logger.info(e)
                pass

        logger.info(f"Adding Completed for #{str(index)} users.")
        return (userlist[index:] if index != (len(userlist) - 1) else [], {client: client_reusable}, userlist[:index])

    async def check_user_privacy(self, client: TelegramClient, user_list: List):
        counter = 0
        users_verified = []
        while counter < len(user_list):
            while GV.ProgramStatus == GV.PROGRAM_STATUS["IDLE"]:
                await asyncio.sleep(1 / 30)
                continue

            if GV.ProgramStatus == GV.PROGRAM_STATUS["STOP"]:
                self.running = False
                break
            try:
                if user_list[counter].username:
                    try:
                        full_user = await client(GetFullUserRequest(user_list[counter].username))
                        await asyncio.sleep(self.user_delay)
                    except errors.FloodWaitError as e:
                        if e.seconds > 300:
                            if self.client_mode:
                                try:
                                    await self.move_current_session(client)
                                except Exception:
                                    logger.exception("Cannot move to session.")
                            await self.disconnect_all_clients(clients=[client])
                            break
                        await asyncio.sleep(e.seconds)
                    except Exception as e:
                        logger.error(f"Exception occured: {str(e)}")
                        counter += 1
                        continue
                    if user_list[counter].username is not None and full_user.phone_calls_available:
                        users_verified.append(user_list[counter])
            except Exception:
                pass

            counter += 1

        if counter != len(user_list):
            user_list = user_list[counter:]
        else:
            user_list = []
        # If user list has elements it means we have long sleep time
        return [users_verified, user_list, {client: False if user_list else True}]

    def remove_admins_from_list(self, messages, admins):
        logger.info("Removing admin messages.")
        admin_user_ids = [participant.user_id for participant in admins.participants]
        messages = [msg for msg in messages if msg.sender_id not in admin_user_ids]

        return messages

    def remove_bad_words(self, messages):
        new_msgs = []
        for msg in messages:
            for bad_word in self.bad_words:
                insensitive_badword = re.compile(re.escape(bad_word), re.IGNORECASE)
                msg = insensitive_badword.sub("", msg).strip()

            new_msgs.append(msg)

        return new_msgs

    def add_replies_to_messages_and_extract_text(self, messages, total_len_messages: int):
        only_txt_messages = []
        messages = [msg for msg in messages if msg.raw_text]
        for msg in messages:
            if msg.reply_to_msg_id:
                list_of_filter = list(filter(lambda x: x.id == msg.reply_to_msg_id, messages))
                if list_of_filter:
                    index_of_reply = str(messages.index(list_of_filter[0]) + 1 + total_len_messages)
                    only_txt_messages.append(emoji.demojize(msg.raw_text.replace("\n", "")) + f" ({index_of_reply})")
                else:
                    only_txt_messages.append(emoji.demojize(msg.raw_text.replace("\n", "")))
            else:
                only_txt_messages.append(emoji.demojize(msg.raw_text.replace("\n", "")))
        only_txt_messages = self.remove_bad_words(only_txt_messages)
        return only_txt_messages, len(only_txt_messages) + total_len_messages

    def remove_spaces_from_file(self):
        with open(rf"{GROUP_CHAT_EXTRACTOR_DIR}\extracted_messages.txt", "r", encoding="utf-8", errors="ignore") as f:
            messages = f.readlines()[:-1]

        messages = [msg for msg in messages if msg != "\n"]
        with open(rf"{GROUP_CHAT_EXTRACTOR_DIR}\extracted_messages.txt", "w+", encoding="utf-8", errors="ignore") as f:
            f.writelines(messages)

    def scrape_messages(
        self, client: TelegramClient, group, admins, start_date: datetime = None, end_date: datetime = None
    ):
        if start_date and end_date:
            pre_first_msg = client.get_messages(group, offset_date=start_date, limit=1)[0]
            first_msg = client.get_messages(group, min_id=pre_first_msg.id, limit=1, reverse=True)[0]
            last_msg = client.get_messages(group, offset_date=end_date, limit=1)[0]
            current_id = first_msg.id + 1000 if first_msg.id + 1000 <= last_msg.id else last_msg.id
            previous_id = first_msg.id
            total_len_messages = 0
            while current_id <= last_msg.id:
                logger.info(f"Extracting messages between ids {previous_id} and {current_id}")
                current_msgs = client.get_messages(group, min_id=previous_id, max_id=current_id, reverse=True)
                current_msgs = self.remove_admins_from_list(current_msgs, admins)
                txt_only_msgs, total_len_messages = self.add_replies_to_messages_and_extract_text(
                    current_msgs, total_len_messages
                )
                with open(
                    rf"{GROUP_CHAT_EXTRACTOR_DIR}\extracted_messages.txt", "a", encoding="utf-8", errors="ignore"
                ) as f:
                    n_msgs = ["{}\n".format(msg) for msg in txt_only_msgs]
                    f.writelines(n_msgs)
                previous_id = current_id
                current_id = current_id + 1000
                # self.remove_spaces_from_file()
                while GV.ProgramStatus == GV.PROGRAM_STATUS["IDLE"]:
                    time.sleep(1 / 30)
                    continue

                if GV.ProgramStatus == GV.PROGRAM_STATUS["STOP"]:
                    self.running = False
                    break
        else:
            last_msg = client.get_messages(group)
            logger.info(f"Total messages found: {last_msg.total} and last message id {last_msg[0].id}")
            current_id = 1000
            previous_id = 0
            while current_id < last_msg[0].id:
                logger.info(f"Extracting messages between ids {previous_id} and {current_id}")
                current_msgs = client.get_messages(group, min_id=previous_id, max_id=current_id, reverse=True)
                current_msgs = self.remove_admins_from_list(current_msgs, admins)
                txt_only_msgs = self.add_replies_to_messages_and_extract_text(current_msgs)
                with open(
                    rf"{GROUP_CHAT_EXTRACTOR_DIR}\extracted_messages.txt", "a", encoding="utf-8", errors="ignore"
                ) as f:
                    n_msgs = ["{}\n".format(msg) for msg in txt_only_msgs]
                    f.writelines(n_msgs)
                previous_id = current_id
                current_id = current_id + 1000
                self.remove_spaces_from_file()
                while GV.ProgramStatus == GV.PROGRAM_STATUS["IDLE"]:
                    time.sleep(1 / 30)
                    continue

                if GV.ProgramStatus == GV.PROGRAM_STATUS["STOP"]:
                    self.running = False
                    break

    def get_group_to_scrape(self, list_of_groups: List[str]):
        text = r"Please enter number of group to scrape users: \n"
        i = 0
        for g in list_of_groups:
            text += f"{str(i)} -  {g.title} \n"
            i += 1

        new_win = Tk()
        new_win.withdraw()
        group_no = simpledialog.askinteger(
            "Group to Scrape", text, parent=new_win, minvalue=0, maxvalue=(len(list_of_groups) - 1)
        )

        new_win.destroy()

        return list_of_groups[group_no]

    def run(self):
        self.running = True
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            if self.client_mode:
                client = self.get_client_from_session()
            else:
                client = self.get_client_from_phone()

            if client:
                if not self.group:
                    raise Exception("No group given for scraping.")
                group_info = self.join_group(self.group[0], client)
            else:
                raise Exception("No client found.")

            # empty file
            with open(
                rf"{GROUP_CHAT_EXTRACTOR_DIR}\extracted_messages.txt", "w+", encoding="utf-8", errors="ignore"
            ) as f:
                ...
            chats, groups, targets = self.get_necessary_info(client)
            group = self.get_group_to_scrape(groups)
            admins = self.scrape_admins_from_group(client, group)
            if self.message_scrape_option:
                self.scrape_messages(
                    client=client,
                    group=group,
                    admins=admins,
                    start_date=self.start_date_user_filter,
                    end_date=self.end_date_user_filter,
                )
            else:
                self.scrape_messages(client=client, group=group, admins=admins)

        except Exception as e:
            logger.exception(f"Unexpected exception occured: {str(e)}")

            try:
                client.disconnect()
            except Exception:
                pass

    # def write_users(self, userlist):
    #     if self.user_add_option:
    #         with open(rf"{AUTO_REGISTER_PATH_DIR}\user_ids.txt", "w+") as f:
    #             n_userlist = ["{}\n".format(user) for user in userlist]
    #             f.writelines(n_userlist)
    #     else:
    #         with open(rf"{AUTO_REGISTER_PATH_DIR}\usernames.txt", "w+") as f:
    #             n_userlist = ["{}\n".format(user) for user in userlist]
    #             f.writelines(n_userlist)

    # def clean_up_duplicates_from_files(self, filename: str):
    #     with open(rf"{AUTO_REGISTER_PATH_DIR}\{filename}.txt", "r", encoding="utf-8", errors="ignore") as f:
    #         extracted_users = f.readlines()

    #     # remove duplicates
    #     with open(rf"{AUTO_REGISTER_PATH_DIR}\{filename}.txt", "w+", encoding="utf-8", errors="ignore") as f:
    #         extracted_users = list(set(extracted_users))
    #         f.writelines(extracted_users)
