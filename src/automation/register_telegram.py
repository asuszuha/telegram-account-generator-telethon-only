import asyncio
import os
import platform
import time
import tkinter.messagebox as tkmb
from typing import Union

from telethon import TelegramClient

from src.automation.abstract_automation import AbstractAutomation
from src.automation.exceptions_automation import (
    CannotRetrieveSMSCode,
    NoTelegramApiInfoFoundException,
    RegisterTelegramException,
)
from src.utils.logger import logger
from src.utils.paths import AUTO_REGISTER_PATH_DIR
from src.utils.sim5_net import NoFreePhoneException, PurchaseNotPossibleException, Sim5Net
from src.utils.sms_activate import NoNumbersException, SmsActivate

from .telethon_wrapper import NumberBannedException, PossibleProxyIssueException, TelethonWrapper


class RegisterTelegram(AbstractAutomation):
    def __init__(
        self,
        sms_operator: Union[Sim5Net, SmsActivate],
        sms_timeout: str,
        country: str,
        sms_after_code_op: str,
        maximum_register: str,
        proxy_enabled: int,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.sms_operator = sms_operator
        self.country = country

        # Init from files
        self.names = self.read_file_with_property(path=AUTO_REGISTER_PATH_DIR, filename="names")
        self.devices = self.read_file_with_property(path=AUTO_REGISTER_PATH_DIR, filename="devices")
        self.proxy_enabled = proxy_enabled
        if proxy_enabled:
            self.proxies = self.read_file_with_property(path=AUTO_REGISTER_PATH_DIR, filename="proxies")
        else:
            self.proxies = []
        self.abouts = self.read_file_with_property(path=AUTO_REGISTER_PATH_DIR, filename="about")
        self.passwords = self.read_file_with_property(path=AUTO_REGISTER_PATH_DIR, filename="passwords")
        self.apis = self.read_file_with_property(path=AUTO_REGISTER_PATH_DIR, filename="api")
        self.output_dir = AUTO_REGISTER_PATH_DIR + "\\" + "sessions"
        self.profile_pics_path = AUTO_REGISTER_PATH_DIR + "\\" + "profile_pics"
        self._list_of_profile_pics_path = os.listdir(self.profile_pics_path)
        self.sms_timeout = int(sms_timeout)
        self.sms_after_code_op = 6 if sms_after_code_op == "cancel" else None
        self.maximum_register = int(maximum_register)
        self.tw_instance = None

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
            while self.paused:
                self.pause_cond.wait()

            if self.stopped:
                try:
                    if self.tw_instance and self.tw_instance.client:
                        self.tw_instance.client.loop.stop()
                    self.running = False
                    self.delete_unsuccessful_session()
                except Exception:
                    ...
                finally:
                    break
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
                if self._phone_number:
                    fh.write(str(self._phone_number + "\n"))

    def generate_username(self, name: str):
        removed_digits = "".join([elem for elem in name if not elem.isdigit()])
        return removed_digits[::-1] + removed_digits[0]

    def delete_unsuccessful_session(self):
        if hasattr(self, "_phone_number"):
            if self.tw_instance and self.tw_instance.client:
                self.tw_instance.client.disconnect()
            if self._phone_number:
                if os.path.isfile(f"{AUTO_REGISTER_PATH_DIR}\\sessions\\{self._phone_number}.session"):
                    os.remove(f"{AUTO_REGISTER_PATH_DIR}\\sessions\\{self._phone_number}.session")

    def run(self):
        self.names_copy = self.names.copy()
        self.running = True
        if not self.names:
            tkmb.showerror("No Names Given", "There are no names given to process. Please fill names.txt file.")

        registration_counter = 0
        for name in self.names:
            with self.pause_cond:
                while self.paused:
                    self.pause_cond.wait()

                if self.stopped:
                    if self.tw_instance and self.tw_instance.client:
                        self.tw_instance.client.loop.stop()
                    self.running = False
                    break
                try:
                    logger.info(
                        f"Starting registration with name {name} | Registration count: {str(registration_counter)}"
                    )

                    first_name, last_name = self.divide_names(name)

                    logger.info(f"Name: {first_name} \n Last Name: {last_name}")
                    username = self.generate_username(name=name)
                    logger.info(f"Username: {username}")

                    current_tg_api_id = None
                    current_tg_hash = None
                    if self.apis:
                        splitted_api_info = self.apis[0].split("-")
                        current_tg_api_id = splitted_api_info[0]
                        current_tg_hash = splitted_api_info[1]
                    else:
                        raise NoTelegramApiInfoFoundException("No telegram api info found.")

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
                    if self.proxy_enabled:
                        if self.proxies:
                            current_proxy = self.proxies[0]
                            formatted_proxy = self.read_txt_proxy(current_proxy)  # type: ignore
                            logger.info(f"Proxy will be used: {formatted_proxy['addr']}")
                        else:
                            raise Exception("No more proxy left in the proxies.txt")

                    device = None
                    if self.devices:
                        device = self.devices[0]
                        logger.info(f"Device name will be used: {device}")

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    retry_count = 0
                    self.tw_instance = None
                    success = False
                    self._phone_number = None
                    while retry_count < 5:
                        try:
                            self.get_number()
                            if not self._phone_number:
                                raise Exception("Unknown exception number not found.")
                            telegram_client = TelegramClient(
                                rf"{AUTO_REGISTER_PATH_DIR}\sessions\{self._phone_number}",
                                api_id=current_tg_api_id,
                                api_hash=current_tg_hash,
                                device_model=device if device else platform.uname().machine,
                                system_version="" if device else platform.uname().release,
                                proxy=formatted_proxy if formatted_proxy else {},
                                base_logger=logger,
                            )

                            self.tw_instance = TelethonWrapper(client=telegram_client, phone=self._phone_number)
                            self.tw_instance.client.loop.run_until_complete(
                                self.tw_instance.register_account(
                                    code_callback=self.wait_sms_code,
                                    first_name=first_name,
                                    last_name=last_name,
                                    password=current_password,
                                )
                            )
                            self.tw_instance.client.loop.run_until_complete(
                                self.tw_instance.set_other_user_settings(
                                    username=username,
                                    password=current_password if current_password else "",
                                    profile_image_path=current_image,
                                    about=current_about[:70]
                                    if current_about and len(current_about) > 70
                                    else current_about
                                    if current_about
                                    else "",  # max char limit
                                )
                            )
                            self.tw_instance.client.disconnect()
                            if isinstance(self.sms_operator, SmsActivate):
                                if self.sms_after_code_op:
                                    self.sms_operator.set_status(self._activation_id, self.sms_after_code_op)
                            elif isinstance(self.sms_operator, Sim5Net):
                                pass
                            success = True
                        except NumberBannedException:
                            logger.info(f"{self._phone_number} is banned. New number will be tried.")
                            if self.tw_instance and self.tw_instance.client:
                                self.tw_instance.client.disconnect()
                            if isinstance(self.sms_operator, SmsActivate):
                                self.sms_operator.set_status(self._activation_id, 8)
                            elif isinstance(self.sms_operator, Sim5Net):
                                pass
                            self.delete_unsuccessful_session()
                        except CannotRetrieveSMSCode:
                            logger.info("Cannot retrieve sms code for current number.")
                            if self.tw_instance and self.tw_instance.client:
                                self.tw_instance.client.disconnect()
                            self.delete_unsuccessful_session()
                            if isinstance(self.sms_operator, SmsActivate):
                                self.sms_operator.set_status(self._activation_id, 8)
                            elif isinstance(self.sms_operator, Sim5Net):
                                pass
                        except (NoNumbersException, PurchaseNotPossibleException, NoFreePhoneException) as e:
                            raise NoNumbersException(str(e))
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
                                if self.proxies:
                                    current_proxy = self.proxies[0]
                                    formatted_proxy = self.read_txt_proxy(current_proxy)
                                else:
                                    raise Exception("No more proxy left in the proxies.txt")
                        except Exception as e:
                            logger.info(f"Unknown exception {str(e)}.")
                            if self.tw_instance and self.tw_instance.client:
                                self.tw_instance.client.disconnect()
                            self.delete_unsuccessful_session()
                            if isinstance(self.sms_operator, SmsActivate):
                                self.sms_operator.set_status(self._activation_id, 8)
                            elif isinstance(self.sms_operator, Sim5Net):
                                pass

                            raise e

                        retry_count += 1
                        if success:
                            break

                        while self.paused:
                            self.pause_cond.wait()

                        if self.stopped:
                            if self.tw_instance and self.tw_instance.client:
                                self.tw_instance.client.loop.stop()
                            self.running = False
                            self.delete_unsuccessful_session()
                            break

                    while self.paused:
                        self.pause_cond.wait()

                    if self.stopped:
                        if self.tw_instance and self.tw_instance.client:
                            self.tw_instance.client.loop.stop()
                        self.running = False
                        try:
                            self.delete_unsuccessful_session()
                        except Exception:
                            ...
                        finally:
                            break

                    if not success:
                        self.delete_unsuccessful_session()
                        raise RegisterTelegramException("Cannot register account due to unknown reasons.")

                    # Clean up
                    self.names_copy.remove(name)
                    self.write_list_to_file(path=AUTO_REGISTER_PATH_DIR, filename="names", new_list=self.names_copy)

                    # Remove image
                    if current_image and self._list_of_profile_pics_path:
                        self.remove_current_picture(current_image)
                        del self._list_of_profile_pics_path[0]

                    # Remove password
                    if current_password and self.passwords:
                        self.passwords.remove(current_password)
                        self.write_list_to_file(
                            path=AUTO_REGISTER_PATH_DIR, filename="passwords", new_list=self.passwords
                        )

                    # Remove about
                    if current_about and self.abouts:
                        self.abouts.remove(current_about)
                        self.write_list_to_file(path=AUTO_REGISTER_PATH_DIR, filename="about", new_list=self.abouts)

                    # Remove proxy
                    if current_proxy and self.proxies:
                        self.proxies.remove(current_proxy)
                        self.write_list_to_file(path=AUTO_REGISTER_PATH_DIR, filename="proxies", new_list=self.proxies)

                    # Remove device
                    if device and self.devices:
                        self.devices.remove(device)
                        self.write_list_to_file(path=AUTO_REGISTER_PATH_DIR, filename="devices", new_list=self.devices)

                    # Remove api info
                    self.apis.remove(self.apis[0])
                    self.write_list_to_file(path=AUTO_REGISTER_PATH_DIR, filename="api", new_list=self.apis)

                    self.write_output_files()
                    registration_counter += 1

                    logger.info(f"Registration complete for {name}.")
                    if self.maximum_register and self.maximum_register <= registration_counter:
                        logger.info(f"Reached maximum number of registrations {str(self.maximum_register)}.")
                        break
                except NoNumbersException:
                    self.delete_unsuccessful_session()
                    tkmb.showerror("Error Occured", "No numbers found.")
                    break
                except NoTelegramApiInfoFoundException:
                    self.delete_unsuccessful_session()
                    tkmb.showerror("Error Occured", "No telegram api info found.")
                    break
                except Exception as e:
                    self.delete_unsuccessful_session()
                    logger.info(f"Exception occured with {str(e)}")
