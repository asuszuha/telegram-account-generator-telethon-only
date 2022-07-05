import glob
import os
import tkinter.messagebox as tkmb
from tkinter import IntVar, ttk

from tkcalendar import DateEntry

from src.automation.name_extractor import NameScraperFromGroup
from src.utils.paths import GROUP_CHAT_EXTRACTOR_DIR

from .abstract_frame_ui import AbstractTab


class TgNameExtractor(AbstractTab):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._create_first_column()
        self.parent = parent

    def _create_first_column(self):
        self.var_client_from = IntVar(value=0)
        lbl_frame_add_user = ttk.LabelFrame(self, text="Client From:")
        rd_btn_session_file = ttk.Radiobutton(
            lbl_frame_add_user,
            text="0: Phones.txt File",
            value=0,
            variable=self.var_client_from,
        )
        rd_btn_phones_file = ttk.Radiobutton(
            lbl_frame_add_user,
            text="1: Session files",
            value=1,
            variable=self.var_client_from,
        )

        lbl_frame_add_user.grid(row=0, column=0, sticky="nswe", padx=(5, 5))
        rd_btn_session_file.grid(row=0, column=0, sticky="w", padx=(10, 5))
        rd_btn_phones_file.grid(row=1, column=0, sticky="w", padx=(10, 5))

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
        lbl_code_required.grid(row=1, column=0, sticky="nswe", padx=(5, 5))
        rd_btn_code_required_no.grid(row=0, column=0, sticky="w", padx=(10, 5))
        rd_btn_code_required_yes.grid(row=1, column=0, sticky="w", padx=(10, 5))

        self.var_extract_names = IntVar(value=0)
        lbl_frame_extract_names = ttk.LabelFrame(self, text="Extract names:")
        rd_btn_all_names = ttk.Radiobutton(
            lbl_frame_extract_names,
            text="0: Extract all names",
            value=0,
            variable=self.var_extract_names,
            command=self.enable_entry_of_name_number,
        )
        rd_btn_number_of_names = ttk.Radiobutton(
            lbl_frame_extract_names,
            text="1: Extract number of names",
            value=1,
            variable=self.var_extract_names,
            command=self.enable_entry_of_name_number,
        )

        lbl_number_of_names = ttk.Label(lbl_frame_extract_names, text="Enter Number of Names to Extract:")
        self._ent_number_of_names = ttk.Entry(lbl_frame_extract_names)
        self._ent_number_of_names.insert(0, "0")

        self._ent_number_of_names.bind("<KeyRelease>", self._check_name_amount)
        self._ent_number_of_names["state"] = "disabled"
        lbl_frame_extract_names.grid(row=0, column=2, stick="we", padx=(5, 5))
        rd_btn_all_names.grid(row=0, column=0, sticky="w", padx=(10, 5))
        rd_btn_number_of_names.grid(row=1, column=0, sticky="w", padx=(10, 5))
        lbl_number_of_names.grid(row=2, column=0, sticky="we", padx=(5, 5))
        self._ent_number_of_names.grid(row=3, column=0, sticky="we", padx=(10, 5))

    def isfloat(self, num):
        try:
            float(num)
            return True
        except ValueError:
            return False

    def _check_name_amount(self, event):
        current_val = self._ent_number_of_names.get()

        if len(current_val) > 5 and current_val.isnumeric():
            self._ent_number_of_names.delete(len(current_val) - 1)
            tkmb.showerror(
                "Maximum Names To Scrape",
                "Maximum names to scrape is 99999. Please put value between 1 to 99999.",
            )

    def enable_entry_of_name_number(self):
        if self.var_extract_names.get():
            self._ent_number_of_names["state"] = "normal"
        else:
            self._ent_number_of_names["state"] = "disabled"

    def run(self):
        if self.var_client_from.get() == 0:
            phones_exists = os.path.exists(rf"{GROUP_CHAT_EXTRACTOR_DIR}\sessions\phones.txt")
            if not phones_exists:
                tkmb.showerror("No phones.txt", "No phones.txt found under sessions folder.")
                return
        else:
            sessions_exists = glob.glob(rf"{GROUP_CHAT_EXTRACTOR_DIR}\sessions\*.session*")
            if not sessions_exists:
                tkmb.showerror("No sessions found", "No session file found under sessions folder.")
                return

        if not self.frame_thread or not self.frame_thread.is_alive():
            self.frame_thread = NameScraperFromGroup(
                client_mode=self.var_client_from.get(),
                code_required=self.var_code_required.get(),
                max_names=self._ent_number_of_names.get(),
                name_scraping_option=self.var_extract_names.get(),
            )
            self.frame_thread = self.frame_thread
            self.frame_thread.start()

        else:
            self.frame_thread.resume()
