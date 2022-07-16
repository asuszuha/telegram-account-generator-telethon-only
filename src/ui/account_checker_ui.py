import glob
import os
import tkinter.messagebox as tkmb
from tkinter import IntVar, ttk

# from src.automation.group_chat_extractor import GroupChatScraper
from src.utils.paths import ACCOUNT_CHECKER_DIR

from .abstract_frame_ui import AbstractTab


class TgAccountChecker(AbstractTab):
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

    def run(self):
        if self.var_client_from.get() == 0:
            phones_exists = os.path.exists(rf"{ACCOUNT_CHECKER_DIR}\sessions\phones.txt")
            if not phones_exists:
                tkmb.showerror("No phones.txt", "No phones.txt found under sessions folder.")
                return
        else:
            sessions_exists = glob.glob(rf"{ACCOUNT_CHECKER_DIR}\sessions\*.session*")
            if not sessions_exists:
                tkmb.showerror("No sessions found", "No session file found under sessions folder.")
                return

        # if not self.frame_thread or not self.frame_thread.is_alive():
        #     self.frame_thread = GroupChatScraper(
        #         client_mode=self.var_client_from.get(),
        #         code_required=self.var_code_required.get(),
        #         # proxy_enabled=self.var_proxy_enabled.get(),
        #         # threading_option=self.var_multi_thread.get(),
        #         # user_scrape_option=self.var_recent_users.get(),
        #         message_scrape_option=self.var_scrape_msg_option.get(),
        #         start_date_user_filter=self.cal_start.get_date(),
        #         end_date_user_filter=self.cal_end.get_date(),
        #     )
        #     self.frame_thread = self.frame_thread
        #     self.frame_thread.start()

        # else:
        #     self.frame_thread.resume()
