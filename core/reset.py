import os
from core.bluetoothctl import bluetoothctl_remove_devices
from core.audio_sinks import unload_audio_modules

def delete_speaker_state_file():
    if os.path.exists("speaker_state.json"):
        os.remove("speaker_state.json")

def delete_selected_devices_state_file():
    if os.path.exists("selected_devices.json"):
        os.remove("selected_devices.json")


def factory_reset():
    bluetoothctl_remove_devices()
    unload_audio_modules()
    delete_speaker_state_file()
    delete_selected_devices_state_file()


################################
######### TEST STACK ###########
################################

if __name__ == "__main__":
    factory_reset()
