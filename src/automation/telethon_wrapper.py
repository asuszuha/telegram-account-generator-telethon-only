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


class TelethonWrapper:
    def __init__(
        self,
        client: TelegramClient,
        phone: str,
        code_callback,
        first_name: str,
        last_name: str,
        username: str,
        profile_image_path: str = None,
        password: str = None,
        about: str = None,
    ):
        self.client_internal = client
        self.phone = phone
        self.code_callback = code_callback
        self.first_name = first_name
        self.last_name = last_name
        self.password = password
        self.username = username
        self.profile_image_path = profile_image_path
        self.about = about

    async def register_account(self):
        logger.info("Starting to register in account with telethon.")
        try:
            self.client_internal = await self.client_internal.start(
                first_name=self.first_name,
                last_name=self.last_name,
                phone=self.phone,
                max_attempts=10,
                code_callback=self.code_callback,
                password=self.password_callback,
            )
        except PhoneNumberBannedError as pbe:
            logger.info(str(pbe))
            raise NumberBannedException(str(pbe))
        except CannotRetrieveSMSCode as crs:
            raise CannotRetrieveSMSCode(str(crs))
        except Exception as e:
            logger.info(f"Unknown error occured: {str(e)}")
            raise Exception(e)

    async def set_other_user_settings(self):
        if self.profile_image_path:
            logger.info("Profile image will be added.")
            await self.client_internal(
                UploadProfilePhotoRequest(await self.client_internal.upload_file(self.profile_image_path))
            )
            logger.info("Profile image successfully added.")

        try:
            logger.info(f"Trying to update username to {self.username}.")
            await self.client_internal(UpdateUsernameRequest(self.username))
            logger.info(f"Username updated to {self.username}")
        except Exception as e:
            logger.error(f"Cannot change username: {str(e)}")

        try:
            if self.password:
                self.client.edit_2fa(new_password=self.password)
                logger.info(f"2fa password is set to {self.password}")
        except Exception as e:
            logger.error(f"Cannot change set 2fa password: {str(e)}")

        try:
            if self.about:
                await self.client(UpdateProfileRequest(about=self.about))
                logger.info(f"About set to {self.about}")
        except Exception as e:
            logger.error(f"Cannot set about: {str(e)}")

    @property
    def client(self) -> TelegramClient:
        return self.client_internal

    def password_callback(self):
        return self.password if self.password else ""
