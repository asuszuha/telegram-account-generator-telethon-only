import asyncio
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
from src.utils.paths import AUTO_REGISTER_PATH_DIR

from .abstract_automation import AbstractAutomation
from .exceptions_automation import (
    CannotOpenLoadPhoneNumbers,
    ClientNotAuthorizedException,
    NoTelegramApiInfoFoundAddUserException,
)


class AddUser(AbstractAutomation):
    def __init__(
        self,
        run_mode: int,
        client_mode: int,
        max_session: str,
        code_required: int,
        user_delay: str,
        proxy_enabled: int,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.run_mode = run_mode
        self.client_mode = client_mode
        self.groups = self.read_file_with_property(path=AUTO_REGISTER_PATH_DIR, filename="groups")
        self.apis = self.read_file_with_property(path=AUTO_REGISTER_PATH_DIR, filename="api")
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

    def disconnect_all_clients(self, clients: List[TelegramClient]):
        for client in clients:
            try:
                if client.is_connected():
                    client.disconnect()
            except Exception:
                pass

    def join_groups(self, clients: List[TelegramClient]):
        cid = []
        ah = []
        for client in clients:
            for group in self.groups:
                if "/" in group:
                    group_link = group.split("/")[-1]
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
                else:
                    print(client.client.get_me().phone, "joined group", group)
                    group_entity_scrapped = client.get_entity(group)
                    updates = client(JoinChannelRequest(group_entity_scrapped))
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
                    if self.tw_instance and self.tw_instance.client:
                        self.tw_instance.client.loop.stop()
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
                                if self.tw_instance and self.tw_instance.client:
                                    if self.tw_instance.client.is_connected():
                                        self.tw_instance.client.disconnect()
                        finally:
                            retry_count += 1

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
                    if self.tw_instance and self.tw_instance.client:
                        self.tw_instance.client.loop.stop()
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
                    if self.tw_instance and self.tw_instance.client:
                        self.tw_instance.client.loop.stop()
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

    def scrape_users_from_groups(self, clients: List[TelegramClient], groups: List):
        group = self.get_group_to_scrape(groups)
        logger.info("Starts scraping channel.")
        chat_id_from = group.id  # type: ignore
        target_groups_from = []
        last_date = None
        chunk_size = 100

        for client in clients:
            with self.pause_cond:
                while self.paused:
                    self.pause_cond.wait()

                if self.stopped:
                    if self.tw_instance and self.tw_instance.client:
                        self.tw_instance.client.loop.stop()
                    self.running = False
                    break

                chats = []
                i = 0
                while True:
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
                        try:
                            if msg.access_hash is not None:
                                if msg.id == chat_id_from:
                                    target_groups_from.append(msg)
                        except Exception:
                            pass
                    i += 1
                    sleep(1)

            if len(target_groups_from) != len(clients):
                logger.info("All accounts should be a member of both groups.")

            groups_participants = []
            i = 0
            for client in clients:
                all_participants = []
                offset = 0
                limit = 1000
                while True:
                    participants = client(
                        GetParticipantsRequest(
                            InputPeerChannel(target_groups_from[i].id, target_groups_from[i].access_hash),
                            ChannelParticipantsSearch(""),
                            offset,
                            limit,
                            hash=0,
                        )
                    )
                    if not participants.users:
                        break
                    all_participants.extend(participants.users)
                    offset += len(participants.users)
                    sleep(1)
                i += 1
                logger.info(len(all_participants))
                groups_participants.append(all_participants)
                logger.info(
                    f" length of groups - {str(len(groups_participants[0]))}",
                )

            try:
                logger.info("Saving user list...")
                with open(rf"{AUTO_REGISTER_PATH_DIR}\user.txt", "w+", encoding="utf-8", errors="ignore") as f:
                    for item in groups_participants[0]:
                        if item.username is not None:
                            f.write("%s\n" % (item.username))
                logger.info("Saving Done...")
            except Exception as e:
                logger.exception("Error occured during saving...")
                logger.exception(e)
            logger.info("Scraping Completed")

    def move_current_session(self, client: TelegramClient):
        if client.is_connected():
            phone = client.get_me().phone
            client.disconnect()

            session = rf"{AUTO_REGISTER_PATH_DIR}\sessions\+{phone}.session"
            if not os.path.exists(session):
                session = rf"{AUTO_REGISTER_PATH_DIR}\sessions\{phone}.session"
            session_filename = session.split("\\")[-1]
            if os.path.exists(session):
                shutil.move(session, rf"{AUTO_REGISTER_PATH_DIR}\used_sessions\{session_filename}")
            else:
                raise Exception(f"Session file not found {session}. So it cannot be moved.")

    def add_users_to_groups(self, clients: List[TelegramClient]):
        peer_flooded = []
        too_many_request = []
        wait_seconds = []
        other_exceptions = []
        [cid, ah] = self.join_groups(clients)
        print("List of groups:")
        ii = 0
        userlist = []
        with open(rf"{AUTO_REGISTER_PATH_DIR}\user.txt", "r", encoding="utf-8", errors="ignore") as f:
            _temp = f.read()
            userlist = _temp.split("\n")
            userlist = userlist[:-1]

        for index, user in enumerate(userlist, 1):
            with self.pause_cond:
                while self.paused:
                    self.pause_cond.wait()

                if self.stopped:
                    if self.tw_instance and self.tw_instance.client:
                        self.tw_instance.client.loop.stop()
                    self.running = False
                    break
                try:
                    __user = clients[ii].get_entity(user)
                    logger.info(f"Adding user : {user} by {str(clients[ii].get_me().phone)}")
                    clients[ii](
                        InviteToChannelRequest(
                            InputChannel(cid[ii], ah[ii]),
                            [__user],
                        )
                    )
                    with open(rf"{AUTO_REGISTER_PATH_DIR}\user.txt", "w+", encoding="utf-8", errors="ignore") as f:
                        for item in userlist[index:]:
                            f.write("%s\n" % (item))
                        for pf in peer_flooded:
                            f.write("%s\n" % (pf))
                    peer_flooded = []
                    too_many_request = []
                    wait_seconds = []
                    other_exceptions = []
                    time.sleep(self.user_delay)
                except Exception as e:
                    time.sleep(self.user_delay)
                    if "PEER_FLOOD" in str(e):
                        peer_flooded.append(user)
                        if len(peer_flooded) > 7:
                            if ii < len(clients) - 1:
                                logger.info(
                                    (
                                        f"switching to {str(clients[ii + 1].get_me().phone)} "
                                        f"after peerflood {str(len(peer_flooded))} times"
                                    )
                                )
                                time.sleep(3)
                                if self.client_mode:
                                    try:
                                        self.move_current_session(clients[ii])
                                    except Exception:
                                        logger.exception("Cannot move to session.")
                                ii += 1
                                peer_flooded = []
                            else:
                                logger.info("all accounts peer flooded")
                                if self.client_mode:
                                    for client in clients:
                                        try:
                                            self.move_current_session(client)
                                        except Exception:
                                            logger.exception("Cannot move to session.")
                                self.disconnect_all_clients(clients=clients)
                                exit()
                    elif "privacy" in str(e):
                        with open(rf"{AUTO_REGISTER_PATH_DIR}\user.txt", "w+", encoding="utf-8", errors="ignore") as f:
                            for item in userlist[index:]:
                                f.write("%s\n" % (item))
                        time.sleep(self.user_delay)
                    elif "Too many requests" in str(e):
                        time.sleep(self.user_delay)
                        too_many_request.append(user)
                        if len(too_many_request) > 7:
                            if ii < len(clients) - 1:
                                logger.info(
                                    (
                                        f"switching to {str(clients[ii + 1].get_me().phone)} "
                                        f"after Too many request {str(len(too_many_request))} times"
                                    )
                                )
                                time.sleep(3)
                                if self.client_mode:
                                    try:
                                        self.move_current_session(clients[ii])
                                    except Exception:
                                        logger.exception("Cannot move to session.")
                                ii += 1
                                too_many_request = []
                            else:
                                if self.client_mode:
                                    for client in clients:
                                        try:
                                            self.move_current_session(client)
                                        except Exception:
                                            logger.exception("Cannot move to session.")
                                logger.info("all accounts too many request")
                                self.disconnect_all_clients(clients=clients)
                                exit()
                    elif "wait" in str(e):
                        time.sleep(self.user_delay)
                        wait_seconds.append(user)
                        if len(wait_seconds) > 7:
                            if ii < len(clients) - 1:
                                logger.info(
                                    (
                                        f"switching to {str(clients[ii + 1].get_me().phone)} "  # type: ignore
                                        f"after wait seconds is required {str(len(wait_seconds))} times"
                                    )
                                )
                                time.sleep(3)
                                if self.client_mode:
                                    try:
                                        self.move_current_session(clients[ii])
                                    except Exception:
                                        logger.exception("Cannot move to session.")
                                ii += 1
                                wait_seconds = []
                            else:
                                if self.client_mode:
                                    for client in clients:
                                        try:
                                            self.move_current_session(client)
                                        except Exception:
                                            logger.exception("Cannot move to session.")
                                self.disconnect_all_clients(clients=clients)
                                logger.info("all accounts wait seconds is required")
                                exit()
                    elif "privacy" not in str(e):
                        time.sleep(self.user_delay)
                        other_exceptions.append(user)
                        if len(other_exceptions) > 7:
                            if ii < len(clients) - 1:
                                logger.info(
                                    (
                                        f"switching to {str(clients[ii + 1].get_me().phone)} "  # type: ignore
                                        "after other errors {str(len(other_exceptions))} times"
                                    )
                                )
                                time.sleep(3)
                                if self.client_mode:
                                    try:
                                        self.move_current_session(clients[ii])
                                    except Exception:
                                        logger.exception("Cannot move to session.")
                                ii += 1
                                other_exceptions = []
                            else:
                                if self.client_mode:
                                    for client in clients:
                                        try:
                                            self.move_current_session(client)
                                        except Exception:
                                            logger.exception("Cannot move to session.")
                                self.disconnect_all_clients(clients=clients)
                                logger.info("all accounts other error occurs")
                                exit()
                    elif "Keyboard" in str(e):
                        time.sleep(self.user_delay)
                        if ii < len(clients) - 1:
                            if self.client_mode:
                                try:
                                    self.move_current_session(clients[ii])
                                except Exception:
                                    logger.exception("Cannot move to session.")
                            ii += 1
                        else:
                            if self.client_mode:
                                try:
                                    clients[ii].disconnect()
                                    self.move_current_session(clients[ii])
                                except Exception:
                                    logger.exception("Cannot move to session.")
                            break
                    logger.info(e)
                    pass

        logger.info("Adding Completed.")

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
            if clients:
                chats, groups, targets = self.get_necessary_info(clients[0])
            else:
                raise Exception("No client found.")
            if self.run_mode == 0:
                self.scrape_users_from_groups(clients, groups=groups)
            elif self.run_mode == 1:
                self.add_users_to_groups(clients=clients)
        except Exception as e:
            logger.exception(f"Unexpected exception occured: {str(e)}")

        for client in clients:
            try:
                client.disconnect()
            except Exception:
                continue
