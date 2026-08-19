#!/usr/bin/env python3
import os
import subprocess
import time
from bt_connect import check_if_connected

# FUNCTION TO INTERACT WITH pactl
def pactl(args: str) -> str:
    proc = subprocess.run(
        ["pactl"] + args.split(), capture_output=True, text=True
    )
    return proc.stdout + proc.stderr

# CREATE DICTIONAIRY THAT MAPS BLUETOOTHCTL CONFIRMED CONNECTED DEVICES TO PACTL LIST SHORT SINKS
def dict_mac_to_sink():
    all_connected, connected_devices_list = check_if_connected(verbose=False) #UNPACKING TUPLE = BOOL, LIST OF [MAC]'s
    if not all_connected:
        print("Not all speakers connected yet, skipping sink creation")
    else:
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
        self.create_null_sink()
    
    def create_null_sink(self):
        self.null_sink_name = self.name + "_null_delayed"
        self.null_sink_module_id = pactl(f"load-module module-null-sink sink_name={self.null_sink_name}")

    def __repr__(self):
        return f"BluetoothSpeaker(name={self.name!r}, mac={self.mac!r}, sink_id={self.sink_id!r}, null_sink_name={self.null_sink_name}, null_sink_module_id={self.null_sink_module_id})"

# BUILD LIST OF BLUETOOTH SPEAKER OBJECTS FROM EACH CONNECTED DEVICE IN dict_mac_to_sink() dict
def build_speakers():
    bluetooth_speakers = []
    for mac, info in dict_mac_to_sink().items():
        sink_id = info["id"]
        device_name = info["name"]
        bluetooth_speakers.append(BluetoothSpeaker(mac=mac, name=device_name, sink_id=sink_id)) 
    return bluetooth_speakers

speakers = build_speakers()
print(speakers)






## IDEAS 
# apply object oriented programming
# have a parent speaker object class
# and child speaker classes

# every child is a device from connected_devices_list
# cross reference the output of the command 'pactl list short sinks' with device
# check if the device is a bluetooth device the bluez_output line (maybe change : for _ in some cases)
# 
# each child should create a null sink to act as the delayed jack input (name it device_null_delayed) 
    # pactl load-module module-nul-sink sink_name={speakername}_..etc 


#  
# implement methods for : pactl unload-module, pactl load-module, change latency

#build the combined sink of all individual null_delayed_sinks as the main output device



# FOR INSTANCE >>>


# # 1. Create a null sink to act as the delayed jack input
# pactl load-module module-null-sink sink_name=jack_delayed sink_properties=device.description="Jack_Delayed"

# # 2. Loop that null sink into the real jack output, with added latency
# pactl load-module module-loopback \
#   source=jack_delayed.monitor \
#   sink=alsa_output.platform-fe00b840.mailbox.stereo-fallback \
#   latency_msec=150

# # 3. Now build the combine sink using jack_delayed instead of the real jack sink
# pactl load-module module-combine-sink \
#   sink_name=combined_speakers \
#   slaves=bluez_output.52_58_0D_19_0A_4B.1,bluez_output.63_5E_53_8E_2B_06.1,bluez_output.04:52:C7:A9:52:B8,bluez_output.E4:58:BC:6E:EC:08,jack_delayed


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