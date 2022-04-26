import os
from tkinter import PhotoImage, ttk


class Header(ttk.Frame):
    def __init__(self, parent):
        ttk.Frame.__init__(self, parent)
        self._create_objects()

    def _create_objects(self):
        btn_style = ttk.Style()
        btn_style.configure("W.TButton", height=10)
        run_image = PhotoImage(file="src/icons/common/run.png")
        self.btn_run = ttk.Button(master=self, text="Run", image=run_image, compound="left", style="W.TButton")
        self.btn_run.image = run_image  # type: ignore

        pause_image = PhotoImage(file="src/icons/common/pause.png")
        self.btn_pause = ttk.Button(master=self, text="Pause", image=pause_image, compound="left")
        self.btn_pause.image = pause_image  # type: ignore
        self.btn_pause["state"] = "disabled"

        stop_image = PhotoImage(file="src/icons/common/stop.png")
        self.btn_stop = ttk.Button(master=self, text="Stop", image=stop_image, compound="left")
        self.btn_stop.image = stop_image  # type: ignore
        self.btn_stop["state"] = "disabled"

        self.btn_run.grid(row=0, column=0, sticky="w")
        self.btn_pause.grid(row=0, column=1, sticky="w")
        self.btn_stop.grid(row=0, column=2, sticky="w")

        self.lbl_current_instance = ttk.Label(self, text=f"Current Running Instance: {os.getcwd()}", wraplength=400)
        self.lbl_current_instance.grid(row=0, column=3, sticky="w", padx=((20, 20)))
