import requests
from retry import retry

from .logger import logger


class Gmailnator:
    def __init__(self, api_key: str):
        self._api_key = api_key

    @retry(Exception, 3, 5)
    def generate_email(self):
        logger.info("Generating email address.")
        url = "https://gmailnator.p.rapidapi.com/generate-email"
        payload = {"options": [6]}
        headers = {
            "content-type": "application/json",
            "X-RapidAPI-Host": "gmailnator.p.rapidapi.com",
            "X-RapidAPI-Key": self._api_key,
        }
        response = requests.request("POST", url, json=payload, headers=headers)
        json_load = response.json()
        logger.info(f"Email address generated {json_load['email']}")
        return json_load["email"]

    def retrieve_discord_verification_url(self, email: str):
        inbox_resp = self.get_inbox(email=email)
        message = self.get_message(inbox_resp[0]["id"])
        return message["content"].lower().split("verify email")[0].split("a href=")[1].split('"')[1]

    @retry(Exception, 3, 5)
    def get_inbox(self, email: str):
        url = "https://gmailnator.p.rapidapi.com/inbox"

        payload = {"email": email, "limit": 10}
        headers = {
            "content-type": "application/json",
            "X-RapidAPI-Host": "gmailnator.p.rapidapi.com",
            "X-RapidAPI-Key": self._api_key,
        }

        response = requests.request("POST", url, json=payload, headers=headers)

        return response.json()

    @retry(Exception, 3, 5)
    def get_message(self, msg_id: str):
        url = "https://gmailnator.p.rapidapi.com/messageid"

        querystring = {"id": msg_id}

        headers = {
            "X-RapidAPI-Host": "gmailnator.p.rapidapi.com",
            "X-RapidAPI-Key": self._api_key,
        }

        response = requests.request("GET", url, headers=headers, params=querystring)

        return response.json()
