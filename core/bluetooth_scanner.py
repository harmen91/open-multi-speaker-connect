import json
import queue
import re
import time
import os

from core.bluetoothctl import (
    bluetoothctl_run,
    bluetoothctl_scan_start,
    scan_queue,
    bluetoothctl_scan_stop
)

from core import load_env

class BluetoothScanner:
    MAC_PATTERN = re.compile(
    r"(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}"
    )

    def __init__(self, scan_queue):
        self.scan_queue = scan_queue
        self.devices = {}
        self.known_devices = {}
        self.selected_devices = set()
        self.save_devices = {}

    def scan(self, timeout=10):
        self.devices.clear()
        self.selected_devices.clear()
        self.save_devices.clear()

        self.load_known_devices()

        while True:
            try:
                self.scan_queue.get_nowait()
            except queue.Empty:
                break

        # Keep this exact sequence together.
        bluetoothctl_run("power off")
        bluetoothctl_run("power on")
        bluetoothctl_scan_start()

        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            try:
                line = self.scan_queue.get(timeout=1)
            except queue.Empty:
                continue

            match = self.MAC_PATTERN.search(line)

            if not match:
                continue

            mac = match.group().upper()
            parts = line.split(maxsplit=3)

            if "[NEW] Device" in line:
                name = parts[3] if len(parts) > 3 else "(unknown)"
                self.devices[mac] = name

            elif "[CHG] Device" in line and mac in self.known_devices:
                self.devices[mac] = self.known_devices[mac]

        return self.devices.copy()

    def load_known_devices(self):
        self.known_devices.clear()
        time.sleep(1)

        output = bluetoothctl_run("devices").stdout

        for line in output.splitlines():
            parts = line.split(maxsplit=2)

            if len(parts) < 3 or parts[0] != "Device":
                continue

            self.known_devices[parts[1].upper()] = parts[2]

    def toggle_device(self, mac):
        """Toggles device selection state. Returns True if now selected, False otherwise."""
        if mac not in self.devices:
            return False

        if mac in self.selected_devices:
            self.selected_devices.remove(mac)
            self.save_devices.pop(mac, None)
            return False
        else:
            self.selected_devices.add(mac)
            self.save_devices[mac] = self.devices[mac]
            return True

    def save_devices_to_json(self, filepath="selected_devices.json"):
        if os.path.exists("selected_devices.json"):
            os.remove("selected_devices.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.save_devices, f, indent=4)
        
        load_env.OUTPUT_DEVICES = load_env.get_output_devices()
        bluetoothctl_scan_stop()
        bluetoothctl_run("power off")
        time.sleep(1)
        

if __name__ == "__main__":
    scanner = BluetoothScanner(scan_queue)

    print("Starting scan...")
    devices = scanner.scan(timeout=30)

    print("\nDiscovered devices:")
    for mac, name in devices.items():
        print(f"{name} - {mac}")

    if devices:
        first_mac = next(iter(devices))
        scanner.select_device(first_mac)

    print("\nSelected devices:")
    scanner.save_devices_to_json()