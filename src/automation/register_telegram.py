import asyncio
import os
import platform
import time
import tkinter.messagebox as tkmb
from typing import List, Union

from telethon import TelegramClient

from src.automation.abstract_automation import AbstractAutomation
from src.utils.logger import logger
from src.utils.sim5_net import NoFreePhoneException, PurchaseNotPossibleException, Sim5Net
from src.utils.sms_activate import NoNumbersException, SmsActivate

from .telethon_wrapper import NumberBannedException, TelethonWrapper


class RegisterTelegramException(Exception):
    pass


class CannotRetrieveSMSCode(RegisterTelegramException):
    pass


class RegisterTelegram(AbstractAutomation):
    def __init__(
        self,
        sms_operator: Union[Sim5Net, SmsActivate],
        sms_timeout: str,
        country: str,
        tg_api_id: str,
        tg_api_hash: str,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.sms_operator = sms_operator
        self.country = country

        # Init from files
        self.names = self.read_file_with_property("names")
        self.devices = self.read_file_with_property("devices")
        self.proxies = self.read_file_with_property("proxies")
        self.abouts = self.read_file_with_property("about")
        self.passwords = self.read_file_with_property("passwords")
        self.output_dir = "output"
        self.profile_pics_path = "profile_pics"
        self._list_of_profile_pics_path = os.listdir(self.profile_pics_path)

        self.tg_api_id = tg_api_id
        self.tg_api_hash = tg_api_hash

        self.sms_timeout = int(sms_timeout)

    def read_file_with_property(self, filename: str):
        if os.path.exists(f"data\\{filename}.txt"):
            with open(f"data\\{filename}.txt", "r") as fh:
                return [line.replace("\\n", "") for line in fh.readlines()]
        else:
            logger.exception(f"Please put {filename} file under data folder.")
            raise Exception("No names file detected!")

    def write_list_to_file(self, filename: str, new_list: List[str]):
        new_list = [elem + "\n" for elem in new_list]
        with open(f"data\\{filename}.txt", "w") as fh:
            fh.writelines(new_list)

    def get_number(self):
        logger.info(f"Getting number from country: {self.country}")
        if isinstance(self.sms_operator, SmsActivate):
            try:
                self._number = self.sms_operator.get_number(country=self.country)
                self._phone_number = "+" + str(self._number["phone"])
                self._activation_id = self._number["activation_id"]
                self.sms_operator.set_status(self._activation_id, 1)
            except NoNumbersException as e:
                logger.info(f"No numbers found: {str(e)}.")
                raise e
        elif isinstance(self.sms_operator, Sim5Net):
            try:
                self._number = self.sms_operator.purchase_number(country=self.country)
                self._phone_number = str(self._number.phone)
                self._activation_id = self._number.id
            except PurchaseNotPossibleException as e:
                logger.info(f"No numbers found: {str(e)}.")
                raise e
            except NoFreePhoneException as e:
                logger.info(f"No numbers found: {str(e)}.")
                raise e

        logger.info(f"Phone number:  {self._phone_number} | activation id: {self._activation_id}")

    def wait_sms_code(self):
        max_retry_count = int(self.sms_timeout / 5)
        logger.info(f"Maximum time out time is set to {str(self.sms_timeout)}.")
        # TODO: If not received throw error
        status = None
        while max_retry_count > 0:
            if isinstance(self.sms_operator, SmsActivate):
                try:
                    status = self.sms_operator.get_status(self._number["activation_id"])  # type: ignore
                    break
                except Exception:
                    logger.info("Waiting for code ...")

            elif isinstance(self.sms_operator, Sim5Net):
                try:
                    status = self.sms_operator.get_status_code(self._number.id)
                    break
                except Exception:
                    logger.info("Waiting for code ...")

            time.sleep(5)
            max_retry_count -= 1

        if not status:
            raise CannotRetrieveSMSCode("Cannot retrieve sms code.")

        logger.info(f"Code retrieved: {status}")
        return status

    def divide_names(self, name: str):
        name = name.replace("\n", "")
        return name[:-1], name[-1]

    def remove_current_picture(self, path_of_file: str):
        try:
            os.remove(path_of_file)
        except Exception:
            logger.exception(f"Cannot remove profile picture under path: {path_of_file}")

    def write_output_files(self):
        if self._number:
            with open(self.output_dir + r"\phones.txt", "a") as fh:
                fh.write(str(self._phone_number + "\n"))

    def read_txt_proxy(self, proxy: str):
        splitted_line = proxy.split(":")
        proxy_dict = {}
        proxy_dict["addr"] = splitted_line[0]
        proxy_dict["port"] = int(splitted_line[1])
        proxy_dict["username"] = splitted_line[2]
        proxy_dict["password"] = splitted_line[3]
        proxy_dict["proxy_type"] = "socks5"

        return proxy_dict

    def generate_username(self, name: str):
        removed_digits = "".join([elem for elem in name if not elem.isdigit()])
        return removed_digits[::-1] + removed_digits[::-1]

    def delete_unsuccessful_session(self):
        if os.path.isfile(f"sessions\\{self._phone_number}.session"):
            os.remove(f"sessions\\{self._phone_number}.session")

    def run(self):
        self.names_copy = self.names.copy()
        self.running = True
        for name in self.names:
            with self.pause_cond:
                while self.paused:
                    self.pause_cond.wait()

                if self.stopped:
                    self.running = False
                    break
                try:
                    logger.info(f"Starting registration with name {name}")

                    first_name, last_name = self.divide_names(name)

                    logger.info(f"Name: {first_name} \n Last Name: {last_name}")
                    username = self.generate_username(name=name)
                    logger.info(f"Username: {username}")

                    current_image = None
                    if self._list_of_profile_pics_path and self.profile_pics_path:
                        logger.info(f"Profile image will used: {self._list_of_profile_pics_path[0]}")
                        current_image = self.profile_pics_path + "\\" + self._list_of_profile_pics_path[0]

                    current_password = None
                    if self.passwords:
                        current_password = self.passwords[0]
                        logger.info(f"2FA password will set: {current_password}")

                    current_about = None
                    if self.abouts:
                        current_about = self.abouts[0]
                        logger.info(f"About info will set: {current_about}")

                    formatted_proxy = None
                    current_proxy = None
                    if self.proxies:
                        current_proxy = self.proxies[0]
                        formatted_proxy = self.read_txt_proxy(current_proxy)  # type: ignore
                        logger.info(f"Proxy will be used: {formatted_proxy['addr']}")

                    device = None
                    if self.devices:
                        device = self.devices[0]
                        logger.info(f"Device name will be used: {device}")

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    retry_count = 0
                    tw_instance = None
                    success = False
                    while retry_count < 5:
                        try:
                            self.get_number()
                            telegram_client = TelegramClient(
                                rf"sessions\{self._phone_number}",
                                api_id=self.tg_api_id,
                                api_hash=self.tg_api_hash,
                                device_model=device if device else platform.uname().machine,
                                system_version="" if device else platform.uname().release,
                                proxy=formatted_proxy if formatted_proxy else {},
                            )

                            tw_instance = TelethonWrapper(
                                client=telegram_client,
                                phone=self._phone_number,
                                code_callback=self.wait_sms_code,
                                first_name=first_name,
                                last_name=last_name,
                                username=username,
                                profile_image_path=current_image,
                                password=current_password,
                                about=current_about,
                            )
                            tw_instance.client.loop.run_until_complete(tw_instance.register_account())
                            tw_instance.client.loop.run_until_complete(tw_instance.set_other_user_settings())
                            tw_instance.client.disconnect()
                            if isinstance(self.sms_operator, SmsActivate):
                                self.sms_operator.set_status(self._activation_id, 6)
                            elif isinstance(self.sms_operator, Sim5Net):
                                pass
                            success = True
                        except NumberBannedException:
                            logger.info(f"{self._phone_number} is banned. New number will be tried.")
                            if isinstance(self.sms_operator, SmsActivate):
                                self.sms_operator.set_status(self._activation_id, 8)
                            elif isinstance(self.sms_operator, Sim5Net):
                                pass
                            self.delete_unsuccessful_session()
                        except CannotRetrieveSMSCode:
                            logger.info("Cannot retrieve sms code for current number.")
                            self.delete_unsuccessful_session()
                            if isinstance(self.sms_operator, SmsActivate):
                                self.sms_operator.set_status(self._activation_id, 8)
                            elif isinstance(self.sms_operator, Sim5Net):
                                pass
                        except Exception as e:
                            logger.info(f"Unknown exception {str(e)}.")
                            self.delete_unsuccessful_session()
                            if isinstance(self.sms_operator, SmsActivate):
                                self.sms_operator.set_status(self._activation_id, 8)
                            elif isinstance(self.sms_operator, Sim5Net):
                                pass
                            raise Exception(e)
                            break
                        finally:
                            if tw_instance and tw_instance.client:
                                tw_instance.client.disconnect()

                        retry_count += 1
                        if success:
                            break

                    if not success:
                        raise RegisterTelegramException("Cannot register account due to unknown reasons.")

                    # Clean up
                    self.names_copy.remove(name)
                    self.write_list_to_file("names", self.names_copy)

                    # Remove image
                    if current_image and self._list_of_profile_pics_path:
                        self.remove_current_picture(current_image)
                        del self._list_of_profile_pics_path[0]

                    # Remove password
                    if current_password and self.passwords:
                        self.passwords.remove(current_password)
                        self.write_list_to_file("passwords", self.passwords)

                    # Remove about
                    if current_about and self.abouts:
                        self.abouts.remove(current_about)
                        self.write_list_to_file("about", self.abouts)

                    # Remove proxy
                    if current_proxy and self.proxies:
                        self.proxies.remove(current_proxy)
                        self.write_list_to_file("proxies", self.proxies)

                    # Remove device
                    if device and self.devices:
                        self.devices.remove(device)
                        self.write_list_to_file("devices", self.devices)

                    self.write_output_files()
                    logger.info(f"Registration complete for {name}.")

                except (NoNumbersException, PurchaseNotPossibleException, NoFreePhoneException):
                    tkmb.showerror("Error Occured", "No numbers found")
                    break
                except Exception as e:
                    logger.info(f"Exception occured with {str(e)}")
