import os
import subprocess
from core.bluetoothctl import bluetoothctl_remove_devices

def delete_speaker_state_file():
    if os.path.exists("speaker_state.json"):
        os.remove("speaker_state.json")

def delete_selected_devices_state_file():
    if os.path.exists("selected_devices.json"):
        os.remove("selected_devices.json")

def unload_audio_modules():
    commands = [
        "pactl list short modules | grep module-null-sink | awk '{print $1}' | xargs -r -n1 pactl unload-module",
        "pactl list short modules | grep module-loopback | awk '{print $1}' | xargs -r -n1 pactl unload-module",
        "pactl list short modules | grep module-combine-sink | awk '{print $1}' | xargs -r -n1 pactl unload-module",
    ]
    for cmd in commands:
        subprocess.run(cmd, shell=True)

def factory_reset():
    bluetoothctl_remove_devices()
    unload_audio_modules()
    delete_selected_devices_state_file()

