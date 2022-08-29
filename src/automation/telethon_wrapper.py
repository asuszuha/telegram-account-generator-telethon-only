from telethon import TelegramClient
from telethon.errors import PhoneNumberBannedError
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest

from src.automation.exceptions_automation import CannotRetrieveSMSCode
from src.utils.logger import logger


class TelethonException(Exception):
    pass


class NumberBannedException(Exception):
    pass


class PossibleProxyIssueException(TelethonException):
    pass


class TelethonWrapper:
    def __init__(
        self,
        client: TelegramClient,
        phone: str,
    ):
        self.client_internal = client
        self.phone = phone

    async def register_account(
        self,
        code_callback,
        first_name: str,
        last_name: str,
        password: str = None,
    ):
        logger.info("Starting to register in account with telethon.")
        try:
            self.client_internal = await self.client_internal.start(
                first_name=first_name,
                last_name=last_name,
                phone=self.phone,
                max_attempts=10,
                code_callback=code_callback,
                password=password if password else "",
            )
        except PhoneNumberBannedError as pbe:
            logger.info(str(pbe))
            raise NumberBannedException(str(pbe))
        except CannotRetrieveSMSCode as crs:
            raise CannotRetrieveSMSCode(str(crs))
        except ConnectionError as ce:
            logger.exception("Possibly issue with proxy. If you are using proxy it will be removed.")
            raise PossibleProxyIssueException(str(ce))
        except Exception as e:
            logger.info(f"Unknown error occured: {str(e)}")
            raise Exception(e)

    def check_client_authorized(self, code_callback=None):
        try:
            self.client_internal.connect()
            if not self.client_internal.is_user_authorized():
                self.client_internal.send_code_request(self.phone)
                self.client_internal.sign_in(self.phone, code=code_callback() if code_callback else None)
            if not self.client_internal.is_user_authorized():
                return False
            return True
        except ConnectionError as ce:
            logger.exception("Possibly issue with proxy. If you are using proxy it will be removed.")
            raise PossibleProxyIssueException(str(ce))
        except Exception as e:
            logger.exception(str(e))
            return False

    async def set_other_user_settings(
        self,
        username: str = None,
        password: str = None,
        profile_image_path: str = None,
        about: str = None,
        first_name: str = None,
        last_name: str = None,
    ):
        if profile_image_path:
            logger.info("Profile image will be added.")
            await self.client_internal(
                UploadProfilePhotoRequest(await self.client_internal.upload_file(profile_image_path))
            )
            logger.info("Profile image successfully added.")

        try:
            if username:
                logger.info(f"Trying to update username to {username}.")
                await self.client_internal(UpdateUsernameRequest(username))
                logger.info(f"Username updated to {username}")
        except Exception as e:
            logger.error(f"Cannot change username: {str(e)}")

        try:
            if password:
                self.client.edit_2fa(new_password=password)
                logger.info(f"2fa password is set to {password}")
        except Exception as e:
            logger.error(f"Cannot change set 2fa password: {str(e)}")

        try:
            if about:
                await self.client(UpdateProfileRequest(about=about))
                logger.info(f"About set to {about}")
        except Exception as e:
            logger.error(f"Cannot set about: {str(e)}")

        try:
            if first_name:
                await self.client(UpdateProfileRequest(first_name=first_name))
                logger.info(f"First name set to {first_name}")
        except Exception as e:
            logger.error(f"Cannot set first name: {str(e)}")

        try:
            if last_name:
                await self.client(UpdateProfileRequest(last_name=last_name))
                logger.info(f"Last name set to {last_name}")
        except Exception as e:
            logger.error(f"Cannot set last name: {str(e)}")

    def retrieve_code(self):
        if not self.client_internal.is_connected():
            self.client_internal.connect()
        code = None
        for chat in self.client_internal.iter_dialogs():
            if "telegram" in chat.title.lower():
                for message in self.client_internal.iter_messages(chat.id):
                    if "login code" in message.message.lower():
                        code = message.message.split(":")[1].split(".")[0].strip()
                        return code

    @property
    def client(self) -> TelegramClient:
        return self.client_internal
