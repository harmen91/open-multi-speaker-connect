import subprocess
import time
from core.bluetoothctl import all_connected
from core.speaker import BluetoothSpeaker
from core.pactl import pactl

# create dictionary that maps bluetoothctl confirmed connected devices to pactl list short sinks
def map_mac_to_sink():
    is_connected, connected_devices_list = all_connected(verbose=False) # unpacking tuple = bool, list of [mac]'s
    out = pactl("list short sinks")
    device_to_sink = {}
    for device in connected_devices_list:
        device_upper = device.upper()
        device_underscored = device_upper.replace(":", "_")
        for line in out.splitlines():
            fields = line.split()
            # Skip lingering null-delayed sinks — they outlive disconnects and must never be mapped as a speaker's real sink
            if len(fields) < 2 or fields[1].endswith("_null_delayed"):
                continue
            line_upper = line.upper()
            if device_upper in line_upper or device_underscored in line_upper:
                # fields = line.split()
                device_to_sink[device] = {"id": fields[0], "name": fields[1]}
                break
    return device_to_sink # dictionary = {'mac': {'sink id': 'name'}}

# func to build list of bluetooth speaker objects from each connected device in dict map_mac_to_sink()
def build_speaker_list():
    bluetooth_speakers = []
    for mac, info in map_mac_to_sink().items():
        sink_id = info["id"]
        device_name = info["name"]
        bluetooth_speakers.append(BluetoothSpeaker(mac=mac, name=device_name, sink_id=sink_id)) 
    return bluetooth_speakers

# func to combine all connected bluetooth speakers into one audio output

def combine_speakers(name_combined_sink):
    # build list of speaker objects
    speakers = build_speaker_list()

    # call create_null_sink method on each speaker object, add small delay
    for speaker in speakers:
        print(f"Creating null_sink for {speaker}")
        speaker.create_null_sink()
        time.sleep(0.5)

    # call create_loopback method on each speaker object, add small delay
    for speaker in speakers:
        print(f"Creating loopback for {speaker}")
        speaker.create_loopback()
        time.sleep(0.5)

    # combining all speakers in one sink
    print(f"Combining all speakers in one sink named {name_combined_sink}")
    null_sink_names = []
    for speaker in speakers:
        null_sink_names.append(speaker.get_null_sink_name())
    null_sink_names_str = ",".join(null_sink_names)
    pactl(f"load-module module-combine-sink sink_name={name_combined_sink} slaves={null_sink_names_str}")
    time.sleep(0.5)

    # set combined_sink as pactl default audio output
    print(f"Setting {name_combined_sink} as default pactl audio output")
    pactl(f"set-default-sink {name_combined_sink}")

    print(f"Succes!")
    return speakers

# this function parses `pactl list modules` into {module_id: {"name": ..., "argument": ...}} so callers can verify a persisted id is still real
def get_live_modules():
    out = pactl("list modules")
    modules = {}
    current_id = current_name = None
    current_arg = ""
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("Module #"):
            if current_id is not None:
                modules[current_id] = {"name": current_name, "argument": current_arg}
            current_id = s.split("#", 1)[1].strip()
            current_name, current_arg = None, ""
        elif s.startswith("Name:"):
            current_name = s.split(":", 1)[1].strip()
        elif s.startswith("Argument:"):
            current_arg = s.split(":", 1)[1].strip()
    if current_id is not None:
        modules[current_id] = {"name": current_name, "argument": current_arg}
    return modules


### needs work: this should actually double-check with connected bluetooth devices, not just the short sink name of the combined sink
### todo
## if not combined, but connected > should remove sink and all corresponding nullsinks and try again
### work in progress ####
def is_combined_sink_active(name_combined_sink):
    out = pactl("list short sinks")
    # Check each line's second column (the sink name)
    for line in out.splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[1] == name_combined_sink:
            return True
    return False










# add FL, FR, RL, RR, center to env.. map them to the object.. use later to manually adjust latency

# # change delay

# find module id:
# pactl list short modules

# pactl unload-module <ID>

# pactl load-module module-loopback \
#   source=jack_delayed.monitor \
#   sink=alsa_output.platform-fe00b840.mailbox.stereo-fallback \
#   latency_msec=180

# # initial calibration ideas

# The Bluetooth speakers have inherent latency (~100-200ms) that the jack output (For the subwoofer) doesn't, so without compensation the jack will sound ahead. module-combine-sink doesn't support per-slave delay directly, so the fix is to insert a delayed loopback in front of the jack sink instead of feeding it directly.

# >> idea: run a python script that interacts with pactl unload-module and load-module to change latency_msec ??