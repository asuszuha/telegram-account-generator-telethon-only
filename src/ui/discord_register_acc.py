import configparser
import tkinter.messagebox as tkmb
from enum import Enum
from tkinter import IntVar, StringVar, ttk

from idlelib.tooltip import Hovertip

from src.discord.register_discord import DiscordAccGenerator
from src.ui.abstract_frame_ui import AbstractTab
from src.ui.generic_styles import set_cbox_attributes
from src.utils.paths import GENERATE_DISCORD_ACCOUNT_DIR
from src.utils.sim5_net import Sim5Net
from src.utils.sms_activate import SmsActivate, SmsActivateException


class SMSOperators(Enum):
    SMS5SIMNET = "5sim.net"
    SMSACTIVATE = "sms-active.org"


SMS_OPERATORS = ["Select", SMSOperators.SMS5SIMNET.value, SMSOperators.SMSACTIVATE.value]


class AutoRegisterDiscord(AbstractTab):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._create_first_column()
        self._create_second_column()
        self._sms_activate_client = None

    def _create_first_column(self):
        lbl_frame_general_settings = ttk.LabelFrame(self, text="General Settings")
        lbl_frame_general_settings.grid(row=0, column=0, sticky="nsw", padx=(5, 5))
        # Verify email checkbox
        self.var_email_verification_enabled = IntVar(value=0)
        _chb_email_ver_enabled = ttk.Checkbutton(
            lbl_frame_general_settings, text="Enable email verification", variable=self.var_email_verification_enabled
        )
        _chb_email_ver_enabled.grid(row=0, column=0, sticky="w", padx=(5, 5))

        # Enable proxy settings
        self.var_proxy_enabled = IntVar(value=0)
        _chb_proxy_enabled = ttk.Checkbutton(
            lbl_frame_general_settings, text="Enable proxy", variable=self.var_proxy_enabled
        )
        _chb_proxy_enabled.grid(row=1, column=0, sticky="w", padx=(5, 5))

        # Registration Counter
        lbl_register_account = ttk.Label(lbl_frame_general_settings, text="Number of accounts to Register:")

        self._entry_register_account = ttk.Entry(
            lbl_frame_general_settings,
        )
        self._entry_register_account.insert(0, "0")
        hvr_tip = Hovertip(self._entry_register_account, "No limit if value set to zero")  # noqa

        self._entry_register_account.bind("<KeyRelease>", self._check_register_amount)

        lbl_register_account.grid(row=2, column=0, sticky="w", padx=(5, 5))
        self._entry_register_account.grid(row=3, column=0, sticky="w", padx=(10, 5))

    def _create_second_column(self):
        lbl_frame_sms_settings = ttk.LabelFrame(self, text="SMS Settings")
        lbl_frame_sms_settings.grid(row=0, column=1, sticky="nsw", padx=(5, 5))
        # Verify sms checkbox
        self.var_sms_verification_enabled = IntVar(value=0)
        _chb_sms_ver_enabled = ttk.Checkbutton(
            lbl_frame_sms_settings,
            text="Enable sms verification",
            variable=self.var_sms_verification_enabled,
            command=self.enable_sms_settings,
        )
        _chb_sms_ver_enabled.grid(row=0, column=1, sticky="w", padx=(5, 5))

        lbl_select_sms_op = ttk.Label(lbl_frame_sms_settings, text="Select SMS Provider:")
        self._cbox_select_sms_op = ttk.Combobox(
            lbl_frame_sms_settings,
            state="readonly",
            values=SMS_OPERATORS,
        )

        set_cbox_attributes(self._cbox_select_sms_op)
        self._cbox_select_sms_op.bind("<<ComboboxSelected>>", self.on_select_sms_op)

        lbl_sms_timeout = ttk.Label(lbl_frame_sms_settings, text="SMS Timeout (seconds):")
        self._entry_sms_timeout = ttk.Entry(lbl_frame_sms_settings)
        self._entry_sms_timeout.bind("<KeyRelease>", self._check_sms_timeout)

        lbl_sms_timeout.grid(row=1, column=1, sticky="w", padx=(5, 5))
        self._entry_sms_timeout.grid(row=2, column=1, sticky="w", padx=(10, 5))

        lbl_select_sms_op.grid(row=3, column=1, sticky="w", padx=(5, 5))
        self._cbox_select_sms_op.grid(row=4, column=1, sticky="w", padx=(10, 5))

        lbl_select_country = ttk.Label(lbl_frame_sms_settings, text="Select SMS Country:")
        self._cbox_select_country = ttk.Combobox(
            lbl_frame_sms_settings,
            state="readonly",
            values=["Select"],
        )
        set_cbox_attributes(self._cbox_select_country)
        lbl_select_country.grid(row=5, column=1, sticky="w", padx=(5, 5))
        self._cbox_select_country.grid(row=6, column=1, sticky="w", padx=(10, 5))

        lbl_select_sms_op = ttk.Label(lbl_frame_sms_settings, text="After Code Received:")
        self.var_sms_after_option = StringVar(value="cancel")
        self.r_cancel = ttk.Radiobutton(
            lbl_frame_sms_settings, text="Cancel Number", value="cancel", variable=self.var_sms_after_option
        )
        self.r_none = ttk.Radiobutton(
            lbl_frame_sms_settings, text="None", value="none", variable=self.var_sms_after_option
        )
        lbl_select_sms_op.grid(row=7, column=1, sticky="w", padx=(5, 5))
        self.r_cancel.grid(row=8, column=1, sticky="w", padx=(10, 5))
        self.r_none.grid(row=9, column=1, sticky="w", padx=(10, 5))

        self.enable_sms_settings()

    def enable_sms_settings(self):
        if self.var_sms_verification_enabled.get():
            self._cbox_select_sms_op["state"] = "normal"
            self._entry_sms_timeout["state"] = "normal"
            self._cbox_select_country["state"] = "normal"
            self.r_cancel["state"] = "normal"
            self.r_none["state"] = "normal"
        else:
            self._cbox_select_sms_op["state"] = "disabled"
            self._entry_sms_timeout["state"] = "disabled"
            self._cbox_select_country["state"] = "disabled"
            self.r_cancel["state"] = "disabled"
            self.r_none["state"] = "disabled"

    def read_api_keys_from_file(self):
        config_file = configparser.ConfigParser()
        config_file.read(rf"{GENERATE_DISCORD_ACCOUNT_DIR}\api_config.ini")
        sim_5_api_key = config_file["APIKeysForProviders"]["5sim_api_key"]
        sms_activate_api_key = config_file["APIKeysForProviders"]["sms_activate_api_key"]
        anti_captcha_api_key = config_file["APIKeysForProviders"]["anti_captcha_api_key"]
        kopeechka_api_key = config_file["APIKeysForProviders"]["kopeechka_api_key"]
        return kopeechka_api_key, anti_captcha_api_key, sim_5_api_key, sms_activate_api_key

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

        if len(current_val) > 4 and current_val.isnumeric():
            self._entry_register_account.delete(len(current_val) - 1)
            tkmb.showerror(
                "Maximum Account To Register",
                "Maximum account to register is 9999. Please put value between 1 to 9999.",
            )

        if not current_val.isnumeric() and len(current_val) > 0:
            self._entry_register_account.delete(len(current_val) - 1)
            tkmb.showerror("Not Numeric", "Please enter only numbers.")

    def on_select_sms_op(self, event):
        kepcheeka_api_key, anti_captcha_key, sim_5_api_key, sms_activate_api_key = self.read_api_keys_from_file()
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
        sms_verification_enabled = self.var_sms_verification_enabled.get()
        kopeechka_api_key, anti_captcha_api_key, sim_5_api_key, sms_activate_api_key = self.read_api_keys_from_file()
        current_sms_operator = None

        if sms_verification_enabled:
            if sms_operator == "Select":
                tkmb.showerror("No SMS Operator Selected", "Please select SMS operator provider.")
                return

            sms_timeout = self._entry_sms_timeout.get()
            if sms_timeout == "" or int(sms_timeout) < 10:
                tkmb.showerror("No SMS Timeout Defined", "Please define sms time out between 10 to 999.")
                return

            if self._cbox_select_sms_op.get() == SMSOperators.SMSACTIVATE.value:
                if not sms_activate_api_key:
                    tkmb.showerror("No SMS API-KEY", "No API key provided for SMS Activate.")
                    self._cbox_select_sms_op.current(0)
                    return
                self._sms_activate_client = SmsActivate(api_key=sms_activate_api_key, service="ds")
                current_sms_operator = self._sms_activate_client
            elif self._cbox_select_sms_op.get() == SMSOperators.SMS5SIMNET.value:
                if not sim_5_api_key:
                    tkmb.showerror("No SMS API-KEY", "No API key provided for SMS Activate.")
                    self._cbox_select_sms_op.current(0)
                    return
                self._sim5_net_client = Sim5Net(api_key=sim_5_api_key, product="discord")
                current_sms_operator = self._sim5_net_client

            country = self._cbox_select_country.get()
            if country == "Select":
                tkmb.showerror("No Country Selected", "Please select SMS operator country.")
                return

        if not self.frame_thread or not self.frame_thread.is_alive():
            if sms_verification_enabled:
                self.frame_thread = DiscordAccGenerator(
                    kopeechka_api_key=kopeechka_api_key,
                    email_verification_enabled=self.var_email_verification_enabled.get(),
                    sms_verification_enabled=sms_verification_enabled,
                    sms_operator=current_sms_operator,
                    country=country,
                    sms_timeout=sms_timeout,
                    sms_after_code_op=self.var_sms_after_option.get(),
                    anticaptcha_api_key=anti_captcha_api_key,
                    proxy_enabled=self.var_proxy_enabled.get(),
                )
            else:
                self.frame_thread = DiscordAccGenerator(
                    kopeechka_api_key=kopeechka_api_key,
                    email_verification_enabled=self.var_email_verification_enabled.get(),
                    sms_verification_enabled=sms_verification_enabled,
                    anticaptcha_api_key=anti_captcha_api_key,
                    proxy_enabled=self.var_proxy_enabled.get(),
                )
            self.frame_thread = self.frame_thread
            self.frame_thread.start()
        else:
            self.frame_thread.resume()
