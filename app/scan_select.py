from core.bluetoothctl import bluetoothctl_scan_start, scan_queue, bluetoothctl_run
import queue
import time
import re

## BUILDS A LIST OF NEWLY DISCOVERED DEVICES 
def scan_to_list():

    pattern = r"\b(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b"
    new_devices_list = []
    local_scan_lines = []


    while True:
        try:
            local_scan_lines.append(scan_queue.get_nowait())
        except queue.Empty:
            break


    bluetoothctl_run("power off")
    bluetoothctl_run("power on")
    bluetoothctl_scan_start()

 
    while True:
        try:
            line = scan_queue.get(timeout=1)
            if re.search(pattern, line): 
                found_mac = re.findall(pattern, line)
                if found_mac not in    new_devices_list:
                    if "[NEW] Device" in line: #only append "[NEW] Device AA:BB:CC:DD"
                        device_mac = line.split(maxsplit=3)[2]
                        device_name = line.split(maxsplit=3)[3]
                        new_devices_list.append((
                            device_mac,
                            device_name
                            ))
            time.sleep(1)
            print(f"TESSTTT>>>>>>      {new_devices_list}")
        except queue.Empty:
            print(f"Waiting for more devices to appear..") #waiting for new entry in queue to appear
        
    