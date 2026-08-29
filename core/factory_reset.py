import os
from core.bt_connect import bluetoothctl_remove_devices
from core.audio_sinks import unload_audio_modules

def delete_speaker_state_file():
    if os.path.exists("speaker_state.json"):
        os.remove("speaker_state.json")

def factory_reset():
    bluetoothctl_remove_devices()
    unload_audio_modules()
    delete_speaker_state_file()


################################
######### TEST STACK ###########
################################

if __name__ == "__main__":
    factory_reset()
