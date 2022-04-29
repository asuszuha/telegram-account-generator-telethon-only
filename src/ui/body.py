import configparser
import tkinter.messagebox as tkmb
from enum import Enum
from tkinter import StringVar, ttk

from idlelib.tooltip import Hovertip

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
        self._sms_activate_client = None

    def _create_first_column(self):
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

        lbl_sms_timeout.grid(row=0, column=0, sticky="w", padx=(5, 5))
        self._entry_sms_timeout.grid(row=1, column=0, sticky="w", padx=(10, 5))

        lbl_select_sms_op.grid(row=2, column=0, sticky="w", padx=(5, 5))
        self._cbox_select_sms_op.grid(row=3, column=0, sticky="w", padx=(10, 5))

        lbl_select_country = ttk.Label(self, text="Select SMS Country:")
        self._cbox_select_country = ttk.Combobox(
            self,
            state="readonly",
            values=["Select"],
        )
        set_cbox_attributes(self._cbox_select_country)
        lbl_select_country.grid(row=4, column=0, sticky="w", padx=(5, 5))
        self._cbox_select_country.grid(row=5, column=0, sticky="w", padx=(10, 5))

    def _create_second_column(self):
        # Registration Counter
        lbl_register_account = ttk.Label(self, text="Number of accounts to Register:")

        self._entry_register_account = ttk.Entry(
            self,
        )
        self._entry_register_account.insert(0, "0")
        hvr_tip = Hovertip(self._entry_register_account, "No limit if value set to zero")  # noqa

        self._entry_register_account.bind("<KeyRelease>", self._check_register_amount)

        lbl_register_account.grid(row=0, column=1, sticky="w", padx=(5, 5))
        self._entry_register_account.grid(row=1, column=1, sticky="w", padx=(10, 5))

        lbl_select_sms_op = ttk.Label(self, text="After Code Received:")
        self.var_sms_after_option = StringVar(value="cancel")
        r_cancel = ttk.Radiobutton(self, text="Cancel Number", value="cancel", variable=self.var_sms_after_option)
        r_none = ttk.Radiobutton(self, text="None", value="none", variable=self.var_sms_after_option)
        lbl_select_sms_op.grid(row=2, column=1, sticky="w", padx=(5, 5))
        r_cancel.grid(row=3, column=1, sticky="w", padx=(10, 5))
        r_none.grid(row=4, column=1, sticky="w", padx=(10, 5))

    def read_api_keys_of_sim_providers(self):
        config_file = configparser.ConfigParser()
        config_file.read("sim_provider_config.ini")
        sim_5_api_key = config_file["SIMProviderAPIKeys"]["5sim_api_key"]
        sms_activate_api_key = config_file["SIMProviderAPIKeys"]["sms_activate_api_key"]
        return sim_5_api_key, sms_activate_api_key

    def _check_sms_timeout(self, event):
        current_val = self._entry_sms_timeout.get()

        if len(current_val) > 3 and current_val.isnumeric():
            self._entry_sms_timeout.delete(len(current_val) - 1)
            tkmb.showerror("Maximum Timeout", "Maximum timeout is 999 seconds.")

        if not current_val.isnumeric() and len(current_val) > 0:
            self._entry_sms_timeout.delete(len(current_val) - 1)
            tkmb.showerror("Not Numeric", "Please enter only numbers.")

    def _check_register_amount(self, event):
        current_val = self._entry_register_account.get()

        if len(current_val) > 3 and current_val.isnumeric():
            self._entry_register_account.delete(len(current_val) - 1)
            tkmb.showerror(
                "Maximum Account To Register",
                "Maximum account to register is 9999. Please put value between 1 to 9999.",
            )

        if not current_val.isnumeric() and len(current_val) > 0:
            self._entry_register_account.delete(len(current_val) - 1)
            tkmb.showerror("Not Numeric", "Please enter only numbers.")

    def on_select_sms_op(self, event):
        sim_5_api_key, sms_activate_api_key = self.read_api_keys_of_sim_providers()
        if self._cbox_select_sms_op.get() == SMSOperators.SMSACTIVATE.value:
            # reset country values
            self._cbox_select_country["values"] = ["Select"]
            try:
                if not sms_activate_api_key:
                    tkmb.showerror("No SMS API-KEY", "No API key provided for SMS Activate.")
                    self._cbox_select_sms_op.current(0)
                    return
                self._sms_activate_client = SmsActivate(sms_activate_api_key)
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
                if not sim_5_api_key:
                    tkmb.showerror("No SMS API-KEY", "No API key provided for SMS Activate.")
                    self._cbox_select_sms_op.current(0)
                    return
                self._sim5_net_client = Sim5Net(sim_5_api_key)
                countries = self._sim5_net_client.get_countries()
                self._sms_activate_client = None
            except Exception as ex:
                tkmb.showerror("Error Occured", str(ex))
                self._cbox_select_sms_op.current(0)
                return
            countries.insert(0, "Select")
            self._cbox_select_country["values"] = countries

    def run(self):
        sms_operator = self._cbox_select_sms_op.get()
        if sms_operator == "Select":
            tkmb.showerror("No SMS Operator Selected", "Please select SMS operator provider.")
            return

        sms_timeout = self._entry_sms_timeout.get()
        if sms_timeout == "" or int(sms_timeout) < 10:
            tkmb.showerror("No SMS Timeout Defined", "Please define sms time out between 10 to 999.")
            return

        current_sms_operator = None
        sim_5_api_key, sms_activate_api_key = self.read_api_keys_of_sim_providers()

        if self._cbox_select_sms_op.get() == SMSOperators.SMSACTIVATE.value:
            if not sms_activate_api_key:
                tkmb.showerror("No SMS API-KEY", "No API key provided for SMS Activate.")
                self._cbox_select_sms_op.current(0)
                return
            self._sms_activate_client = SmsActivate(sms_activate_api_key)
            current_sms_operator = self._sms_activate_client
        elif self._cbox_select_sms_op.get() == SMSOperators.SMS5SIMNET.value:
            if not sim_5_api_key:
                tkmb.showerror("No SMS API-KEY", "No API key provided for SMS Activate.")
                self._cbox_select_sms_op.current(0)
                return
            self._sim5_net_client = Sim5Net(sim_5_api_key)
            current_sms_operator = self._sim5_net_client

        country = self._cbox_select_country.get()
        if country == "Select":
            tkmb.showerror("No Country Selected", "Please select SMS operator country.")
            return

        if not self.frame_thread or not self.frame_thread.is_alive():
            self.frame_thread = RegisterTelegram(
                sms_operator=current_sms_operator,  # type: ignore
                country=country,
                sms_timeout=sms_timeout,
                sms_after_code_op=self.var_sms_after_option.get(),
                maximum_register=self._entry_register_account.get(),
            )
            self.frame_thread = self.frame_thread
            self.frame_thread.start()
            self.frame_thread.delete_unsuccessful_session()

        else:
            self.frame_thread.resume()
