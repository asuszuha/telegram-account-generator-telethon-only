import time

from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from appium.webdriver.common.touch_action import TouchAction
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait  # type: ignore


class SocksDroid:
    def __init__(self, driver: webdriver.webdriver.WebDriver):
        self._driver = driver
        self._package_name = "net.typeblog.socks"
        self._driver.terminate_app("net.typeblog.socks")
        self._driver.activate_app(self._package_name)

    def is_emulator(self, device_name: str):
        return "emulator" in device_name.lower()

    def enable_proxy(self):
        toggle_button = self._driver.find_element(by=AppiumBy.ID, value="net.typeblog.socks:id/switch_action_button")
        if toggle_button.get_attribute("checked") == "false":
            toggle_button.click()
            time.sleep(10)

    def disable_proxy(self):
        toggle_button = self._driver.find_element(by=AppiumBy.ID, value="net.typeblog.socks:id/switch_action_button")
        if toggle_button.get_attribute("checked") == "false":
            toggle_button.click()
            time.sleep(2)

    def set_proxy_socks_droid(self, ip_address: str, port: str, username: str, password: str):
        toggle_button = WebDriverWait(self._driver, 30).until(
            expected_conditions.presence_of_element_located((AppiumBy.ID, "net.typeblog.socks:id/switch_action_button"))
        )
        if toggle_button.get_attribute("checked") == "true":
            toggle_button.click()

        # Set IP
        server_ip_open = WebDriverWait(self._driver, 30).until(
            expected_conditions.presence_of_element_located(
                (
                    AppiumBy.XPATH,
                    (
                        "//android.widget.LinearLayout[2]//android.widget.RelativeLayout"
                        "//android.widget.TextView[@text='Server IP']"
                    ),
                )
            )
        )
        server_ip_open.click()

        server_ip_edit = WebDriverWait(self._driver, 30).until(
            expected_conditions.presence_of_element_located((AppiumBy.ID, "android:id/edit"))
        )
        server_ip_edit.clear()
        server_ip_edit.send_keys(ip_address)

        server_ip_ok = WebDriverWait(self._driver, 30).until(
            expected_conditions.presence_of_element_located((AppiumBy.ID, "android:id/button1"))
        )
        server_ip_ok.click()

        # Set Port
        server_port_open = WebDriverWait(self._driver, 30).until(
            expected_conditions.presence_of_element_located(
                (
                    AppiumBy.XPATH,
                    "//android.widget.RelativeLayout//android.widget.TextView[@text='Server Port']",
                )
            )
        )
        server_port_open.click()

        server_port_edit = WebDriverWait(self._driver, 30).until(
            expected_conditions.presence_of_element_located((AppiumBy.ID, "android:id/edit"))
        )
        server_port_edit.clear()
        server_port_edit.send_keys(port)

        server_port_ok = WebDriverWait(self._driver, 30).until(
            expected_conditions.presence_of_element_located((AppiumBy.ID, "android:id/button1"))
        )
        server_port_ok.click()
        # Username and password activation
        username_pass_cb = WebDriverWait(self._driver, 30).until(
            expected_conditions.presence_of_element_located(
                (
                    AppiumBy.XPATH,
                    "//android.widget.LinearLayout[7]//android.widget.LinearLayout//android.widget.CheckBox",
                )
            )
        )

        if username_pass_cb.get_attribute("checked") == "false":
            username_pass_cb.click()

        # Scroll to reach username
        action = TouchAction(self._driver)
        action.press(username_pass_cb).move_to(server_port_open).release().perform()

        # Set Username
        set_username = WebDriverWait(self._driver, 30).until(
            expected_conditions.presence_of_element_located(
                (
                    AppiumBy.XPATH,
                    "//android.widget.RelativeLayout//android.widget.TextView[@text='Username']",
                )
            )
        )
        set_username.click()

        set_username_edit = WebDriverWait(self._driver, 30).until(
            expected_conditions.presence_of_element_located((AppiumBy.ID, "android:id/edit"))
        )
        set_username_edit.clear()
        set_username_edit.send_keys(username)

        set_username_ok = WebDriverWait(self._driver, 30).until(
            expected_conditions.presence_of_element_located((AppiumBy.ID, "android:id/button1"))
        )
        set_username_ok.click()

        # Set Password
        set_password = WebDriverWait(self._driver, 30).until(
            expected_conditions.presence_of_element_located(
                (
                    AppiumBy.XPATH,
                    "//android.widget.RelativeLayout//android.widget.TextView[@text='Password']",
                )
            )
        )
        set_password.click()

        set_password_edit = WebDriverWait(self._driver, 30).until(
            expected_conditions.presence_of_element_located((AppiumBy.ID, "android:id/edit"))
        )
        set_password_edit.clear()
        set_password_edit.send_keys(password)

        set_password_ok = WebDriverWait(self._driver, 30).until(
            expected_conditions.presence_of_element_located((AppiumBy.ID, "android:id/button1"))
        )
        set_password_ok.click()

    def end_process(self):
        self._driver.quit()
