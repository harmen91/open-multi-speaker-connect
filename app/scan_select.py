from core.bluetoothctl import bluetoothctl_scan_start, scan_queue, bluetoothctl_run
import queue
import time
import re

def scan_to_list():


    pattern = r"\b(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b"
    lines_with_macs = []
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
                if found_mac not in lines_with_macs:
                    if "[NEW] Device" in line: #only append "[NEW] Device AA:BB:CC:DD"
                        device_mac = line.split(maxsplit=3)[2]
                        device_name = line.split(maxsplit=3)[3]
                        lines_with_macs.append((
                            device_mac,
                            device_name
                            ))
            time.sleep(1)
            print(f"TESSTTT>>>>>>{lines_with_macs}")
        except queue.Empty:
            print(f"Waiting for more devices to appear..") #waiting for new entry in queue to appear
        
    