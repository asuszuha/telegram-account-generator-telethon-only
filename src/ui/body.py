import tkinter as tk
import tkinter.messagebox as tkmb
from enum import Enum
from tkinter import filedialog as fd
from tkinter import ttk

from src.automation.register_telegram import RegisterTelegram
from src.ui.abstract_frame_ui import AbstractFrame
from src.ui.generic_styles import set_cbox_attributes
from src.utils.adb_helper import ADBHelper
from src.utils.logger import logger
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
        self._create_third_column()
        self._loaded_list_of_names = None
        self._loaded_list_of_proxies = None
        self._loaded_list_of_passwords = None
        self._profile_image_directory = None
        self._output_folder_directory = None
        self._sms_activate_client = None

    def _create_first_column(self):
        lbl_select_device = ttk.Label(self, text="Select Android Device:")
        self._cbox_select_device = ttk.Combobox(
            self,
            state="readonly",
            values=["Select"],
        )
        set_cbox_attributes(self._cbox_select_device)
        self._cbox_select_device.bind("<Button-1>", self.load_devices)

        lbl_select_device.grid(row=0, column=0, sticky="w", padx=(5, 5))
        self._cbox_select_device.grid(row=1, column=0, sticky="w", padx=(10, 5))

        lbl_sms_api_key = ttk.Label(self, text="SMS Provider API-KEY:")
        self._entry_sms_api_key = ttk.Entry(self)

        lbl_sms_api_key.grid(row=2, column=0, sticky="w", padx=(5, 5))
        self._entry_sms_api_key.grid(row=3, column=0, sticky="w", padx=(10, 5))

        lbl_select_sms_op = ttk.Label(self, text="Select SMS Provider:")
        self._cbox_select_sms_op = ttk.Combobox(
            self,
            state="readonly",
            values=SMS_OPERATORS,
        )

        set_cbox_attributes(self._cbox_select_sms_op)
        self._cbox_select_sms_op.bind("<<ComboboxSelected>>", self.on_select_sms_op)

        lbl_select_sms_op.grid(row=4, column=0, sticky="w", padx=(5, 5))
        self._cbox_select_sms_op.grid(row=5, column=0, sticky="w", padx=(10, 5))

        lbl_select_country = ttk.Label(self, text="Select SMS Country:")
        self._cbox_select_country = ttk.Combobox(
            self,
            state="readonly",
            values=["Select"],
        )
        set_cbox_attributes(self._cbox_select_country)
        lbl_select_country.grid(row=6, column=0, sticky="w", padx=(5, 5))
        self._cbox_select_country.grid(row=7, column=0, sticky="w", padx=(10, 5))

    def _create_second_column(self):
        lbl_tg_api_id = ttk.Label(self, text="Telegram API Id:")
        self._entry_tg_api_id = ttk.Entry(self)

        lbl_tg_api_id.grid(row=0, column=1, sticky="w", padx=(5, 5))
        self._entry_tg_api_id.grid(row=1, column=1, sticky="w", padx=(10, 5))

        lbl_tg_api_hash = ttk.Label(self, text="Telegram API Hash:")
        self._entry_tg_api_hash = ttk.Entry(self)

        lbl_tg_api_hash.grid(row=2, column=1, sticky="w", padx=(5, 5))
        self._entry_tg_api_hash.grid(row=3, column=1, sticky="w", padx=(10, 5))

    def _create_third_column(self):
        self._var_proxy_status = tk.IntVar(self)
        cb_proxy_enable = ttk.Checkbutton(self, text="Enable Proxy", state="", variable=self._var_proxy_status)
        cb_proxy_enable.bind("<Button-1>", self._switch_upload_proxy_file_btn)

        cb_proxy_enable.grid(row=0, column=2, sticky="w", padx=(5, 5))

        lbl_select_proxy_file = ttk.Label(self, text="Select Proxy List:")
        self._btn_choose_proxy_file = ttk.Button(
            self, text="Choose File", command=self.load_list_of_proxies, state=tk.DISABLED
        )
        self._lbl_choose_proxy_file = ttk.Label(self, text="No file choosen", wraplength=300)

        lbl_select_proxy_file.grid(row=1, column=2, sticky="ws", padx=(5, 5))
        self._btn_choose_proxy_file.grid(row=2, column=2, sticky="ws", padx=(10, 5))
        self._lbl_choose_proxy_file.grid(row=2, column=3, sticky="ws", padx=(5, 5))

        lbl_select_password_file = ttk.Label(self, text="Select File of 2FA passwords:")
        btn_choose_password_file = ttk.Button(self, text="Choose File", command=self.load_list_of_passwords)
        self._lbl_choose_password_file = ttk.Label(self, text="No file choosen", wraplength=300)

        lbl_select_password_file.grid(row=3, column=2, sticky="ws", padx=(5, 5))
        btn_choose_password_file.grid(row=4, column=2, sticky="ws", padx=(10, 5))
        self._lbl_choose_password_file.grid(row=4, column=3, sticky="ws", padx=(5, 5))

        lbl_select_profile_img = ttk.Label(self, text="Select Directory of Profile Images:")
        btn_choose_directory_profile_img = ttk.Button(
            self, text="Choose Directory", command=self.select_profile_img_directory
        )
        self._lbl_directory_prof_img = ttk.Label(self, text="No directory choosen")

        lbl_select_profile_img.grid(row=5, column=2, sticky="ws", padx=(5, 5))
        btn_choose_directory_profile_img.grid(row=6, column=2, sticky="ws", padx=(10, 5))
        self._lbl_directory_prof_img.grid(row=6, column=3, sticky="ws", padx=(5, 5))

        lbl_load_names_list = ttk.Label(self, text="Load List of Names")
        btn_load_names_list = ttk.Button(self, text="Choose File", command=self.load_list_of_names)
        self._lbl_loaded_names_file = ttk.Label(self, text="No file choosen")

        lbl_load_names_list.grid(row=7, column=2, sticky="ws", padx=(5, 5))
        btn_load_names_list.grid(row=8, column=2, sticky="ws", padx=(10, 5))
        self._lbl_loaded_names_file.grid(row=8, column=3, sticky="ws", padx=(5, 5))

        lbl_output_folder = ttk.Label(self, text="Select Output Folder")
        btn_open_output_folder = ttk.Button(self, text="Choose Folder", command=self.select_output_folder_directory)
        self._lbl_output_folder_name = ttk.Label(self, text="No folder choosen")

        lbl_output_folder.grid(row=9, column=2, sticky="ws", padx=(5, 5))
        btn_open_output_folder.grid(row=10, column=2, sticky="ws", padx=(10, 5))
        self._lbl_output_folder_name.grid(row=10, column=3, sticky="ws", padx=(5, 5))

    def _switch_upload_proxy_file_btn(self, event):
        if not self._var_proxy_status.get():
            self._btn_choose_proxy_file["state"] = tk.NORMAL
        else:
            self._btn_choose_proxy_file["state"] = tk.DISABLED

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

    def load_devices(self, event):
        list_of_devices = self.adb_helper.get_devices()
        list_of_devices.insert(0, "Select")

        self._cbox_select_device["values"] = list_of_devices

    def select_profile_img_directory(self):
        self._profile_image_directory = fd.askdirectory(title="Open Directory for Profile Images")
        if self._profile_image_directory:
            self._lbl_directory_prof_img["text"] = self._profile_image_directory

    def select_output_folder_directory(self):
        self._output_folder_directory = fd.askdirectory(title="Open Directory for Output Folder")
        if self._output_folder_directory:
            self._lbl_output_folder_name["text"] = self._output_folder_directory

    def load_list_of_names(self):
        filetypes = (("text files", "*.txt"), ("All files", "*.*"))
        self._loaded_list_of_names = fd.askopenfile(
            title="Open File with List of Names", initialdir="/", filetypes=filetypes
        )
        if self._loaded_list_of_names:
            self._lbl_loaded_names_file["text"] = self._loaded_list_of_names.name
            self._loaded_list_of_names_read = self._loaded_list_of_names.readlines()

    def load_list_of_proxies(self):
        filetypes = (("text files", "*.txt"), ("All files", "*.*"))
        self._loaded_list_of_proxies = fd.askopenfile(
            title="Open File with List of Proxies", initialdir="/", filetypes=filetypes
        )
        if self._loaded_list_of_proxies:
            self._lbl_choose_proxy_file["text"] = self._loaded_list_of_proxies.name
            self._loaded_list_of_proxies_read = self._loaded_list_of_proxies.readlines()

    def load_list_of_passwords(self):
        filetypes = (("text files", "*.txt"), ("All files", "*.*"))
        self._loaded_list_of_passwords = fd.askopenfile(
            title="Open File with List of Passwords", initialdir="/", filetypes=filetypes
        )
        if self._loaded_list_of_passwords:
            self._lbl_choose_password_file["text"] = self._loaded_list_of_passwords.name
            self._loaded_list_of_passwords_read = self._loaded_list_of_passwords.readlines()

    def run(self):
        device_name = self._cbox_select_device.get()
        if device_name == "Select":
            tkmb.showerror("No Device Selected", "Please first select device to run your code.")
            return
        api_key = self._entry_sms_api_key.get()
        if not api_key:
            tkmb.showerror("No API Key", "Please enter API Key.")
            return
        sms_operator = self._cbox_select_sms_op.get()
        if sms_operator == "Select":
            tkmb.showerror("No SMS Operator Selected", "Please select SMS operator provider.")
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

        if not self._profile_image_directory:
            logger.info("No image directory selected. Profile images will not be loaded.")

        if not self._loaded_list_of_names:
            tkmb.showerror("No Names Loaded", "No names file loaded.")
            return
        else:
            with open(self._loaded_list_of_names.name, "r") as fh:
                self._loaded_list_of_names_read = fh.readlines()

        if not self._output_folder_directory:
            tkmb.showerror("No Output Directory", "No output directory selected.")
            return

        if self._var_proxy_status.get() and not self._loaded_list_of_proxies:
            tkmb.showerror("No Proxy File", "No proxy list selected but proxy enabled.")
            return

        if not self._loaded_list_of_passwords:
            logger.info("No password file selected. No 2FA password will set to accounts.")

        if not self.frame_thread or not self.frame_thread.is_alive():
            self.frame_thread = RegisterTelegram(
                device_name=device_name,
                sms_operator=current_sms_operator,  # type: ignore
                country=country,
                names=self._loaded_list_of_names_read,
                filename=self._loaded_list_of_names.name,
                profile_pics_paths=self._profile_image_directory,
                output_dir=self._output_folder_directory,
                tg_api_id=tg_api_id,
                tg_api_hash=tg_api_hash,
                proxy_list=self._loaded_list_of_proxies_read if self._var_proxy_status.get() else None,
                proxy_filename=self._loaded_list_of_proxies.name if self._var_proxy_status.get() else None,  # type: ignore # noqa
                password_filename=self._loaded_list_of_passwords.name if self._loaded_list_of_passwords else None,  # type: ignore # noqa
                password_list=self._loaded_list_of_passwords_read if self._loaded_list_of_passwords else None,
            )
            self.frame_thread = self.frame_thread
            self.frame_thread.start()

        else:
            self.frame_thread.resume()
