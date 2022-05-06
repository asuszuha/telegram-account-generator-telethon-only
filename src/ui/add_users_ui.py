import glob
import os
import tkinter.messagebox as tkmb
from tkinter import IntVar, ttk

from src.automation.add_user_automation import AddUser
from src.utils.paths import AUTO_REGISTER_PATH_DIR

from .abstract_frame_ui import AbstractTab


class AddTgUsers(AbstractTab):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._create_first_column()
        self.parent = parent

    def _create_first_column(self):
        self.var_user_add_option = IntVar(value=0)
        lbl_frame = ttk.LabelFrame(self, text="Available Task List:")
        rd_btn_scrape = ttk.Radiobutton(lbl_frame, text="0: Scrape User", value=0, variable=self.var_user_add_option)
        rd_btn_add_user = ttk.Radiobutton(lbl_frame, text="1: Add User", value=1, variable=self.var_user_add_option)

        lbl_frame.grid(row=0, column=0, sticky="we", padx=(5, 5))
        rd_btn_scrape.grid(row=1, column=0, sticky="w", padx=(10, 5))
        rd_btn_add_user.grid(row=2, column=0, sticky="w", padx=(10, 5))

        self.var_add_user_from = IntVar(value=0)
        lbl_frame_add_user = ttk.LabelFrame(self, text="Add Users From:")
        rd_btn_session_file = ttk.Radiobutton(
            lbl_frame_add_user,
            text="0: Phones.txt File",
            value=0,
            variable=self.var_add_user_from,
            command=self.enable_entry_of_session_number,
        )
        rd_btn_phones_file = ttk.Radiobutton(
            lbl_frame_add_user,
            text="1: Session files",
            value=1,
            variable=self.var_add_user_from,
            command=self.enable_entry_of_session_number,
        )

        lbl_number_of_sessions = ttk.Label(lbl_frame_add_user, text="Enter Number of Session to Process:")
        self._ent_number_of_sessions = ttk.Entry(lbl_frame_add_user)
        self._ent_number_of_sessions.insert(0, "0")

        self._ent_number_of_sessions.bind("<KeyRelease>", self._check_session_amount)

        lbl_frame_add_user.grid(row=3, column=0, sticky="we", padx=(5, 5))
        rd_btn_session_file.grid(row=4, column=0, sticky="w", padx=(10, 5))
        rd_btn_phones_file.grid(row=5, column=0, sticky="w", padx=(10, 5))

        self._ent_number_of_sessions["state"] = "disabled"
        lbl_number_of_sessions.grid(row=6, column=0, sticky="w", padx=(5, 5))
        self._ent_number_of_sessions.grid(row=7, column=0, sticky="w", padx=(10, 5))

        # ask if code required to ask
        self.var_code_required = IntVar(value=0)
        lbl_code_required = ttk.LabelFrame(self, text="Ask for code (only for phones.txt):")
        rd_btn_code_required_no = ttk.Radiobutton(
            lbl_code_required,
            text="0: Don't ask for code",
            value=0,
            variable=self.var_code_required,
        )
        rd_btn_code_required_yes = ttk.Radiobutton(
            lbl_code_required,
            text="1: Ask for code",
            value=1,
            variable=self.var_code_required,
        )

        lbl_code_required.grid(row=0, column=1, sticky="we", padx=(5, 5))
        rd_btn_code_required_no.grid(row=1, column=1, sticky="w", padx=(10, 5))
        rd_btn_code_required_yes.grid(row=2, column=1, sticky="w", padx=(10, 5))

        lbl_delay_for_user = ttk.LabelFrame(self, text="Additional Settings")
        lbl_user_delay = ttk.Label(lbl_delay_for_user, text="User Adding Delay (seconds):")
        self._spb_delay_for_adding = ttk.Spinbox(lbl_delay_for_user, from_=0, to=999, increment=0.1)
        self._spb_delay_for_adding.bind("<KeyRelease>", self._check_user_delay)

        lbl_delay_for_user.grid(row=3, column=1, sticky="we", padx=(5, 5))
        lbl_user_delay.grid(row=5, column=1, sticky="w", padx=(5, 5))
        self._spb_delay_for_adding.grid(row=6, column=1, sticky="w", padx=(10, 5))

        self.var_proxy_enabled = IntVar(value=0)
        _chb_proxy_enabled = ttk.Checkbutton(lbl_delay_for_user, text="Enable proxy", variable=self.var_proxy_enabled)
        _chb_proxy_enabled.grid(row=4, column=1, sticky="w", padx=(5, 5))

    def isfloat(self, num):
        try:
            float(num)
            return True
        except ValueError:
            return False

    def _check_user_delay(self, event):
        current_val = self._spb_delay_for_adding.get()

        if len(current_val) > 3 and self.isfloat(current_val):
            if current_val.count(".") == 1:
                integer_part = current_val.split(".")[0]
                if len(integer_part) > 3:
                    self._spb_delay_for_adding.delete(len(current_val) - 1)
                    tkmb.showerror("Maximum Timeout", "Maximum timeout is 999.99 seconds.")
            else:
                self._spb_delay_for_adding.delete(len(current_val) - 1)
                tkmb.showerror("Maximum Timeout", "Maximum timeout is 999.99 seconds.")

        if self.isfloat(current_val) and current_val.count(".") == 1:
            decimal_part = current_val.split(".")[1]
            if len(decimal_part) > 2 and decimal_part.isnumeric():
                self._spb_delay_for_adding.delete(len(current_val) - 1)
                tkmb.showerror("Maximum Timeout", "Maximum timeout is 999.99 seconds.")

        if not self.isfloat(current_val) and len(current_val) > 0 and current_val.count(".") > 1:
            self._spb_delay_for_adding.delete(len(current_val) - 1)
            tkmb.showerror("Not Numeric", "Please enter only numbers.")

    def enable_entry_of_session_number(self):
        if self.var_add_user_from.get():
            self._ent_number_of_sessions["state"] = "normal"
        else:
            self._ent_number_of_sessions["state"] = "disabled"

    def _check_session_amount(self, event):
        current_val = self._ent_number_of_sessions.get()

        if len(current_val) > 5 and current_val.isnumeric():
            self._ent_number_of_sessions.delete(len(current_val) - 1)
            tkmb.showerror(
                "Maximum Account To Add",
                "Maximum account to add is 99999. Please put value between 1 to 99999.",
            )

        if not current_val.isnumeric() and len(current_val) > 0:
            self._ent_number_of_sessions.delete(len(current_val) - 1)
            tkmb.showerror("Not Numeric", "Please enter only numbers.")

    def run(self):
        if self.var_add_user_from.get() == 0:
            phones_exists = os.path.exists(rf"{AUTO_REGISTER_PATH_DIR}\sessions\phones.txt")
            if not phones_exists:
                tkmb.showerror("No phones.txt", "No phones.txt found under sessions folder.")
                return
        else:
            sessions_exists = glob.glob(rf"{AUTO_REGISTER_PATH_DIR}\sessions\*.session*")
            if not sessions_exists:
                tkmb.showerror("No sessions found", "No session file found under sessions folder.")
                return

        adding_user_delay = self._spb_delay_for_adding.get()

        if not self.frame_thread or not self.frame_thread.is_alive():
            self.frame_thread = AddUser(
                run_mode=self.var_user_add_option.get(),
                client_mode=self.var_add_user_from.get(),
                max_session=self._ent_number_of_sessions.get(),
                code_required=self.var_code_required.get(),
                user_delay=adding_user_delay if adding_user_delay else "0",
                proxy_enabled=self.var_proxy_enabled.get(),
            )
            self.frame_thread = self.frame_thread
            self.frame_thread.start()

        else:
            self.frame_thread.resume()
