import abc
from tkinter import ttk


class AbstractFrame(ttk.Frame, abc.ABC):
    def __init__(self, parent):
        ttk.Frame.__init__(self, parent)
        self.frame_thread = None

    def pause(self):
        if self.frame_thread and self.frame_thread.is_alive():
            self.frame_thread.pause()

    def stop(self):
        if self.frame_thread and self.frame_thread.is_alive():
            self.frame_thread.stop()

    @abc.abstractmethod
    def run(self):
        ...
