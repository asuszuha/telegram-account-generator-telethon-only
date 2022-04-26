from typing import Any, Optional

import requests
from pydantic import BaseModel
from retry import retry


class Sim5NetException(Exception):
    pass


class PurchaseNotPossibleException(Sim5NetException):
    pass


class Sim5StatusException(Sim5NetException):
    pass


class NoFreePhoneException(Sim5NetException):
    pass


class PurchaseModel(BaseModel):
    id: int
    phone: str
    operator: str
    product: str
    price: float
    status: str
    expires: str
    sms: Optional[Any]
    created_at: str
    forwarding: Optional[bool]
    forwarding_number: Optional[str]
    country: str


class Sim5Net:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-type": "application/json",
        }
        self._operator = "any"
        self._product = "telegram"
        self._list_of_countries = None

    def get_countries(self):
        country_url = r"https://5sim.net/v1/guest/countries"
        response = requests.get(country_url, headers=self.headers)

        self._list_of_countries = list(response.json().keys())

        return self._list_of_countries

    @retry(Exception, 3, 3)
    def purchase_number(
        self,
        country: str,
    ):
        response = requests.get(
            f"https://5sim.net/v1/user/buy/activation/{country}/{self._operator}/{self._product}", headers=self.headers
        )

        if response.status_code != 200:
            raise PurchaseNotPossibleException(f"Error occured with message: {response.reason}")
        if "no free phones" in response.text.lower():
            raise NoFreePhoneException(f"No free phones found in {country}.")

        return PurchaseModel(**response.json())

    def get_status_code(self, id: int):
        response = requests.get("https://5sim.net/v1/user/check/" + str(id), headers=self.headers)
        response_json = response.json()
        if not response_json["sms"]:
            raise Sim5StatusException("No sms received yet.")

        return response_json["sms"][0]["code"]
