import os
import subprocess
from core.bluetoothctl import bluetoothctl_remove_devices

# removes the saved speaker state file if it exists, so state doesn't carry over between runs
def delete_speaker_state_file():
    if os.path.exists("speaker_state.json"):
        os.remove("speaker_state.json")

# removes the saved selected-devices state file if it exists
def delete_selected_devices_state_file():
    if os.path.exists("selected_devices.json"):
        os.remove("selected_devices.json")

# unloads any loaded null-sink, loopback and combine-sink modules so the audio stack starts clean
def unload_audio_modules():
    commands = [
        "pactl list short modules | grep module-null-sink | awk '{print $1}' | xargs -r -n1 pactl unload-module",
        "pactl list short modules | grep module-loopback | awk '{print $1}' | awk '{print $1}' | xargs -r -n1 pactl unload-module",
        "pactl list short modules | grep module-combine-sink | awk '{print $1}' | xargs -r -n1 pactl unload-module",
    ]
    for cmd in commands:
        subprocess.run(cmd, shell=True)

# wipes all persisted bluetooth and audio state: forget devices, unload modules, clear saved selections
def factory_reset():
    bluetoothctl_remove_devices()
    unload_audio_modules()
    delete_selected_devices_state_file()