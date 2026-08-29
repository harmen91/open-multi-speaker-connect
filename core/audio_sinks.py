#!/usr/bin/env python3
import subprocess
import time
from core.bluetoothctl import all_connected
from core.speaker import BluetoothSpeaker
from core.pactl import pactl

# FUNC TO CLEANUP NULL, LOOPBACK AND COMBINE SINKS
def unload_audio_modules():
    commands = [
        "pactl list short modules | grep module-null-sink | awk '{print $1}' | xargs -r -n1 pactl unload-module",
        "pactl list short modules | grep module-loopback | awk '{print $1}' | xargs -r -n1 pactl unload-module",
        "pactl list short modules | grep module-combine-sink | awk '{print $1}' | xargs -r -n1 pactl unload-module",
    ]
    for cmd in commands:
        subprocess.run(cmd, shell=True)  

# CREATE DICTIONAIRY THAT MAPS BLUETOOTHCTL CONFIRMED CONNECTED DEVICES TO PACTL LIST SHORT SINKS
def map_mac_to_sink():
    is_connected, connected_devices_list = all_connected(verbose=False) #UNPACKING TUPLE = BOOL, LIST OF [MAC]'s
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

# FUNC TO BUILD LIST OF BLUETOOTH SPEAKER OBJECTS FROM EACH CONNECTED DEVICE IN DICT map_mac_to_sink()
def build_speaker_list():
    bluetooth_speakers = []
    for mac, info in map_mac_to_sink().items():
        sink_id = info["id"]
        device_name = info["name"]
        bluetooth_speakers.append(BluetoothSpeaker(mac=mac, name=device_name, sink_id=sink_id)) 
    return bluetooth_speakers

# FUNC TO COMBINE ALL CONNECTED BLUETOOTH SPEAKERS INTO ONE AUDIO OUTPUT

def combine_speakers(name_combined_sink):
    # BUILD LIST OF SPEAKER OBJECTS
    speakers = build_speaker_list()

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
    return speakers


### FIX THIS TO ACTUALLY DOUBLE CHECK WITH CONNECTED BLUETOOTH DEVICES, NOT JUST SHORT SINK NAME OF COMBINED SINK
### >>> !! <<< 
## IF NOT COMBINED, BUT CONNECTED > SHOULD REMOVE SINK AND ALL CORRESPONDING NULLSINKS AND TRY AGAIN
### WORK IN PROGRESS ####
def is_combined_sink_active(name_combined_sink):
    out = pactl("list short sinks")
    # Check each line's second column (the sink name)
    for line in out.splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[1] == name_combined_sink:
            return True
    return False









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