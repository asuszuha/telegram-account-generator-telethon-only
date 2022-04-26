import subprocess


class ADBHelper:
    def get_devices(self):
        decoded_output = subprocess.run("adb devices", capture_output=True).stdout.decode("Utf-8")
        list_of_devices = [elem for elem in decoded_output.split("\r\n") if "\tdevice" in elem]
        devices = [elem.split("\t")[0] for elem in list_of_devices]
        return devices

    def get_emulator_name(self, emulator_udid: str):
        process_getprop = subprocess.run(f"adb -s {emulator_udid} shell getprop", capture_output=True)
        decoded_output = subprocess.run(
            ["findstr", "/c:[ro.kernel.qemu.avd_name]"], input=process_getprop.stdout, capture_output=True
        ).stdout.decode("utf-8")

        return decoded_output.split(":")[1].strip().replace("[", "").replace("]", "")

    def clear_app_history(self, device_name: str, package_name: str) -> bool:
        decoded_message = subprocess.run(
            f"adb -s {device_name} shell pm clear {package_name}", capture_output=True
        ).stdout.decode("utf-8")
        if "success" in decoded_message.lower():
            return True
        else:
            return False

    # def set_proxy_to_device()
