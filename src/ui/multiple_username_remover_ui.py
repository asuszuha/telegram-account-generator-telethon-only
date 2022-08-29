from tkinter import ttk

from src.automation.multiple_user_remover import MultipleUserRemover
from src.utils.paths import MULTIPLE_USERNAME_REMOVER_DIR

from .abstract_frame_ui import AbstractTab


class MultiUsernameRemoveTg(AbstractTab):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._create_first_column()
        self.parent = parent

    def _create_first_column(self):
        lbl_header = ttk.Label(self, text="Multiple Username Remover", font=("arial", 20))
        lbl_content = ttk.Label(
            self,
            text=(
                f"Fill username.txt under {MULTIPLE_USERNAME_REMOVER_DIR} folder.\nThen run the code."
                "It will remove all duplicates."
            ),
        )
        lbl_header.grid(row=0, column=0, sticky="we", padx=(5, 5))
        lbl_content.grid(row=1, column=0, sticky="we", padx=(5, 5))

    def run(self):
        if not self.frame_thread or not self.frame_thread.is_alive():
            self.frame_thread = MultipleUserRemover()
            self.frame_thread = self.frame_thread
            self.frame_thread.start()

        else:
            self.frame_thread.resume()
