import asyncio
import os
import time
import tkinter.messagebox as tkmb
from typing import List, Optional, Union

from appium import webdriver
from appium.webdriver.appium_service import AppiumService
from appium.webdriver.common.appiumby import AppiumBy
from retry import retry
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait  # type: ignore
from telethon import TelegramClient

from src.automation.abstract_automation import AbstractAutomation
from src.utils.adb_helper import ADBHelper
from src.utils.logger import logger
from src.utils.sim5_net import NoFreePhoneException, PurchaseNotPossibleException, Sim5Net
from src.utils.sms_activate import NoNumbersException, SmsActivate

from .socks_droid import SocksDroid
from .telethon_wrapper import TelethonWrapper


class RegisterTelegramException(Exception):
    pass


class CannotRetrieveSMSCode(RegisterTelegramException):
    pass


class RegisterTelegram(AbstractAutomation):
    def __init__(
        self,
        device_name: str,
        sms_operator: Union[Sim5Net, SmsActivate],
        country: str,
        names: List[str],
        filename: str,
        profile_pics_paths: Optional[str],
        output_dir: str,
        tg_api_id: str,
        tg_api_hash: str,
        proxy_list: Optional[List[str]],
        proxy_filename: Optional[str],
        password_list: Optional[List[str]],
        password_filename: Optional[str],
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._port = 4723
        self._appium_service = AppiumService()
        self._appium_service.start(args=[f"-p {str(self._port)}"])
        self.device_name = device_name
        self._package_name = "org.telegram.messenger"
        self._caps = {}
        self._caps["platformName"] = "Android"
        self._caps["appium:ensureWebviewsHavePages"] = True
        self._caps["appium:nativeWebScreenshot"] = True
        self._caps["appium:newCommandTimeout"] = 10000
        self._caps["appium:autoGrantPermissions	"] = True
        self._caps["appium:connectHardwareKeyboard"] = True
        self._caps["appium:appPackage"] = self._package_name
        self._caps["appium:appActivity"] = "org.telegram.ui.LaunchActivity"
        self._emulator = False
        if self.is_emulator(device_name):
            self._emulator = True
            emulator_name = ADBHelper().get_emulator_name(device_name)
            self._caps["appium:avd"] = emulator_name
        else:
            self._caps["appium:udid"] = device_name

        self.sms_operator = sms_operator
        self.country = country
        self.names = names
        self.filename = filename
        self.profile_pics_path = profile_pics_paths
        if profile_pics_paths:
            self._list_of_profile_pics_path = os.listdir(profile_pics_paths)
        else:
            self._list_of_profile_pics_path = None
        self.first_run = True
        self._driver = None
        self.output_dir = output_dir
        self.tg_api_id = tg_api_id
        self.tg_api_hash = tg_api_hash
        self.proxy_list = proxy_list
        self.proxy_filename = proxy_filename
        self.password_list = password_list
        self.password_filename = password_filename

    def is_emulator(self, device_name: str):
        return "emulator" in device_name.lower()

    def install_socksdroid(self, driver):
        if not driver.is_app_installed("net.typeblog.socks"):
            driver.install_app(r"apks\net_typeblog_socks.apk")

    @retry(Exception, 3, 5)
    def start_messaging_screen(self, driver):
        if self._emulator:
            wait_time = 100
        else:
            wait_time = 30

        start_messaging_elem = WebDriverWait(driver, wait_time).until(
            expected_conditions.presence_of_element_located(
                (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("Start Messaging")')
            )
        )

        start_messaging_elem.click()
        time.sleep(4)

    def allow_phone_calls(self, driver):
        try:
            pop_up_allow_calls = driver.find_element_by_android_uiautomator('new UiSelector().textContains("CONTINUE")')
            pop_up_allow_calls.click()
            time.sleep(5)
            allow_calls = driver.find_element(AppiumBy.XPATH, "//android.widget.Button[@text='Allow']")
            allow_calls.click()
        except Exception:
            pass

        time.sleep(4)

    def fill_country_code_and_phone_number(self, driver):
        country = driver.find_element(by=AppiumBy.ACCESSIBILITY_ID, value="Country code")
        country.clear()
        phone_number = driver.find_element(by=AppiumBy.ACCESSIBILITY_ID, value="Phone number")
        phone_number.clear()
        if isinstance(self.sms_operator, SmsActivate):
            try:
                self._number = self.sms_operator.get_number(country=self.country)
                self._phone_number = "+" + str(self._number["phone"])
            except NoNumbersException as e:
                logger.info(f"No numbers found: {str(e)}.")
                raise e
            country.send_keys(self._number["phone"])
        elif isinstance(self.sms_operator, Sim5Net):
            try:
                self._number = self.sms_operator.purchase_number(country=self.country)
                self._phone_number = str(self._number.phone)
            except PurchaseNotPossibleException as e:
                logger.info(f"No numbers found: {str(e)}.")
                raise e
            except NoFreePhoneException as e:
                logger.info(f"No numbers found: {str(e)}.")
                raise e

            country.send_keys(self._number.phone)
        complete_phone_no = driver.find_element(by=AppiumBy.ACCESSIBILITY_ID, value="Done")
        complete_phone_no.click()
        time.sleep(3)
        try:
            pop_up = driver.find_element_by_android_uiautomator('new UiSelector().textContains("Yes")')
            pop_up.click()
        except Exception:
            logger.info("No popup appeared for approving number.")

        time.sleep(5)

    def allow_read_call_log(self, driver):
        try:
            pop_up_allow_read_call_log = driver.find_element_by_android_uiautomator(
                'new UiSelector().textContains("CONTINUE")'
            )
            pop_up_allow_read_call_log.click()
            time.sleep(5)
            allow_call_logs = driver.find_element(AppiumBy.XPATH, "//android.widget.Button[@text='Allow']")
            allow_call_logs.click()
        except Exception:
            pass

        time.sleep(4)

    def get_verification_code(self):
        verification_message_overview = WebDriverWait(self._driver, 10).until(
            expected_conditions.visibility_of_element_located(
                (
                    AppiumBy.XPATH,
                    (
                        "//android.widget.FrameLayout[2]"
                        "//androidx.recyclerview.widget.RecyclerView//android.view.ViewGroup"
                    ),
                )
            )
        )

        verification_message_overview.click()
        time.sleep(3)
        verification_message_all = WebDriverWait(self._driver, 10).until(
            expected_conditions.visibility_of_element_located(
                (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("Login code")')
            )
        )
        code = verification_message_all.text.split(":")[1].split(".")[0].strip()
        return code

    def fill_sms_code(self, driver):
        wait_for_code_screen = WebDriverWait(driver, 40).until(  # noqa
            expected_conditions.presence_of_element_located(
                (
                    By.XPATH,
                    (
                        "//android.widget.FrameLayout//android.widget.LinearLayout"
                        "//android.widget.TextView[@text='Enter code']"
                    ),
                )
            )
        )

        sms_code_elem = WebDriverWait(driver, 30).until(
            expected_conditions.presence_of_element_located((By.XPATH, "//android.widget.EditText[@index=0]"))
        )

        retry_count = 0
        # TODO: If not received throw error
        while retry_count < 10:
            if isinstance(self.sms_operator, SmsActivate):
                try:
                    status = self.sms_operator.get_status(self._number["activation_id"])  # type: ignore
                    sms_code_elem = WebDriverWait(driver, 30).until(
                        expected_conditions.presence_of_element_located(
                            (By.XPATH, "//android.widget.EditText[@index=0]")
                        )
                    )
                    sms_code_elem.click()
                    sms_code_elem.send_keys(status)
                    break
                except Exception:
                    logger.info(f"Cannot get status code. Retry number {retry_count + 1}.")

            elif isinstance(self.sms_operator, Sim5Net):
                try:
                    status = self.sms_operator.get_status_code(self._number.id)
                    sms_code_elem = WebDriverWait(driver, 30).until(
                        expected_conditions.presence_of_element_located(
                            (By.XPATH, "//android.widget.EditText[@index=0]")
                        )
                    )
                    sms_code_elem.click()
                    sms_code_elem.send_keys(status)
                    break
                except Exception:
                    logger.info(f"Cannot get status code. Retry number {retry_count + 1}.")

            time.sleep(5)
            retry_count += 1

    def divide_names(self, name: str):
        name = name.replace("\n", "")
        return name[:-1], name[-1]

    @retry(Exception, 3, 5)
    def fill_name_last_name(self, driver, name_to_fill: str, last_name_to_fill: str):
        # this is a placeholder for waiting page to load
        profile_info = WebDriverWait(driver, 20).until(  # noqa # type: ignore
            expected_conditions.visibility_of_element_located(
                (
                    AppiumBy.XPATH,
                    "//android.widget.FrameLayout//android.widget.LinearLayout//android.widget.TextView[@text='Profile info']",
                )
            )
        )
        first_name = WebDriverWait(driver, 10).until(
            expected_conditions.visibility_of_element_located(
                (AppiumBy.XPATH, "//android.widget.FrameLayout[@index=0]//android.widget.EditText")
            )
        )
        first_name.click()
        first_name.send_keys(name_to_fill)

        last_name = WebDriverWait(driver, 10).until(
            expected_conditions.visibility_of_element_located(
                (
                    AppiumBy.XPATH,
                    (
                        "//android.widget.FrameLayout[@index=3]"
                        "//android.widget.FrameLayout[@index=1]//android.widget.EditText"
                    ),
                )
            )
        )
        last_name.click()
        last_name.send_keys(last_name_to_fill)

        complete_name_part = WebDriverWait(driver, 10).until(
            expected_conditions.visibility_of_element_located((AppiumBy.ACCESSIBILITY_ID, "Done"))
        )
        complete_name_part.click()

        time.sleep(4)

    def additional_pop_up_after_filling_name(self, driver):
        try:
            pop_up_access_contacts = WebDriverWait(driver, 10).until(
                expected_conditions.visibility_of_element_located(
                    (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("CONTINUE")')
                )
            )

            # pop_up_access_contacts = driver.find_element_by_android_uiautomator(
            #     'new UiSelector().textContains("CONTINUE")'
            # )
            pop_up_access_contacts.click()
            time.sleep(4)
            allow_contacts = driver.find_element(AppiumBy.XPATH, "//android.widget.Button[@text='Allow']")
            allow_contacts.click()
        except Exception:
            pass

        time.sleep(4)

    def logout_from_telegram(self, driver):
        nav_menu = driver.find_element(by=AppiumBy.ACCESSIBILITY_ID, value="Open navigation menu")
        nav_menu.click()
        time.sleep(3)
        settings_elem = driver.find_element(
            by=AppiumBy.XPATH,
            value="//android.widget.TextView[@text='Settings']",
        )
        settings_elem.click()
        more_opts = driver.find_element(
            by=AppiumBy.XPATH,
            value="//android.widget.ImageButton[@content-desc='More options']//android.widget.ImageView",
        )
        more_opts.click()
        time.sleep(3)
        logout_elem = driver.find_element(
            by=AppiumBy.XPATH,
            value="//android.widget.TextView[@text='Log out']",
        )
        logout_elem.click()
        time.sleep(4)
        logout_main = driver.find_element(
            by=AppiumBy.XPATH,
            value=(
                "//androidx.recyclerview.widget.RecyclerView"
                "//android.widget.FrameLayout[7]//android.widget.TextView[@text='Log Out']"
            ),
        )
        logout_main.click()

        time.sleep(3)
        logout_popup = driver.find_element(
            by=AppiumBy.XPATH,
            value="//android.widget.TextView[@text='LOG OUT']",
        )
        logout_popup.click()

    def stop_service(self):
        if self._driver:
            self._driver.quit()
        self._appium_service.stop()

    def write_list_to_file(self, filename: str, new_list: List[str]):
        with open(filename, "w") as fh:
            fh.writelines(new_list)

    def remove_current_picture(self, path_of_file: str):
        try:
            os.remove(path_of_file)
        except Exception:
            logger.exception(f"Cannot remove profile picture under path: {path_of_file}")

    def write_output_files(self):
        if self._number:
            with open(self.output_dir + r"\phones.txt", "a") as fh:
                fh.write(str(self._phone_number + "\n"))

    def set_proxy(self, driver: webdriver.webdriver.WebDriver):
        driver.launch_app("")

    def get_latest_proxy(self):
        if self.proxy_list:
            return [proxy for proxy in self.proxy_list if "used" not in proxy.split(":")[-1]][0]

    def set_proxy_used(self, current_proxy):
        if self.proxy_list:
            self.proxy_list[self.proxy_list.index(current_proxy)].replace(r"\n", r":used\n")

    def read_txt_proxy(self, proxy: str):
        splitted_line = proxy.replace("\n", "").split(":")
        proxy_dict = {}
        proxy_dict["ip_address"] = splitted_line[0]
        proxy_dict["port"] = splitted_line[1]
        proxy_dict["username"] = splitted_line[2]
        proxy_dict["password"] = splitted_line[3]

        return proxy_dict

    def run(self):
        self.names_copy = self.names.copy()
        self.running = True
        if not self._driver:
            self._driver = webdriver.Remote(f"http://localhost:{str(self._port)}/wd/hub", self._caps)
        sd_client = None
        for name in self.names:
            with self.pause_cond:
                while self.paused:
                    self.pause_cond.wait()

                if self.stopped:
                    self.running = False
                    break
                try:
                    logger.info(f"Starting registration with name {name}")

                    current_proxy = None
                    if self.proxy_list:
                        self.install_socksdroid(self._driver)
                        sd_client = SocksDroid(self._driver)
                        current_proxy = self.get_latest_proxy()
                        formatted_proxy = self.read_txt_proxy(current_proxy)  # type: ignore
                        sd_client.set_proxy_socks_droid(**formatted_proxy)
                        sd_client.enable_proxy()
                        self._driver.activate_app(self._package_name)
                    # it will initialize if not initialized yet
                    self.start_messaging_screen(self._driver)
                    self.allow_phone_calls(self._driver)
                    self.fill_country_code_and_phone_number(self._driver)
                    self.allow_read_call_log(self._driver)
                    self.fill_sms_code(self._driver)
                    first_name, last_name = self.divide_names(name)

                    self.fill_name_last_name(driver=self._driver, name_to_fill=first_name, last_name_to_fill=last_name)
                    self.additional_pop_up_after_filling_name(self._driver)

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    telegram_client = TelegramClient(
                        rf"sessions\{self._phone_number}", api_id=self.tg_api_id, api_hash=self.tg_api_hash
                    )

                    current_image = None
                    if self._list_of_profile_pics_path and self.profile_pics_path:
                        current_image = self.profile_pics_path + "/" + self._list_of_profile_pics_path[0]

                    current_password = None
                    if self.password_list:
                        current_password = self.password_list[0]

                    tw_instance = TelethonWrapper(
                        client=telegram_client,
                        phone=self._phone_number,
                        code_callback=self.get_verification_code,
                        first_name=first_name,
                        last_name=last_name,
                        username=name[::-1],
                        profile_image_path=current_image,
                        password=current_password,
                    )

                    tw_instance.client.loop.run_until_complete(tw_instance.register_account())
                    tw_instance.client.disconnect()
                    self.names_copy.remove(name)
                    self.write_list_to_file(self.filename, self.names_copy)

                    if self.proxy_list and current_proxy:
                        self.set_proxy_used(current_proxy)
                        self.write_list_to_file(self.proxy_filename, self.proxy_list)  # type: ignore

                    if current_password and self.password_list:
                        self.password_list.remove(current_password)
                        self.write_list_to_file(self.password_filename, self.password_list)  # type: ignore

                    if current_image and self._list_of_profile_pics_path:
                        self.remove_current_picture(current_image)
                        del self._list_of_profile_pics_path[0]
                    self.write_output_files()
                    logger.info(f"Registration complete for {name}.")

                except (NoNumbersException, PurchaseNotPossibleException, NoFreePhoneException):
                    tkmb.showerror("Error Occured", "No numbers found")
                    break
                except Exception as e:
                    logger.info(f"Exception occured with {str(e)}")
                finally:
                    if ADBHelper().clear_app_history(device_name=self.device_name, package_name=self._package_name):
                        logger.info(f"Successfully app data cleaned: {self._package_name}")
                    else:
                        logger.info(f"Cleaning app data not successful: {self._package_name}")
                    if sd_client:
                        if ADBHelper().clear_app_history(
                            device_name=self.device_name, package_name=sd_client._package_name
                        ):
                            logger.info(f"Successfully app data cleaned: {sd_client._package_name}")
                        else:
                            logger.info(f"Cleaning app data not successful: {self._package_name}")
                    if self._driver:
                        self._driver.reset()

        self.stop_service()
