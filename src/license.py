import ctypes
import datetime
import winreg
from tkinter import messagebox as tkmb

REG_PATH = r"SOFTWARE\WinTgCb\Settings"
KEY = "vQ5Lg2j6u4poMnK3jVkY97LUy3HHdDVt3orlgBWjWoo="


def set_license(name, value):
    try:
        winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_WRITE)
        winreg.SetValueEx(registry_key, name, 0, winreg.REG_SZ, value)
        winreg.CloseKey(registry_key)
        return True
    except WindowsError:
        return False


def get_license(name):
    try:
        registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ)
        value, regtype = winreg.QueryValueEx(registry_key, name)
        winreg.CloseKey(registry_key)
        return value
    except WindowsError:
        return 0


def check_license_validity(root, install_date, license_type, validity):
    while True:
        if install_date != False:
            date_format = "%Y-%m-%d %H:%M:%S"
            From = datetime.datetime.strptime(str(install_date), date_format)
            To = datetime.datetime.strptime(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), date_format)
            MinutesUsed = (To - From).total_seconds() / 60
            DaysUsed = (MinutesUsed / 60) / 24
            if int(license_type) == 1:
                if int(MinutesUsed) >= int(validity):
                    tkmb.showerror("License expired", "License expired. Please activate new license")
                    exit()
            elif int(license_type) == 2:
                if int(DaysUsed) >= int(validity):
                    tkmb.showerror("License expired", "License expired. Please activate new license")
                    exit()

        root.after(5000, check_license_validity)


def generate_license(input, output, len):
    t1 = 0
    t2 = 0
    t3 = 0
    t4 = 0
    vartemp = 0
    data1 = (ctypes.c_ubyte * 512)()
    data2 = (ctypes.c_ubyte * 512)()

    licenseGen = bytearray(b"passy")
    input = bytearray(input, "utf-8")
    Length = 5

    t1 = 0
    t2 = 0
    while t1 <= 255:
        data1[t1] = t1
        data2[t1] = licenseGen[t2]
        t2 += 1
        t2 = t2 % Length
        t1 += 1

    t1 = 0
    t2 = 0
    while t1 <= 255:
        t2 = t2 + data1[t1] + data2[t1]
        t2 = t2 % 256
        vartemp = data1[t1]
        data1[t1] = data1[t2]
        data1[t2] = vartemp
        t1 += 1

    t1 = 0
    t2 = 0
    t4 = 0
    while t4 < len:
        t1 = t1 + 1
        t1 = t1 % 256
        t2 = t2 + data1[t1]
        t2 = t2 % 256

        vartemp = data1[t1]
        data1[t1] = data1[t2]
        data1[t2] = vartemp

        t3 = data1[t1] + (data1[t2] % 256)
        t3 = t3 % 256
        output[t4] = input[t4] ^ data1[t3]
        t4 += 1


def get_code_from_name(Name):
    idx = 0
    code = ""
    temp = ""
    output = (ctypes.c_ubyte * 512)()

    Length = len(Name)
    generate_license(Name, output, Length)

    code = ""
    idx = 0
    while idx < Length:
        temp = f"{output[idx]:02X}"
        code += temp
        idx += 1
    return code
