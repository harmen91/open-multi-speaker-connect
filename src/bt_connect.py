#!/usr/bin/env python3
import os
import subprocess
import time
from load_env import env

#bluetooth hardware controller used for speakers (audio output)
CONTROLLER_OUTPUT = env["CONTROLLER_OUTPUT"]
#bluetooth hardware controller used to pair phones (audio input)
CONTROLLER_INPUT = env["CONTROLLER_INPUT"]

SPEAKERS = [
    env["DIY_SPEAKER_1"],
    env["DIY_SPEAKER_2"],
    env["BOSE_SOUNDLINK"],
    # env["BOSE_SOUNDLINK_HOME"],
]

PHONE = env["PHONE_IPHONE"]
 
# FUNCTION TO INTERACT WITH bluetoothctl
def bt(script: str) -> str:
    proc = subprocess.run(
        ["bluetoothctl"], input=script, capture_output=True, text=True
    )
    return proc.stdout + proc.stderr

def bt_off_on():
    print("Powering off bluetooth controller")
    bt("power off")
    time.sleep(1)
    print("Powering on bluetooth controller")
    bt("power on")
    time.sleep(1)
 
def setup_controller(controller: str):
    print(f"== Setting up controller {controller} ==")
    out = bt(f"select {controller}\npower on\nagent on\ndefault-agent\n")
    # print(out)
 
# REMOVE ALL DEVICES
def remove_devices():
    for mac in SPEAKERS:
        bt((f"remove {mac}\n"))

########################

## Recursively calls itself untill everything is trusted and paired
def trust_and_pair_device(mac):
    max_attempts = 10
    delay = 1

    for attempt in range(max_attempts):
        print(f"{mac} Attempt {attempt + 1}/{max_attempts}")    

        trusted = mac in bt("devices Trusted")
        if not trusted:
            print(f"{mac} Trusting..")
            bt(f"trust {mac}\n")
            time.sleep(delay)
            continue

        paired = mac in bt("devices Paired")
        if not paired:
            print(f"{mac} Pairing..")
            bt(f"pair {mac}\n")
            time.sleep(delay)
            continue
        

        return True
    
    print(f"Retrying for {mac}")
    bt_off_on()
    return trust_and_pair_device(mac)


# CALL THIS TO PAIR ALL DEVICES
def pair_all_devices():
    remove_devices()
    time.sleep(1)
    bt_off_on()

    for mac in SPEAKERS:
        trust_and_pair_device(mac)
    
    print("Sucessfully trusted & paired all devices")

def check_if_paired():
    for mac in SPEAKERS:
        paired = mac in bt("devices Paired")
        if paired:
            print(f"{mac} paired")
        else:
            print(f"{mac} unpaired")
            return False
    return True

##################################

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

# CALL THIS TO CONNECT ALL DEVICES
def connect_all_devices():

    for mac in SPEAKERS:
        bt_connect_device(mac)
        time.sleep(2)

def check_if_connected() -> (bool, list):
    list_connected = []
    for mac in SPEAKERS:
        connected = mac in bt("devices Connected")
        if connected:
            print(f"{mac} connected")
            list_connected.append(mac)
        else:
            print(f"{mac} disconnected")
            return False, list_connected
            
    return True, list_connected