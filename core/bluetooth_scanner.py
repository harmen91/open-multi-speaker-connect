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

# discovers nearby bluetooth devices by watching the shared scan queue
class BluetoothScanner:
    # matches standard mac address format: six hex pairs separated by colons
    MAC_PATTERN = re.compile(
    r"(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}"
    )

    def __init__(self, scan_queue):
        self.scan_queue = scan_queue
        self.devices = {}          # macs discovered during the last scan -> advertised name
        self.known_devices = {}    # macs already known to bluetoothctl (paired devices) -> stored name
        self.selected_devices = set()  # macs toggled for saving
        self.save_devices = {}     # subset of devices to write to selected_devices.json

    # runs a fresh power cycle + background scan for --timeout seconds,
    # then collects [NEW]/[CHG] device lines from the scan queue into self.devices
    def scan(self, timeout=10):
        self.devices.clear()
        self.selected_devices.clear()
        self.save_devices.clear()
        self.load_known_devices()

        # drain any stale entries from previous scans so only fresh lines are read
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

            # ignore lines that don't contain a mac address
            match = self.MAC_PATTERN.search(line)

            if not match:
                continue

            mac = match.group().upper()
            parts = line.split(maxsplit=3)

            # [NEW] lines carry the advertised name; fall back to "(unknown)" if absent
            if "[NEW] Device" in line:
                name = parts[3] if len(parts) > 3 else "(unknown)"
                self.devices[mac] = name

            # [CHG] lines update names for devices already known to bluetoothctl
            elif "[CHG] Device" in line and mac in self.known_devices:
                self.devices[mac] = self.known_devices[mac]

        return self.devices.copy()

    # fetches all devices currently known to bluetoothctl (via `devices`),
    # so their stored names survive advertising glitches during the scan
    def load_known_devices(self):
        self.known_devices.clear()
        time.sleep(1)

        output = bluetoothctl_run("devices").stdout

        for line in output.splitlines():
            parts = line.split(maxsplit=2)

            # only process lines shaped like "Device <MAC> <Name>"
            if len(parts) < 3 or parts[0] != "Device":
                continue

            self.known_devices[parts[1].upper()] = parts[2]

    # toggles device selection state. Returns True if now selected, False otherwise.
    # no-op for macs that weren't discovered in the last scan
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

    # writes the selected devices to json and refreshes the loaded session state:
    # replaces any existing selection file, reloads OUTPUT_DEVICES, then powers
    # bluetooth off to end the scan cleanly
    def save_devices_to_json(self, filepath="selected_devices.json"):
        if os.path.exists("selected_devices.json"):
            os.remove("selected_devices.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.save_devices, f, indent=4)
        
        # refresh the in-memory device list so the rest of the app sees the new selection
        load_env.OUTPUT_DEVICES = load_env.get_output_devices()
        bluetoothctl_scan_stop()
        bluetoothctl_run("power off")
        time.sleep(1)
        
