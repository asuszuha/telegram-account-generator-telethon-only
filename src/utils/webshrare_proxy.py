from posixpath import split
from this import d
import requests

from retry import retry
from pydantic import BaseModel
from typing import Optional, List
from src.utils.logger import logger


class ProxyPorts(BaseModel):
    http: int
    socks5: int


class ProxyDefinition(BaseModel):
    username: str
    password: str
    proxy_address: str
    ports: ProxyPorts
    valid: bool
    last_verification: str
    country_code: str
    country_code_confidence: int
    city_name: str


class ProxyListResponse(BaseModel):
    count: int
    next: Optional[str]
    previous: Optional[str]
    results: List[ProxyDefinition]


class WebshareProxy:
    def __init__(self, api_key: str, ip_authorized: bool):
        self.ip_authorized = True
        self.api_key = api_key
        self._headers = {"Authorization": f"Token {self.api_key}"}
        self._current_page = None
        self._current_proxy_counter = None

    def _build_proxy_string(self, proxy_info: ProxyDefinition):
        proxy_string = (
            proxy_info.username
            + ":"
            + proxy_info.password
            + "@"
            + proxy_info.proxy_address
            + ":"
            + proxy_info.ports.http
        )
        return proxy_string

    def get_proxy(self):
        if self._current_page and not self._current_proxy_counter < len(self._current_page.results):
            if self._current_page and self._current_page.next:
                response = requests.get(self._current_page.next, headers=self._headers)
                self._current_page = ProxyListResponse(**response.json())
            else:
                response = requests.get("https://proxy.webshare.io/api/proxy/list/?page=1", headers=self._headers)
                self._current_page = ProxyListResponse(**response.json())

        if self._current_proxy_counter is not None:
            self._current_proxy_counter += 1
        else:
            self._current_proxy_counter = 0

        proxy_info = self._current_page.results[self._current_proxy_counter]

        return self._build_proxy_string(proxy_info)

    @staticmethod
    def read_txt_proxy(proxy_list: List[str]):
        splitted_line = proxy_list.replace("\n", "").split(":")
        proxy_address = splitted_line[0]
        port = splitted_line[1]
        username = splitted_line[2]
        password = splitted_line[3]

        proxy_string = username + ":" + password + "@" + proxy_address + ":" + port

        return proxy_string
