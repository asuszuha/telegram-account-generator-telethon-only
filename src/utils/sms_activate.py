from typing import Optional

from smsactivate.api import SMSActivateAPI


class SmsActivateException(Exception):
    pass


class NoNumbersException(SmsActivateException):
    pass


class StatusException(SmsActivateException):
    pass


class CannotRetrieveCountries(SmsActivateException):
    pass


global list_of_countries


class SmsActivate:
    def __init__(self, api_key: str, service: Optional[str] = "tg"):
        self._sms_api = SMSActivateAPI(api_key)
        self._countries = self.get_all_countries()
        self._service = service

    def get_all_countries(self):
        self._all_info_countries = self._sms_api.getCountries()
        if "error" in self._all_info_countries.keys():
            raise CannotRetrieveCountries(self._all_info_countries["message"])
        list_of_countries = []
        for key, value in self._all_info_countries.items():
            list_of_countries.append(value["eng"])

        return list_of_countries

    def get_number(self, country: str):
        country_id = self._countries.index(country)
        number = self._sms_api.getNumber(service=self._service, country=country_id, verification="false")
        if "error" in number.keys():
            raise NoNumbersException(number["message"])

        return number

    def get_status(self, activation_id: int):
        response = self._sms_api.getStatus(activation_id)
        if type(response) is dict and "error" in response.keys():
            raise StatusException(response["message"])
        if type(response) == str and "WAIT_CODE" in response.upper():  # type: ignore
            raise StatusException("Waiting for status")
        return response.split(":")[1]  # type: ignore

    def set_status(self, activation_id: int, status: int):
        response = self._sms_api.setStatus(id=activation_id, status=status)
        return response
