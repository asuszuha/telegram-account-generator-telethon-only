import tkinter.messagebox as tkmb
from enum import Enum
from tkinter import ttk

from src.automation.register_telegram import RegisterTelegram
from src.ui.abstract_frame_ui import AbstractFrame
from src.ui.generic_styles import set_cbox_attributes
from src.utils.adb_helper import ADBHelper
from src.utils.sim5_net import Sim5Net
from src.utils.sms_activate import SmsActivate, SmsActivateException


class SMSOperators(Enum):
    SMS5SIMNET = "5sim.net"
    SMSACTIVATE = "sms-active.org"


SMS_OPERATORS = ["Select", SMSOperators.SMS5SIMNET.value, SMSOperators.SMSACTIVATE.value]


class BodyTelegramBot(AbstractFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.adb_helper = ADBHelper()
        self._create_first_column()
        self._create_second_column()
        self._loaded_list_of_names = None
        self._loaded_list_of_proxies = None
        self._loaded_list_of_passwords = None
        self._profile_image_directory = None
        self._sms_activate_client = None

    def _create_first_column(self):
        lbl_tg_api_id = ttk.Label(self, text="Telegram API Id:")
        self._entry_tg_api_id = ttk.Entry(self)

        lbl_tg_api_id.grid(row=0, column=0, sticky="w", padx=(5, 5))
        self._entry_tg_api_id.grid(row=1, column=0, sticky="w", padx=(10, 5))

        lbl_tg_api_hash = ttk.Label(self, text="Telegram API Hash:")
        self._entry_tg_api_hash = ttk.Entry(self)

        lbl_tg_api_hash.grid(row=2, column=0, sticky="w", padx=(5, 5))
        self._entry_tg_api_hash.grid(row=3, column=0, sticky="w", padx=(10, 5))

    def _create_second_column(self):
        lbl_sms_api_key = ttk.Label(self, text="SMS Provider API-KEY:")
        self._entry_sms_api_key = ttk.Entry(self)

        lbl_sms_api_key.grid(row=0, column=1, sticky="w", padx=(5, 5))
        self._entry_sms_api_key.grid(row=1, column=1, sticky="w", padx=(10, 5))

        lbl_select_sms_op = ttk.Label(self, text="Select SMS Provider:")
        self._cbox_select_sms_op = ttk.Combobox(
            self,
            state="readonly",
            values=SMS_OPERATORS,
        )

        set_cbox_attributes(self._cbox_select_sms_op)
        self._cbox_select_sms_op.bind("<<ComboboxSelected>>", self.on_select_sms_op)

        lbl_sms_timeout = ttk.Label(self, text="SMS Timeout (seconds):")
        self._entry_sms_timeout = ttk.Entry(self)
        self._entry_sms_timeout.bind("<KeyRelease>", self._check_sms_timeout)

        lbl_sms_timeout.grid(row=2, column=1, sticky="w", padx=(5, 5))
        self._entry_sms_timeout.grid(row=3, column=1, sticky="w", padx=(10, 5))

        lbl_select_sms_op.grid(row=4, column=1, sticky="w", padx=(5, 5))
        self._cbox_select_sms_op.grid(row=5, column=1, sticky="w", padx=(10, 5))

        lbl_select_country = ttk.Label(self, text="Select SMS Country:")
        self._cbox_select_country = ttk.Combobox(
            self,
            state="readonly",
            values=["Select"],
        )
        set_cbox_attributes(self._cbox_select_country)
        lbl_select_country.grid(row=6, column=1, sticky="w", padx=(5, 5))
        self._cbox_select_country.grid(row=7, column=1, sticky="w", padx=(10, 5))

    def _check_sms_timeout(self, event):
        current_val = self._entry_sms_timeout.get()

        if len(current_val) > 3 and current_val.isnumeric():
            self._entry_sms_timeout.delete(len(current_val) - 1)
            tkmb.showerror("Maximum Timeout", "Maximum timeout is 999 seconds.")

        if not current_val.isnumeric() and len(current_val) > 0:
            self._entry_sms_timeout.delete(len(current_val) - 1)
            tkmb.showerror("Not Numeric", "Please enter only numbers.")

    def on_select_sms_op(self, event):
        api_key = self._entry_sms_api_key.get()
        if not api_key:
            tkmb.showerror("No SMS API-KEY", "No API key provided.")
            self._cbox_select_sms_op.current(0)
            return

        if self._cbox_select_sms_op.get() == SMSOperators.SMSACTIVATE.value:
            # reset country values
            self._cbox_select_country["values"] = ["Select"]

            try:
                self._sms_activate_client = SmsActivate(api_key)
                countries = self._sms_activate_client.get_all_countries()
                self._sim5_net_client = None
            except SmsActivateException as ex:
                tkmb.showerror("Error Occured", str(ex))
                self._cbox_select_sms_op.current(0)
                return

            countries.insert(0, "Select")
            self._cbox_select_country["values"] = countries
        elif self._cbox_select_sms_op.get() == SMSOperators.SMS5SIMNET.value:
            # reset country values
            self._cbox_select_country["values"] = ["Select"]

            try:
                self._sim5_net_client = Sim5Net(api_key)
                countries = self._sim5_net_client.get_countries()
                self._sms_activate_client = None
            except Exception as ex:
                tkmb.showerror("Error Occured", str(ex))
                self._cbox_select_sms_op.current(0)
                return
            countries.insert(0, "Select")
            self._cbox_select_country["values"] = countries

    def run(self):
        api_key = self._entry_sms_api_key.get()
        if not api_key:
            tkmb.showerror("No API Key", "Please enter API Key.")
            return

        sms_operator = self._cbox_select_sms_op.get()
        if sms_operator == "Select":
            tkmb.showerror("No SMS Operator Selected", "Please select SMS operator provider.")
            return

        sms_timeout = self._entry_sms_timeout.get()
        if sms_timeout == "" or int(sms_timeout) < 10:
            tkmb.showerror("No SMS Timeout Defined", "Please define sms time out between 10 to 999.")
            return

        current_sms_operator = None
        if self._cbox_select_sms_op.get() == SMSOperators.SMSACTIVATE.value:
            self._sms_activate_client = SmsActivate(api_key)
            current_sms_operator = self._sms_activate_client
        elif self._cbox_select_sms_op.get() == SMSOperators.SMS5SIMNET.value:
            self._sim5_net_client = Sim5Net(api_key)
            current_sms_operator = self._sim5_net_client

        country = self._cbox_select_country.get()
        if country == "Select":
            tkmb.showerror("No Country Selected", "Please select SMS operator country.")
            return

        tg_api_id = self._entry_tg_api_id.get()
        if not tg_api_id:
            tkmb.showerror("No TG API Id", "Please enter telegram API id.")
            return

        tg_api_hash = self._entry_tg_api_hash.get()
        if not tg_api_hash:
            tkmb.showerror("No TG API Hash", "Please enter telegram API hash.")
            return

        if not self.frame_thread or not self.frame_thread.is_alive():
            self.frame_thread = RegisterTelegram(
                sms_operator=current_sms_operator,  # type: ignore
                country=country,
                tg_api_id=tg_api_id,
                tg_api_hash=tg_api_hash,
                sms_timeout=sms_timeout,
            )
            self.frame_thread = self.frame_thread
            self.frame_thread.start()

        else:
            self.frame_thread.resume()
