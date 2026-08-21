#!/usr/bin/env python3
import os
import subprocess
import time
from bt_connect_v3 import check_if_all_connected

# FUNC TO CLEANUP NULL, LOOPBACK AND COMBINE SINKS
def cleanup_modules():
    commands = [
        "pactl list short modules | grep module-null-sink | awk '{print $1}' | xargs -r -n1 pactl unload-module",
        "pactl list short modules | grep module-loopback | awk '{print $1}' | xargs -r -n1 pactl unload-module",
        "pactl list short modules | grep module-combine-sink | awk '{print $1}' | xargs -r -n1 pactl unload-module",
    ]
    for cmd in commands:
        subprocess.run(cmd, shell=True)  

# FUNCTION TO INTERACT WITH pactl
def pactl(args: str) -> str:
    proc = subprocess.run(
        ["pactl"] + args.split(), capture_output=True, text=True
    )
    return proc.stdout + proc.stderr

# CREATE DICTIONAIRY THAT MAPS BLUETOOTHCTL CONFIRMED CONNECTED DEVICES TO PACTL LIST SHORT SINKS
def dict_mac_to_sink():
    all_connected, connected_devices_list = check_if_all_connected(verbose=False) #UNPACKING TUPLE = BOOL, LIST OF [MAC]'s
    out = pactl("list short sinks")
    device_to_sink = {}
    for device in connected_devices_list:
        device_upper = device.upper()
        device_underscored = device_upper.replace(":", "_")
        for line in out.splitlines():
            line_upper = line.upper()
            if device_upper in line_upper or device_underscored in line_upper:
                fields = line.split()
                device_to_sink[device] = {"id": fields[0], "name": fields[1]}
                break
    return device_to_sink # DICTIONARY = {'MAC':{'SINK ID':'NAME'}}

# BLUETOOTH SPEAKER CLASS
class BluetoothSpeaker:
    def __init__(self, mac, name, sink_id, default_latency_ms=0):
        self.mac = mac
        self.name = name
        self.sink_id = sink_id
        self.latency_ms = default_latency_ms
        self.loopback_module_id = None
        self.null_sink_name = None
        self.null_sink_module_id = None
        self.loopback_sink_name = None
        self.loopback_sink_module_id = None
    
    def create_null_sink(self):
        self.null_sink_name = self.name + "_null_delayed"
        self.null_sink_module_id = pactl(f"load-module module-null-sink sink_name={self.null_sink_name}")

    def create_loopback(self):
        self.loopback_name = self.name + "_loopback"
        self.loopback_module_id = pactl(f"load-module module-loopback source={self.null_sink_name}.monitor sink={self.name} latency_msec={self.latency_ms}")
    
    def get_null_sink_name(self):
        return self.null_sink_name 
    

    def __repr__(self):
        return f"BluetoothSpeaker(name={self.name!r}, mac={self.mac!r}, sink_id={self.sink_id!r}, null_sink_name={self.null_sink_name}, null_sink_module_id={self.null_sink_module_id})"

# FUNC TO BUILD LIST OF BLUETOOTH SPEAKER OBJECTS FROM EACH CONNECTED DEVICE IN DICT dict_mac_to_sink()
def build_speakers():
    bluetooth_speakers = []
    for mac, info in dict_mac_to_sink().items():
        sink_id = info["id"]
        device_name = info["name"]
        bluetooth_speakers.append(BluetoothSpeaker(mac=mac, name=device_name, sink_id=sink_id)) 
    return bluetooth_speakers

# FUNC TO COMBINE ALL CONNECTED BLUETOOTH SPEAKERS INTO ONE AUDIO OUTPUT

def combine_speakers(name_combined_sink):
    # BUILD LIST OF SPEAKER OBJECTS
    speakers = build_speakers()

    # CALL CREATE_NULL_SINK METHOD ON EACH SPEAKER OBJECT, ADD SMALL DELAY
    for speaker in speakers:
        print(f"Creating null_sink for {speaker}")
        speaker.create_null_sink()
        time.sleep(0.5)

    # CALL CREATE_LOOPBACK METHOD ON EACH SPEAKER OBJECT, ADD SMALL DELAY
    for speaker in speakers:
        print(f"Creating loopback for {speaker}")
        speaker.create_loopback()
        time.sleep(0.5)

    # COMBINING ALL SPEAKERS IN ONE SINK
    print(f"Combining all speakers in one sink named {name_combined_sink}")
    null_sink_names = []
    for speaker in speakers:
        null_sink_names.append(speaker.get_null_sink_name())
    null_sink_names_str = ",".join(null_sink_names)
    pactl(f"load-module module-combine-sink sink_name={name_combined_sink} slaves={null_sink_names_str}")
    time.sleep(0.5)

    # SET COMBINED_SINK AS PACTL DEFAULT AUDIO OUTPUT
    print(f"Setting {name_combined_sink} as default pactl audio output")
    pactl(f"set-default-sink {name_combined_sink}")

    print(f"Succes!")

def check_if_combined(name_combined_sink):
    if name_combined_sink in pactl("list short sinks"):
        return True
    return False


# TO DO
# Implement latency adjustment method
# ADD FL, FR, RL, RR, CENTER to ENV.. map them to the object.. use it later to manually adjust latency

# # CHANGE DELAY 

# find module id: 
# pactl list short modules

# pactl unload-module <ID>

# pactl load-module module-loopback \
#   source=jack_delayed.monitor \
#   sink=alsa_output.platform-fe00b840.mailbox.stereo-fallback \
#   latency_msec=180

# # Initial calibration ideas

# The Bluetooth speakers have inherent latency (~100-200ms) that the jack output (For the subwoofer) doesn't, so without compensation the jack will sound ahead. module-combine-sink doesn't support per-slave delay directly, so the fix is to insert a delayed loopback in front of the jack sink instead of feeding it directly.

# >> Run python script interacting with pactl unload-module and load-module to change latency_msec ?? <<