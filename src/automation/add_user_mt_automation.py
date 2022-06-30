import asyncio
import os
import shutil
import time
import tkinter.messagebox as tkmb
from cgitb import reset
from datetime import datetime
from re import I, T
from sys import exit
from time import sleep
from tkinter import Tk, simpledialog
from tokenize import group
from typing import List

import aiofiles
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
from src.utils.paths import AUTO_REGISTER_PATH_DIR

from .abstract_automation import AbstractAutomation
from .exceptions_automation import (
    CannotOpenLoadPhoneNumbers,
    ClientNotAuthorizedException,
    NoTelegramApiInfoFoundAddUserException,
)


class AddUserMt(AbstractAutomation):
    def __init__(
        self,
        run_mode: int,
        client_mode: int,
        max_session: str,
        code_required: int,
        user_delay: str,
        proxy_enabled: int,
        threading_option: int,
        user_scrape_option: int,
        user_add_option: int,
        start_date_user_filter: datetime,
        end_date_user_filter: datetime,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.run_mode = run_mode
        self.client_mode = client_mode
        self.groups = self.read_file_with_property(path=AUTO_REGISTER_PATH_DIR, filename="groups")
        self.apis = self.read_file_with_property(path=AUTO_REGISTER_PATH_DIR, filename="api")
        self.added_user_ids = self.read_file_with_property(path=AUTO_REGISTER_PATH_DIR, filename="added_user_ids")
        self.group_to_scrape = self.read_file_with_property(path=AUTO_REGISTER_PATH_DIR, filename="group_to_scrape")

        self.sessions = self.read_all_sessions(path=AUTO_REGISTER_PATH_DIR)
        self.code_required = code_required
        if self.client_mode == 1 and int(max_session):
            self.max_sessions = int(max_session)
            self.sessions = self.sessions[: self.max_sessions]

        if self.client_mode == 0:
            self.phones = self.load_phone_numbers()

        self.user_delay = float(user_delay)
        if proxy_enabled:
            self.proxies = self.read_file_with_property(path=AUTO_REGISTER_PATH_DIR, filename="proxies")
        else:
            self.proxies = []
        self.threading_option = threading_option
        self.user_scrape_option = user_scrape_option
        self.user_add_option = user_add_option
        self.start_date_user_filter = start_date_user_filter
        self.end_date_user_filter = end_date_user_filter
        if end_date_user_filter < start_date_user_filter and self.user_scrape_option:
            logger.error("Start date should be smaller than end date.")
            raise Exception("Start date should be smaller than end date.")

    def load_phone_numbers(self):
        try:
            with open(rf"{AUTO_REGISTER_PATH_DIR}\sessions\phones.txt", "r") as phone_file:
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

    async def join_groups(self, groups: List, clients: List[TelegramClient]):
        cid = []
        ah = []
        for client in clients:
            for group in groups:
                if "/" in group:
                    group_link = group.split("/")[-1]
                    try:
                        try:
                            updates = await client(ImportChatInviteRequest(group_link))
                            cid.append(updates.chats[0].id)
                            ah.append(updates.chats[0].access_hash)
                        except Exception as e:
                            chatinvite = await client(CheckChatInviteRequest(group_link))
                            cid.append(chatinvite.chat.id)
                            ah.append(chatinvite.chat.access_hash)
                            print(e)
                            pass
                    except Exception as e:
                        logger.error(f"Error occured: {str(e)}")
                else:
                    client_me = await client.get_me()
                    print(client_me.phone, "joined group", group)
                    group_entity_scrapped = await client.get_entity(group)
                    updates = await client(JoinChannelRequest(group_entity_scrapped))
                    cid.append(updates.chats[0].id)
                    ah.append(updates.chats[0].access_hash)
        res = [cid, ah]
        return res

    def get_clients_from_phones(self):
        clients = []
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

                    formatted_proxy = None
                    current_proxy = None
                    if self.proxies:
                        current_proxy = self.proxies[0]
                        formatted_proxy = self.read_txt_proxy(current_proxy)  # type: ignore
                        logger.info(f"Proxy will be used: {formatted_proxy['addr']}")
                    retry_count = 0
                    while retry_count < 5:
                        try:
                            telegram_client = TelegramClient(
                                rf"{AUTO_REGISTER_PATH_DIR}\sessions\{phone}",
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
                                    path=AUTO_REGISTER_PATH_DIR, filename="proxies", new_list=self.proxies
                                )
                                current_proxy = self.proxies[0]
                                formatted_proxy = self.read_txt_proxy(current_proxy)  # type: ignore
                                if self.tw_instance and self.tw_instance.client:
                                    if self.tw_instance.client.is_connected():
                                        self.tw_instance.client.disconnect()
                        finally:
                            retry_count += 1

                    self.tw_instance.client.flood_sleep_threshold = 0
                    clients.append(self.tw_instance.client)

                    # Remove api
                    self.apis.remove(self.apis[0])
                    self.write_list_to_file(path=AUTO_REGISTER_PATH_DIR, filename="api", new_list=self.apis)

                    # Remove proxy
                    if current_proxy and self.proxies:
                        self.proxies.remove(current_proxy)
                        self.write_list_to_file(path=AUTO_REGISTER_PATH_DIR, filename="proxies", new_list=self.proxies)
                except NoTelegramApiInfoFoundAddUserException as e:
                    self.write_list_to_file(
                        path=rf"{AUTO_REGISTER_PATH_DIR}\sessions", filename="phones", new_list=self.phones_copy
                    )
                    tkmb.showerror("Error Occured", "No telegram api info found.")
                    raise e
                except Exception as e:
                    # Clean up
                    self.phones_copy.remove(phone)
                    self.write_list_to_file(
                        path=rf"{AUTO_REGISTER_PATH_DIR}\sessions", filename="phones", new_list=self.phones_copy
                    )
                    self.delete_unsuccessful_session(phone)
                    logger.exception(f"Exception occured with {str(e)}")

        return clients

    def get_clients_from_sessions(self):
        clients = []

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

                    formatted_proxy = None
                    current_proxy = None
                    if self.proxies:
                        current_proxy = self.proxies[0]
                        formatted_proxy = self.read_txt_proxy(current_proxy)  # type: ignore
                        logger.info(f"Proxy will be used: {formatted_proxy['addr']}")
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
                                    path=AUTO_REGISTER_PATH_DIR, filename="proxies", new_list=self.proxies
                                )
                                current_proxy = self.proxies[0]
                                if (
                                    self.tw_instance
                                    and self.tw_instance.client
                                    and self.tw_instance.client.is_connected()
                                ):
                                    self.tw_instance.client.disconnect()
                        finally:
                            retry_count += 1

                    self.tw_instance.client.flood_sleep_threshold = 0
                    clients.append(self.tw_instance.client)

                    # Remove api
                    self.apis.remove(self.apis[0])
                    self.write_list_to_file(path=AUTO_REGISTER_PATH_DIR, filename="api", new_list=self.apis)

                    # Remove proxy
                    if current_proxy and self.proxies:
                        self.proxies.remove(current_proxy)
                        self.write_list_to_file(path=AUTO_REGISTER_PATH_DIR, filename="proxies", new_list=self.proxies)
                except NoTelegramApiInfoFoundAddUserException as e:
                    tkmb.showerror("Error Occured", "No telegram api info found.")
                    raise e
                except Exception as e:
                    logger.exception(f"Exception occured with {str(e)}")

        return clients

    def delete_unsuccessful_session(self, phone: str):
        if self.tw_instance and self.tw_instance.client:
            self.tw_instance.client.disconnect()
            if os.path.isfile(f"{AUTO_REGISTER_PATH_DIR}\\sessions\\{phone}.session"):
                os.remove(f"{AUTO_REGISTER_PATH_DIR}\\sessions\\{phone}.session")

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

    async def scrape_users_from_groups(self, client: TelegramClient, group):
        logger.info("Starts scraping channel.")
        all_participants = []
        limit = 1000

        admins = await client(
            GetParticipantsRequest(
                channel=InputPeerChannel(group.id, group.access_hash),
                filter=ChannelParticipantsAdmins(),
                offset=0,
                limit=limit,
                hash=0,
            )
        )
        client.flood_sleep_threshold = 100
        while GV.ProgramStatus == GV.PROGRAM_STATUS["IDLE"]:
            await asyncio.sleep(1 / 30)
            continue

        if GV.ProgramStatus == GV.PROGRAM_STATUS["STOP"]:
            self.running = False
        try:
            async for participant in client.iter_participants(group, aggressive=True):
                all_participants.append(participant)

        except Exception as e:
            logger.error(f"Cannot extract users due to : {str(e)}")

        # all_participants.extend(list(participants))
        await asyncio.sleep(1)
        logger.info(len(all_participants))
        logger.info(
            f"{str(client._self_id)} extracted length of groups - {str(len(all_participants))}",
        )
        # Filter out admins
        logger.info("Filtering out admin accounts...")
        all_participants = [participant for participant in all_participants if participant not in admins.users]

        return all_participants

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

    def run(self):
        self.running = True
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        clients = []
        try:
            if self.client_mode:
                clients = self.get_clients_from_sessions()
            else:
                clients = self.get_clients_from_phones()

            if clients and self.run_mode == 0:
                if not self.group_to_scrape:
                    raise Exception("No group given for scraping.")
                group_info = loop.run_until_complete(self.join_groups(self.group_to_scrape, clients))
                chats, groups, targets = self.get_necessary_info(clients[0])
            elif clients and self.run_mode == 1:
                if not self.groups:
                    raise Exception("No group given for adding users.")
                group_info = loop.run_until_complete(self.join_groups(self.groups, clients))
            else:
                raise Exception("No client found.")

            if self.run_mode == 0:
                # Open file to empty it
                with open(rf"{AUTO_REGISTER_PATH_DIR}\usernames.txt", "w+", encoding="utf-8", errors="ignore") as f:
                    ...
                # Open file to empty it
                with open(rf"{AUTO_REGISTER_PATH_DIR}\user_ids.txt", "w+", encoding="utf-8", errors="ignore") as f:
                    ...
                tasks = []

                # append tasks for each client
                group = self.get_group_to_scrape(groups)
                for client in clients:
                    chats, groups, targets = self.get_necessary_info(client)
                    group = [group for group in groups if group.id == group.id][0]
                    tasks.append(self.scrape_users_from_groups(client, group=group))

                results = loop.run_until_complete(asyncio.gather(*tasks))

                logger.info("Scraping Completed")

                self.clean_up_duplicates_from_files("usernames")
                self.clean_up_duplicates_from_files("user_ids")

                # # append tasks for each client
                # group = self.get_group_to_scrape(groups)
                # result = loop.run_until_complete(self.scrape_users_from_groups(clients[0], group=group))
                result = results[0]
                logger.info("Filter out added users.")
                result = [user for user in result if user.id not in self.added_user_ids]
                if self.user_scrape_option == 1:
                    local = pytz.timezone("UTC")
                    last_month_date = local.localize(datetime.utcnow()) - relativedelta(months=1)
                    last_week_date = local.localize(datetime.utcnow()) - relativedelta(weeks=1)
                    total_participants = []
                    user_recent = [user for user in result if isinstance(user.status, UserStatusRecently)]
                    user_online = [user for user in result if isinstance(user.status, UserStatusOnline)]
                    user_lastmonth = []
                    if (datetime.now().date() - self.start_date_user_filter).days > 30 and (
                        datetime.now().date() - self.end_date_user_filter
                    ).days < 30:
                        user_lastmonth = [user for user in result if isinstance(user.status, UserStatusLastMonth)]
                    user_lastweek = []
                    if (datetime.now().date() - self.start_date_user_filter).days > 7 and (
                        datetime.now().date() - self.end_date_user_filter
                    ).days < 7:
                        user_lastweek = [user for user in result if isinstance(user.status, UserStatusLastWeek)]

                    user_offline = [user for user in result if isinstance(user.status, UserStatusOffline)]
                    # Filter with main date
                    user_offline = list(
                        filter(
                            lambda user: (user.status.was_online.date() >= self.start_date_user_filter)
                            and (user.status.was_online.date() <= self.end_date_user_filter),
                            user_offline,
                        )
                    )
                    user_offline.sort(key=lambda user: user.status.was_online, reverse=True)

                    user_offline_last_week = list(
                        filter(
                            lambda user: user.status.was_online >= last_week_date,
                            user_offline,
                        )
                    )
                    user_offline_last_month = list(
                        filter(
                            lambda user: (user.status.was_online >= last_month_date)
                            and (user.status.was_online < last_week_date),
                            user_offline,
                        )
                    )
                    user_older_than_a_month = list(
                        filter(
                            lambda user: user.status.was_online < last_month_date,
                            user_offline,
                        )
                    )

                    total_participants.extend(user_online)
                    total_participants.extend(user_recent)
                    total_participants.extend(user_offline_last_week)
                    total_participants.extend(user_lastweek)
                    total_participants.extend(user_offline_last_month)
                    total_participants.extend(user_lastmonth)
                    total_participants.extend(user_older_than_a_month)

                else:
                    total_participants = result

                loop.run_until_complete(self.save_scraped_list(total_participants))

                logger.info("Scraping Completed")

                self.clean_up_duplicates_from_files("usernames")
                self.clean_up_duplicates_from_files("user_ids")

            elif self.run_mode == 1:
                if self.user_add_option:
                    with open(rf"{AUTO_REGISTER_PATH_DIR}\user_ids.txt", "r", encoding="utf-8", errors="ignore") as f:
                        _temp = f.read()
                        userlist = _temp.split("\n")
                        userlist = userlist[:-1]
                else:
                    with open(rf"{AUTO_REGISTER_PATH_DIR}\usernames.txt", "r", encoding="utf-8", errors="ignore") as f:
                        _temp = f.read()
                        userlist = _temp.split("\n")
                        userlist = userlist[:-1]

                if self.threading_option:
                    while clients and userlist:
                        tasks = []

                        counter = 0
                        total_divider = int(len(userlist) / len(clients))

                        # append tasks for each client
                        for client in clients:
                            if counter == (len(clients) - 1):
                                tasks.append(
                                    self.add_users_to_groups(
                                        client=client,
                                        userlist=userlist[counter * total_divider :],
                                        group_info=group_info,
                                        counter=counter,
                                    )
                                )
                                break

                            tasks.append(
                                self.add_users_to_groups(
                                    client=client,
                                    userlist=userlist[
                                        counter * total_divider : (counter * total_divider + total_divider)
                                    ],
                                    group_info=group_info,
                                    counter=counter,
                                )
                            )
                            counter += 1

                        result = loop.run_until_complete(asyncio.gather(*tasks))

                        userlist = []
                        clients = []

                        for user, client_stat, added_users in result:
                            userlist.extend(user)
                            if self.user_add_option:
                                self.added_user_ids.extend(added_users)
                            for key, value in client_stat.items():
                                if value:
                                    clients.append(key)

                        self.write_users(userlist=userlist)
                        if self.user_add_option:
                            self.write_list_to_file(AUTO_REGISTER_PATH_DIR, "added_user_ids", self.added_user_ids)

                        if GV.ProgramStatus == GV.PROGRAM_STATUS["STOP"]:
                            break
                else:
                    counter = 0
                    for client in clients:
                        # to stop processing further
                        if len(userlist) == 0:
                            logger.info("No users found to add. Please first scrape users.")
                            break
                        result = loop.run_until_complete(
                            self.add_users_to_groups(
                                client=client,
                                userlist=userlist,
                                group_info=group_info,
                                counter=counter,
                            )
                        )
                        if GV.ProgramStatus == GV.PROGRAM_STATUS["STOP"]:
                            break

                        userlist.extend(result[0])

                        self.write_users(userlist=userlist)
                        counter += 1

                        if GV.ProgramStatus == GV.PROGRAM_STATUS["STOP"]:
                            break

        except Exception as e:
            logger.exception(f"Unexpected exception occured: {str(e)}")

        for client in clients:
            try:
                client.disconnect()
            except Exception:
                continue

    def write_users(self, userlist):
        if self.user_add_option:
            with open(rf"{AUTO_REGISTER_PATH_DIR}\user_ids.txt", "w+") as f:
                n_userlist = ["{}\n".format(user) for user in userlist]
                f.writelines(n_userlist)
        else:
            with open(rf"{AUTO_REGISTER_PATH_DIR}\usernames.txt", "w+") as f:
                n_userlist = ["{}\n".format(user) for user in userlist]
                f.writelines(n_userlist)

    def clean_up_duplicates_from_files(self, filename: str):
        with open(rf"{AUTO_REGISTER_PATH_DIR}\{filename}.txt", "r", encoding="utf-8", errors="ignore") as f:
            extracted_users = f.readlines()

        # remove duplicates
        with open(rf"{AUTO_REGISTER_PATH_DIR}\{filename}.txt", "w+", encoding="utf-8", errors="ignore") as f:
            extracted_users = list(set(extracted_users))
            f.writelines(extracted_users)
