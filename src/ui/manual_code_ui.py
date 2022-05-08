import glob
import os
import tkinter.messagebox as tkmb
from tkinter import IntVar, ttk

from src.automation.retrieve_code_automation import RetrieveCode
from src.utils.paths import RETRIEVE_MANUAL_DIR

from .abstract_frame_ui import AbstractTab


class ManualTgCode(AbstractTab):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._create_first_column()
        self.parent = parent

    def _create_first_column(self):
        lbl_get_code = ttk.Label(self, text="GET MANUAL CODE", font=("arial", 20))
        lbl_get_code.grid(row=0, column=0, sticky="we", padx=(5, 5))

    def run(self):
        phones_exists = os.path.exists(rf"{RETRIEVE_MANUAL_DIR}\sessions\phones.txt")
        if not phones_exists:
            tkmb.showerror("No phones.txt", "No phones.txt found under sessions folder.")
            return

        if not self.frame_thread or not self.frame_thread.is_alive():
            self.frame_thread = RetrieveCode()
            self.frame_thread = self.frame_thread
            self.frame_thread.start()

        else:
            self.frame_thread.resume()
