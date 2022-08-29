import glob
import os
import tkinter.messagebox as tkmb
from tkinter import ttk

from src.automation.extract_number_from_session import ExtractNumberFromSessions
from src.utils.paths import NUMBER_EXTRACT_FROM_SESSIONS_DIR

from .abstract_frame_ui import AbstractTab


class ExtracNumTgSession(AbstractTab):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._create_first_column()
        self.parent = parent

    def _create_first_column(self):
        lbl_get_code = ttk.Label(self, text="Extract Numbers From Sessions", font=("arial", 20))
        lbl_get_code2 = ttk.Label(
            self,
            text=(
                "Fill sessions under session folder.And fill api.txt with apis. "
                "\nThen code should extract numbers with only good sessions."
            ),
        )
        lbl_get_code.grid(row=0, column=0, sticky="we", padx=(5, 5))
        lbl_get_code2.grid(row=1, column=0, sticky="we", padx=(5, 5))

    def run(self):
        phones_exists = os.path.exists(rf"{NUMBER_EXTRACT_FROM_SESSIONS_DIR}\sessions\phones.txt")
        if not phones_exists:
            tkmb.showerror("No phones.txt", "No phones.txt found under sessions folder.")
            return
        sessions_exists = glob.glob(rf"{NUMBER_EXTRACT_FROM_SESSIONS_DIR}\sessions\*.session")
        if not sessions_exists:
            tkmb.showerror("No sessions found", "No session file found under sessions folder.")
            return

        if not self.frame_thread or not self.frame_thread.is_alive():
            self.frame_thread = ExtractNumberFromSessions()
            self.frame_thread = self.frame_thread
            self.frame_thread.start()

        else:
            self.frame_thread.resume()
