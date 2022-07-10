import asyncio
import os
import shutil
import time
import tkinter.messagebox as tkmb
import uuid
from cgitb import reset
from datetime import datetime
from email import message
from lib2to3.pgen2.token import NAME
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
from src.utils.paths import NAME_EXTRACTOR_DIR

from .abstract_automation import AbstractAutomation
from .exceptions_automation import (
    CannotOpenLoadPhoneNumbers,
    ClientNotAuthorizedException,
    NoTelegramApiInfoFoundAddUserException,
)


class NameScraperFromGroup(AbstractAutomation):
    def __init__(
        self,
        client_mode: int,
        max_names: str,
        code_required: int,
        name_scraping_option: int,
        extraction_opts: int,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.client_mode = client_mode
        self.name_scraping_option = name_scraping_option
        self.extraction_opts = extraction_opts
        self.group = self.read_file_with_property(path=NAME_EXTRACTOR_DIR, filename="group")
        self.apis = self.read_file_with_property(path=NAME_EXTRACTOR_DIR, filename="api")
        self.max_names = int(max_names)
        self.sessions = self.read_all_sessions(path=NAME_EXTRACTOR_DIR)
        self.code_required = code_required

        if self.client_mode == 0:
            self.phones = self.load_phone_numbers()

    def load_phone_numbers(self):
        try:
            with open(rf"{NAME_EXTRACTOR_DIR}\sessions\phones.txt", "r") as phone_file:
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
                                rf"{NAME_EXTRACTOR_DIR}\sessions\{phone}",
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
                    self.write_list_to_file(path=NAME_EXTRACTOR_DIR, filename="api", new_list=self.apis)

                    # Remove proxy
                    # if current_proxy and self.proxies:
                    #     self.proxies.remove(current_proxy)
                    #     self.write_list_to_file(path=AUTO_REGISTER_PATH_DIR, filename="proxies", new_list=self.proxies)
                    return self.tw_instance.client

                except NoTelegramApiInfoFoundAddUserException as e:
                    self.write_list_to_file(
                        path=rf"{NAME_EXTRACTOR_DIR}\sessions", filename="phones", new_list=self.phones_copy
                    )
                    tkmb.showerror("Error Occured", "No telegram api info found.")
                    raise e
                except Exception as e:
                    # Clean up
                    self.phones_copy.remove(phone)
                    self.write_list_to_file(
                        path=rf"{NAME_EXTRACTOR_DIR}\sessions", filename="phones", new_list=self.phones_copy
                    )
                    self.delete_unsuccessful_session(phone)
                    logger.exception(f"Exception occured with {str(e)}")

    def get_client_from_session(self) -> TelegramClient:
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
                    self.write_list_to_file(path=NAME_EXTRACTOR_DIR, filename="api", new_list=self.apis)

                    return self.tw_instance.client
                except NoTelegramApiInfoFoundAddUserException as e:
                    tkmb.showerror("Error Occured", "No telegram api info found.")
                    raise e
                except Exception as e:
                    logger.exception(f"Exception occured with {str(e)}")

    def delete_unsuccessful_session(self, phone: str):
        if self.tw_instance and self.tw_instance.client:
            self.tw_instance.client.disconnect()
            if os.path.isfile(f"{NAME_EXTRACTOR_DIR}\\sessions\\{phone}.session"):
                os.remove(f"{NAME_EXTRACTOR_DIR}\\sessions\\{phone}.session")

    def scrape_users_from_groups(self, client: TelegramClient, group, limit_of_return: int = None):
        logger.info("Starts scraping channel.")
        all_participants = []
        limit = 1000

        admins = client(
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
            time.sleep(1 / 30)
            continue

        if GV.ProgramStatus == GV.PROGRAM_STATUS["STOP"]:
            self.running = False
        try:
            if limit_of_return:
                all_participants = client.get_participants(group, aggressive=True, limit=limit_of_return)
            else:
                all_participants = client.get_participants(group, aggressive=True)
        except Exception as e:
            logger.error(f"Cannot extract users due to : {str(e)}")

        time.sleep(1)
        logger.info(
            f"{str(client._self_id)} extracted length of groups - {str(len(all_participants))}",
        )
        # Filter out admins
        logger.info("Filtering out admin accounts...")
        all_participants = [participant for participant in all_participants if participant not in admins.users]

        return all_participants

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

    def remove_admins_from_list(self, messages, admins):
        logger.info("Removing admin messages.")
        admin_user_ids = [participant.user_id for participant in admins.participants]
        messages = [msg for msg in messages if msg.sender_id not in admin_user_ids]

        return messages

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

    def write_to_file_names(self, names):
        with open(rf"{NAME_EXTRACTOR_DIR}\extracted_user_names.txt", "a", encoding="utf-8", errors="ignore") as f:
            n_names = ["{}\n".format(msg) for msg in names]
            f.writelines(n_names)

    async def extract_profile_photo(self, client: TelegramClient, scraped_users):
        for user in scraped_users:
            while GV.ProgramStatus == GV.PROGRAM_STATUS["IDLE"]:
                time.sleep(1 / 30)
                continue

            if GV.ProgramStatus == GV.PROGRAM_STATUS["STOP"]:
                self.running = False
                break
            if user.photo:
                if user.photo.has_video:
                    extension = "gif"
                else:
                    extension = "jpg"

                await client.download_profile_photo(
                    user.id, file=rf"{NAME_EXTRACTOR_DIR}\profile_pictures\{str(uuid.uuid4())}.{extension}"
                )

    async def extract_name(self, scraped_users):
        all_names = []
        counter = 0
        for user in scraped_users:
            if user.first_name:
                first_name = user.first_name
            else:
                continue

            if user.last_name:
                full_name = first_name + " " + user.last_name
            else:
                full_name = first_name

            all_names.append(emoji.demojize(full_name))
            while GV.ProgramStatus == GV.PROGRAM_STATUS["IDLE"]:
                time.sleep(1 / 30)
                continue

            if GV.ProgramStatus == GV.PROGRAM_STATUS["STOP"]:
                self.running = False
                break
            if counter == 100:
                counter = 0
                self.write_to_file_names(all_names)
                all_names = []
            counter += 1
        if all_names:
            self.write_to_file_names(all_names)

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
            with open(rf"{NAME_EXTRACTOR_DIR}\extracted_user_names.txt", "w+", encoding="utf-8", errors="ignore") as f:
                ...

            chats, groups, targets = self.get_necessary_info(client)
            group = self.get_group_to_scrape(groups)

            if self.name_scraping_option:
                scraped_users = self.scrape_users_from_groups(
                    client=client, group=group, limit_of_return=self.max_names
                )
            else:
                scraped_users = self.scrape_users_from_groups(
                    client=client, group=group, limit_of_return=self.max_names
                )

            if self.extraction_opts == 0:
                loop.run_until_complete(self.extract_profile_photo(client, scraped_users))
            elif self.extraction_opts == 1:
                loop.run_until_complete(self.extract_name(scraped_users))
            else:
                loop.run_until_complete(
                    asyncio.gather(self.extract_profile_photo(client, scraped_users), self.extract_name(scraped_users))
                )

            client.disconnect()
            logger.info("Extraction completed.")
        except Exception as e:
            logger.exception(f"Unexpected exception occured: {str(e)}")

            try:
                client.disconnect()
            except Exception:
                pass
