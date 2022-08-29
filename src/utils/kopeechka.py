import time
from typing import Optional

import requests
from retry import retry


class KopeechkaException(Exception):
    pass


class CannotGenerateNewAddress(Exception):
    pass


class Kopeechka:
    def __init__(self, api_key: str, mail_type: Optional[str] = "OUTLOOK"):
        self._api_key = api_key
        self._site = "discord.com"
        self._mail_type = mail_type

    @retry(Exception, 3, 5)
    def generate_email(self):
        construct_url = (
            "https://api.kopeechka.store/mailbox-get-email?"
            "api=2.0&spa=1&site=discord.com&sender=discord&regex=&"
            f"mail_type=&token={self._api_key}"
        )
        response = requests.get(construct_url).json()
        if response["status"] == "OK":
            return response
        else:
            raise CannotGenerateNewAddress(f"Cannot generate new email address due to: {response}")

    def check_email(self, id: str):
        response = requests.get(
            f"https://api.kopeechka.store/mailbox-get-message?full=1&spa=1&id={id}&token={self._api_key}"
        ).json()
        return response["value"]

    def delete_email(self, id: str):
        requests.get(f"https://api.kopeechka.store/mailbox-cancel?id={id}&token={self._api_key}")

    def wait_for_email(self, id: str):
        trial_count = 0
        while trial_count < 20:
            time.sleep(2)
            email: str = self.check_email(id=id)
            if email != "WAIT_LINK":
                self.delete_email(id=id)
                return email.replace("\\", "")
            trial_count += 1
        return False
