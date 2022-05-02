import glob
import os
import tkinter.messagebox as tkmb
from tkinter import IntVar, ttk

from src.automation.add_user_automation import AddUser

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

        lbl_frame.grid(row=0, column=0, sticky="w", padx=(5, 5))
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

        lbl_frame_add_user.grid(row=3, column=0, sticky="w", padx=(5, 5))
        rd_btn_session_file.grid(row=4, column=0, sticky="w", padx=(10, 5))
        rd_btn_phones_file.grid(row=5, column=0, sticky="w", padx=(10, 5))

        self._ent_number_of_sessions["state"] = "disabled"
        lbl_number_of_sessions.grid(row=6, column=0, sticky="w", padx=(5, 5))
        self._ent_number_of_sessions.grid(row=7, column=0, sticky="w", padx=(10, 5))

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
            phones_exists = os.path.exists(r"sessions\phones.txt")
            if not phones_exists:
                tkmb.showerror("No phones.txt", "No phones.txt found under sessions folder.")
                return
        else:
            sessions_exists = glob.glob(r"sessions\*.session*")
            if not sessions_exists:
                tkmb.showerror("No sessions found", "No session file found under sessions folder.")
                return

        if not self.frame_thread or not self.frame_thread.is_alive():
            self.frame_thread = AddUser(
                run_mode=self.var_user_add_option.get(),
                client_mode=self.var_add_user_from.get(),
                max_session=self._ent_number_of_sessions.get(),
            )
            self.frame_thread = self.frame_thread
            self.frame_thread.start()

        else:
            self.frame_thread.resume()
