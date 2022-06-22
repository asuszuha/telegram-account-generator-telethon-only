import base64
import os
import pathlib
import tkinter.messagebox as tkmb
from atexit import register
from base64 import b64encode as b
from random import randrange
from typing import Dict, Optional, Union
from weakref import proxy

import cloudscraper
import pymailtm
from anticaptchaofficial.hcaptchaproxyless import *
from anticaptchaofficial.hcaptchaproxyon import *
from retry import retry
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver as ChromeWebDriver

# from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.support.wait import WebDriverWait

from src.automation.abstract_automation import AbstractAutomation
from src.automation.exceptions_automation import CannotRetrieveSMSCode
from src.utils.gmailnator import Gmailnator
from src.utils.kopeechka import Kopeechka
from src.utils.logger import logger
from src.utils.paths import GENERATE_DISCORD_ACCOUNT_DIR
from src.utils.sim5_net import NoFreePhoneException, PurchaseNotPossibleException, Sim5Net
from src.utils.sms_activate import NoNumbersException, SmsActivate


class DiscordAccGeneratorException(Exception):
    pass


class CannotRetrieveCaptchaToken(DiscordAccGeneratorException):
    pass


class BadProxyCannotProceed(DiscordAccGeneratorException):
    pass


class CannotGetRegistrationPage(DiscordAccGeneratorException):
    pass


class DiscordAccGenerator(AbstractAutomation):
    def __init__(
        self,
        kopeechka_api_key: str,
        email_verification_enabled: bool,
        sms_verification_enabled: bool,
        anticaptcha_api_key: str,
        proxy_enabled: int,
        sms_operator: Optional[Union[Sim5Net, SmsActivate]] = None,
        sms_timeout: Optional[str] = None,
        country: Optional[str] = None,
        sms_after_code_op: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.kopeechka_api_key = kopeechka_api_key
        self.sms_verification_enabled = sms_verification_enabled
        self.email_verification_enabled = email_verification_enabled
        if self.sms_verification_enabled:
            self.sms_operator = sms_operator
            self.country = country
            self.sms_after_code_op = 6 if sms_after_code_op == "cancel" else None
            self.sms_timeout = int(sms_timeout)
        self.proxy_enabled = proxy_enabled
        if proxy_enabled:
            self.proxies = self.read_file_with_property(path=GENERATE_DISCORD_ACCOUNT_DIR, filename="proxies")
        else:
            self.proxies = []

        self.users = self.read_file_with_property(path=GENERATE_DISCORD_ACCOUNT_DIR, filename="user")
        self.passwords = self.read_file_with_property(path=GENERATE_DISCORD_ACCOUNT_DIR, filename="passwords")

        self.profile_pics_path = GENERATE_DISCORD_ACCOUNT_DIR + "\\" + "profile_pics"
        self._list_of_profile_pics_path = os.listdir(self.profile_pics_path)
        self._default_chrome_dir = f"{os.getcwd()}\\chrome_settings"
        self.api_key_captcha = anticaptcha_api_key
        self.site_key_register = "4c672d35-0701-42b2-88c3-78380b0db560"
        self.register_url = "https://discord.com/register"
        self.verify_url = "https://discord.com/verify"
        self.site_key_verify = "f5561ba9-8f1e-40ca-9b5b-a0b3f719ef34"
        self.verify_sms_url = "https://discord.com/channels/@me"
        self.site_key_sms_verify = "f5561ba9-8f1e-40ca-9b5b-a0b3f719ef34"

        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.67 Safari/537.36"

    def get_number(self):
        logger.info(f"Getting number from country: {self.country}")
        if isinstance(self.sms_operator, SmsActivate):
            try:
                number = self.sms_operator.get_number(country=self.country)
                phone_number = "+" + str(number["phone"])
                activation_id = number["activation_id"]
                self.sms_operator.set_status(activation_id, 1)
            except NoNumbersException as e:
                logger.info(f"No numbers found: {str(e)}.")
                raise e
        elif isinstance(self.sms_operator, Sim5Net):
            try:
                number = self.sms_operator.purchase_number(country=self.country)
                phone_number = str(number.phone)
                activation_id = number.id
            except PurchaseNotPossibleException as e:
                logger.info(f"No numbers found: {str(e)}.")
                raise e
            except NoFreePhoneException as e:
                logger.info(f"No numbers found: {str(e)}.")
                raise e

        logger.info(f"Phone number:  {phone_number} | activation id: {activation_id}")
        return number, phone_number

    def wait_sms_code(self, number):
        max_retry_count = int(self.sms_timeout / 5)
        logger.info(f"Maximum time out time is set to {str(self.sms_timeout)}.")
        # TODO: If not received throw error
        status = None
        while max_retry_count > 0:

            if isinstance(self.sms_operator, SmsActivate):
                try:
                    status = self.sms_operator.get_status(number["activation_id"])  # type: ignore
                    break
                except Exception:
                    logger.info("Waiting for code ...")

            elif isinstance(self.sms_operator, Sim5Net):
                try:
                    status = self.sms_operator.get_status_code(number.id)
                    break
                except Exception:
                    logger.info("Waiting for code ...")

            time.sleep(5)
            while self.paused:
                self.pause_cond.wait()

            if self.stopped:
                break
            max_retry_count -= 1

        if not status:
            raise CannotRetrieveSMSCode("Cannot retrieve sms code.")

        logger.info(f"Code retrieved: {status}")
        return status

    @retry(Exception, 3, 5)
    def retrieve_hcaptcha(self, site_key: str, url: str, proxy: Optional[Dict[str, str]] = None, cookies=None):
        if proxy:
            solver = hCaptchaProxyon()
            solver.set_verbose(1)
            solver.set_key(self.api_key_captcha)
            solver.set_website_url(url)
            solver.set_website_key(site_key)
            solver.set_proxy_address(proxy["addr"])
            solver.set_proxy_port(proxy["port"])
            solver.set_proxy_login(proxy["username"])
            solver.set_proxy_password(proxy["password"])
            solver.set_user_agent(self.user_agent)
            solver.set_proxy_type("http")
            if cookies:
                solver.set_cookies(cookies)
            g_response = solver.solve_and_return_solution()

            if g_response != 0:
                logger.info("Token successfuly received.")
                return g_response
            else:
                logger.exception(f"Cannot retieve captcha token: {g_response['errorDescription']}")
                raise CannotRetrieveCaptchaToken(f"Cannot retieve captcha token: {g_response['errorDescription']}")

        else:
            solver = hCaptchaProxyless()
            solver.set_verbose(1)
            solver.set_key(self.api_key_captcha)
            solver.set_website_url(url)
            solver.set_website_key(site_key)
            solver.set_user_agent(self.user_agent)
            if cookies:
                solver.set_cookies(cookies)
            g_response = solver.solve_and_return_solution()
            if g_response != 0:
                logger.info("Token successfuly received.")
                return g_response
            else:
                logger.exception(f"Cannot retieve captcha token: {g_response['errorDescription']}")
                raise CannotRetrieveCaptchaToken(f"Cannot retieve captcha token: {g_response['errorDescription']}")

    def register_account(self, session, captcha_key, email, password, username, fingerprint):
        response = session.post(
            "https://discord.com/api/v9/auth/register",
            headers={"referer": "https://discord.com/register", "authorization": "undefined"},
            json={
                "captcha_key": captcha_key,
                "consent": True,
                "date_of_birth": f"{str(randrange(1970, 2000))}-{str(randrange(1, 12)).zfill(2)}-{str(randrange(1, 26)).zfill(2)}",
                "email": email,
                "fingerprint": fingerprint,
                "gift_code_sku_id": None,
                "invite": None,
                "password": password,
                "username": username,
            },
        ).json()
        print(response)
        return response["token"]

    def get_email_token(self, session: cloudscraper.Session, url: str):
        return session.get(url).url.split("#token=")[1]

    def verify_email(self, session: cloudscraper.Session, url: str, captcha_key: str, token: str):
        email_token = self.get_email_token(session, url)
        response = session.post(
            "https://discord.com/api/v9/auth/verify",
            headers={
                "sec-ch-ua": '" Not;A Brand";v="99", "Firefox";v="91", "Chromium";v="91"',
                "referer": "https://discord.com/verify",
                "authorization": token,
            },
            json={"captcha_key": captcha_key, "token": email_token},
        ).json()

        return response["token"]

    def verify_phone(self, session: cloudscraper.Session, captcha_key: str, token: str, password: str):
        number_info, phone_number = self.get_number()
        self.request_sms(session=session, captcha_key=captcha_key, number=phone_number, token=token)
        code_returned = self.wait_sms_code(number_info)
        token = self.submit_sms(
            session=session, token=token, code=code_returned, number=phone_number.replace("+", ""), password=password
        )
        return token

    def get_proxy_formatted(self, proxy: Dict):
        return f"{proxy['username']}:{proxy['password']}@{proxy['addr']}:{proxy['port']}"

    def create_session(self, proxy: Optional[Dict]):
        useragent = self.user_agent
        current_session = cloudscraper.Session()
        if proxy:
            proxy_formatted = self.get_proxy_formatted(proxy)
            current_session.proxies.update(
                {"http": f"http://" + proxy_formatted, "https": f"http://" + proxy_formatted}
            )
            try:
                current_session.get("https://ipv4.icanhazip.com/").text
            except:
                raise BadProxyCannotProceed("Bad proxy cannot proceed.")

        try:
            response = current_session.get("https://discord.com/register")
        except:
            raise CannotGetRegistrationPage("Cannot retrieve registration page")

        dcfduid = response.headers["Set-Cookie"].split("__dcfduid=")[1].split(";")[0]
        current_session.cookies["__dcfduid"] = dcfduid
        sdcfduid = response.headers["Set-Cookie"].split("__sdcfduid=")[1].split(";")[0]
        current_session.cookies["__sdcfduid"] = sdcfduid
        current_session.cookies["locale"] = "en"

        super_properties = b(
            json.dumps(
                {
                    "os": "Windows",
                    "browser": "Chrome",
                    "device": "",
                    "system_locale": "en-US",
                    "browser_user_agent": useragent,
                    "browser_version": "101.0.4951.67",
                    "os_version": "10",
                    "referrer": "",
                    "referring_domain": "",
                    "referrer_current": "",
                    "referring_domain_current": "",
                    "release_channel": "stable",
                    "client_build_number": 129705,
                    "client_event_source": None,
                },
                separators=(",", ":"),
            ).encode()
        ).decode()

        current_session.headers.update(
            {
                "Accept": "*/*",
                "Accept-Language": "en",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Pragma": "no-cache",
                "Content-Type": "application/json",
                "Origin": "https://discord.com",
                "Referer": "https://discord.com",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "sec-ch-ua-platform": "Windows",
                "sec-ch-ua-mobile": "?0",
                "" "User-Agent": useragent,
                "X-Super-Properties": super_properties,
                "Cookie": "__dcfduid=" + dcfduid + "; __sdcfduid=" + dcfduid,
                "TE": "Trailers",
            }
        )

        return current_session

    def get_fingerprint(self, session: cloudscraper.Session):
        response = session.get("https://discord.com/api/v9/experiments").json()
        fingerprint = response["fingerprint"]
        session.headers.update({"x-fingerprint": fingerprint})
        return fingerprint

    def request_sms(self, session: cloudscraper.Session, captcha_key: str, number: str, token: str):
        payload = {"captcha_key": captcha_key, "change_phone_reason": "user_action_required", "phone": number}
        response = session.post(
            "https://discord.com/api/v9/users/@me/phone",
            headers={
                "sec-ch-ua": '" Not A;Brand";v="99", "Chromium";v="101", "Google Chrome";v="101"',
                "referer": "https://discord.com/channels/@me",
                "authorization": token,
            },
            json=payload,
        )
        if response.status_code == 204:
            return True

        print(response)
        return False

    def submit_sms(self, session: cloudscraper.Session, token: str, code: str, number: str, password: str):
        phone_token = session.post(
            "https://discord.com/api/v9/phone-verifications/verify",
            headers={"referer": "https://discord.com/channels/@me", "authorization": token},
            json={"code": code, "phone": "+" + number},
        ).json()
        phone_token = phone_token["token"]
        response = session.post(
            "https://discord.com/api/v9/users/@me/phone",
            headers={"referer": "https://discord.com/channels/@me", "authorization": token},
            json={"change_phone_reason": "user_action_required", "password": password, "phone_token": phone_token},
        )
        if response.status_code != 204:
            Exception("Something went wrong with SMS verification")
        else:
            return token

    def patch_user_info(self, session: cloudscraper.Session, token: str, username: str, image_data):
        response = session.patch(
            "https://discord.com/api/v9/users/@me",
            headers={"referer": "https://discord.com/channels/@me", "authorization": token},
            json={"username": username, "avatar": image_data},
        )
        if response.status_code != 204:
            Exception("Something went wrong with SMS verification")
        else:
            return token

    @retry(Exception, 3, 5)
    def get_mail_account(self):
        return pymailtm.MailTm().get_account()

    def run(self):
        self.users_copy = self.users.copy()
        self.running = True
        kopeechka_client = Kopeechka(self.kopeechka_api_key)
        if not self.users:
            tkmb.showerror("No Users Given", "There are no users given to process. Please fill user.txt file.")
            return

        if not self.passwords:
            tkmb.showerror(
                "No Passwords Given", "There are no passwords given to process. Please fill passwords.txt file."
            )
            return

        if not self.proxy_enabled:
            if self.proxies:
                tkmb.showerror(
                    "No Proxies Given", "There are no proxies given to process. Please fill proxies.txt file."
                )
                return

        for user in self.users:
            with self.pause_cond:
                while self.paused:
                    self.pause_cond.wait()

                if self.stopped:
                    self.running = False
                    break

                try:
                    current_proxy = None
                    formatted_proxy = None
                    if self.proxies:
                        current_proxy = self.proxies[0]
                        formatted_proxy = self.read_txt_proxy(current_proxy)
                        logger.info(f"Proxy to be used: {current_proxy}")
                    current_password = self.passwords[0]
                    response = kopeechka_client.generate_email()
                    email = response["mail"]
                    id = response["id"]
                    logger.info(f"Registration started with {email} | {current_password}")
                    captcha_key = self.retrieve_hcaptcha(site_key=self.site_key_register, url=self.register_url)
                    session = self.create_session(proxy=formatted_proxy)
                    fingerprint = self.get_fingerprint(session=session)

                    current_image = None
                    if self._list_of_profile_pics_path and self.profile_pics_path:
                        logger.info(f"Profile image will used: {self._list_of_profile_pics_path[0]}")
                        current_image = self.profile_pics_path + "\\" + self._list_of_profile_pics_path[0]
                        with open(current_image, "rb") as imageFile:
                            imagestr = base64.b64encode(imageFile.read())
                        img_suffix = pathlib.Path(current_image).suffix.lower()
                        suffix_map = {".jpg": "image/jpeg", ".png": "image/png", ".gif": "image/gif"}
                        if img_suffix in suffix_map.keys():
                            current_image = f"data:{suffix_map[img_suffix]};base64,{imagestr}"
                        else:
                            raise Exception("Not recognized image format.")

                    token = self.register_account(
                        session=session,
                        captcha_key=captcha_key,
                        email=email,
                        password=current_password,
                        username=user,
                        fingerprint=fingerprint,
                    )
                    time.sleep(5)
                    # Remove proxy
                    if current_proxy and self.proxies:
                        self.proxies.remove(current_proxy)
                        self.write_list_to_file(
                            path=GENERATE_DISCORD_ACCOUNT_DIR, filename="proxies", new_list=self.proxies
                        )

                    # Remove password
                    self.passwords.remove(current_password)
                    self.write_list_to_file(
                        path=GENERATE_DISCORD_ACCOUNT_DIR, filename="passwords", new_list=self.passwords
                    )

                    # Clean up
                    self.users_copy.remove(user)
                    self.write_list_to_file(
                        path=GENERATE_DISCORD_ACCOUNT_DIR, filename="user", new_list=self.users_copy
                    )

                    with open(GENERATE_DISCORD_ACCOUNT_DIR + r"\account_info.txt", "a") as fh:
                        if self.proxy_enabled:
                            fh.write(
                                f"{email}:{current_password}:{token}:{self.get_proxy_formatted(formatted_proxy)}\n"
                            )
                        else:
                            fh.write(f"{email}:{current_password}:{token}\n")

                    logger.info("Registration completed.")

                    if self.sms_verification_enabled:
                        counter = 0
                        while counter < 3:
                            try:
                                captcha_key_verify_sms = self.retrieve_hcaptcha(
                                    site_key=self.site_key_verify,
                                    url=self.verify_url,
                                    proxy=formatted_proxy,
                                    cookies=session.cookies.get_dict(),
                                )
                                token = self.verify_phone(
                                    session=session,
                                    captcha_key=captcha_key_verify_sms,
                                    token=token,
                                    password=current_password,
                                )
                                logger.info("SMS verification completed.")
                                break
                            except:
                                counter += 1

                    if self.email_verification_enabled:
                        url = kopeechka_client.wait_for_email(id=id)
                        # url = current_account.get_messages()[0].text.split("Verify Email:")[1].strip()
                        captcha_key_verify = self.retrieve_hcaptcha(site_key=self.site_key_verify, url=self.verify_url)
                        email_token = self.verify_email(
                            session=session, url=url, captcha_key=captcha_key_verify, token=token
                        )

                        logger.info("Email verification completed.")

                    # change avatar:
                    if current_image:
                        self.patch_user_info(session=session, token=token, username=user, image_data=current_image)

                except Exception as e:
                    logger.info(f"Exception occured with {str(e)}")
