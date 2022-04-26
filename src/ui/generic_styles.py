from tkinter import ttk


def set_cbox_attributes(cbox: ttk.Combobox):
    cbox.current(0)
    cbox.bind("<<ComboboxSelected>>", lambda e: cbox.selection_clear())
    cbox["style"] = "BW.TCombobox"
