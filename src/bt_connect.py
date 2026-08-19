#!/usr/bin/env python3
import os
import subprocess
import time
from load_env import env

# BLUETOOTH HARDWARE MAC FOR AUDIO OUTPUT (SPEAKER DEVICES)
CONTROLLER_OUTPUT = env["CONTROLLER_OUTPUT"]
# BLUETOOTH HARDWARE MAC FOR AUDIO INPUT (PHONE, COMPUTER, AUDIO STREAM, ETC)
# USEFULL FOR HAVING TWO SEPERATE BLUETOOTH CONTROLERS HANDLE INCOMING AND OUTGOING 
# BLUETOOTH STREAMS FOR IMPROVED PERFORMANCE AND REDUCED LATENCY
CONTROLLER_INPUT = env["CONTROLLER_INPUT"]

# STORED MAC ADDRESSES OF OUTPUT DEVICES IN ENV
OUTPUT_DEVICES = [v for k, v in env.items() if k.startswith("OUTPUT_DEVICE")] 

# STORED MAC ADDRESSES OF INPUT DEVICES IN ENV
INPUT_DEVICES = [v for k, v in env.items() if k.startswith("INPUT_DEVICE")] 


# FUNCTION TO INTERACT WITH bluetoothctl
def bt(script: str) -> str:
    proc = subprocess.run(
        ["bluetoothctl"], input=script, capture_output=True, text=True
    )
    return proc.stdout + proc.stderr

def setup_controller(controller: str):
    print(f"== Setting up bluetooth controller {controller} ==")
    out = bt(f"select {controller}\npower on\nagent on\ndefault-agent\npairable on")
    # print(out)
    time.sleep(1)
    return out

# RUNNING SCAN PROCESS IN THE BACKGROUND FOR 60 SECONDS, PROCESS NEEDS TO STAY OPEN FOR SCANNING TO BE ALIVE
scan_process = None
def bt_scan_on():
    global scan_process
    print("Starting background scan...")
    scan_process = subprocess.Popen(
        ["bluetoothctl", "--timeout", "60", "scan", "on"],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True
    )
    time.sleep(1)

# STOPS LAST INSTANCE OF BT_SCAN_ON // DOES NOT ALWAYS 100% WORK
def bt_scan_stop():
    global scan_process
    if scan_process and scan_process.poll() is None:  # still running
        scan_process.terminate()
        scan_process.wait()
        print("Scan stopped.")
    scan_process = None
    time.sleep(1)

# KILLS ALL LINGERING BACKGROUND PROCESSES OF BT_SCAN_ON()
def bt_scan_stop_all():
    subprocess.run(["pkill", "-f", "bluetoothctl --timeout"])
    print("Terminated any lingering bluetoothctl scan processes")

# RESTARTS THE BLUETOOTH HARDWARE BY POWERING IT OFF AND ON
def bt_off_on():
    print("Powering off bluetooth controller")
    bt("power off")
    time.sleep(1)
    print("Powering on bluetooth controller")
    bt("power on")
    time.sleep(1)

# UNUSED, PAIRABLE IS SET IN setup_controller()
def bt_pairable_on():
    print("Toggling bluetooth pairable mode on")
    bt("pairable on")
    time.sleep(1)

# UNUSED, MAYBE USEFULL FOR BLUETOOTH-IN FUNCTIONALITY LATER
def bt_discoverable_on():
    print("Toggling bluetooth discoverable mode on")
    bt("discoverable on")
    time.sleep(1)
 
# REMOVE ALL TRUSTED, PAIRED and CONNECTED BLUETOOTH DEVICES
def remove_devices():
    for mac in OUTPUT_DEVICES:
        bt((f"remove {mac}\n"))

########################

## RECURSIVELY CALLS ITSELF UNTILL THE DEVICE IS TRUSTED AND PAIRED, INFINITE LOOP!!
## WILL NEVER STOP IF THE BLUETOOTH HARDWARE IS OFF OR OUT OF REACH
## NEEDS IMPROVEMENT ERROR HANDLING, MAX RECURSION DEPTH ETC
## ALSO TURNS BLUETOOTH POWER AND BLUETOOTH SCAN ON AND OFF DURING EVERY ATTEMPT
def trust_and_pair_device(mac):
    max_attempts = 25
    delay = 0.5
    bt_scan_on()

    for attempt in range(max_attempts):
        print(f"{mac} Attempting to pair..{attempt + 1}/{max_attempts}")    

        trusted = mac in bt("devices Trusted")
        paired = mac in bt("devices Paired")
        if not trusted and not paired:
            # print(f"{mac} Trusting..")
            bt(f"trust {mac}\n")
            time.sleep(delay)
            # print(f"{mac} Pairing..")
            bt(f"pair {mac}\n")
            time.sleep(delay)
            continue
        
        return True
    
    print(f"Retrying for {mac}")
    bt_scan_stop()
    bt_off_on()
    return trust_and_pair_device(mac)


# CALL THIS TO PAIR ALL OUTPUT_DEVICES FROM ENV
def pair_all_devices():
    remove_devices()
    time.sleep(1)

    for mac in OUTPUT_DEVICES:
        trust_and_pair_device(mac)
    
    print("Sucessfully trusted & paired all devices")

# CHECK IF ALL OUTPUT_DEVICES IN ENV ARE ACTUALLY PAIRED IN BLUETOOTHCTL
def check_if_paired(verbose = True):
    for mac in OUTPUT_DEVICES:
        paired = mac in bt("devices Paired")
        if paired:
            if verbose:
                print(f"{mac} paired")
        else:
            if verbose:
                print(f"{mac} unpaired")
            return False
    return True

# CONNECT BLUETOOTH DEVICE, NO RECURSION HERE WE ARE ALREADY TRUSTED AND PAIRED, NO SCANNING NECESSARY EITHER
def bt_connect_device(mac):
    
    max_attempts = 20
    delay = 1

    for attempt in range(max_attempts):
        print(f"{mac} Connecting.. attempt {attempt + 1}/{max_attempts}")

        connected = mac in bt("devices Connected")
        if not connected:
            bt(f"connect {mac}\n")
            time.sleep(delay)
            continue

        return True
    print(f"{mac} Failed to connect")
    return False

# CALL THIS TO CONNECT ALL OUTPUT_DEVICES FROM ENV
def connect_all_devices():

    for mac in OUTPUT_DEVICES:
        bt_connect_device(mac)
        time.sleep(2)
    
    print("Succesfully connected all devices")

# CHECK IF ALL OUTPUT_DEVICES IN ENV ARE ACTUALLY CONNECTED IN BLUETOOTHTCL
# RETURN A BOOL AND LIST
# LIST USEFULL FOR USE IN AUDIO_SINKS.PY TO CROSS REFERENCE CONNECTED BLUETOOTH WITH PIPEWIRE

def check_if_connected(verbose = True) -> (bool, list):
    list_connected = []
    for mac in OUTPUT_DEVICES:
        connected = mac in bt("devices Connected")
        if connected:
            if verbose:
                print(f"{mac} connected")
            list_connected.append(mac)
        else:
            return False, list_connected
            

    return True, list_connected