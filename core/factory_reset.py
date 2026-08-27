import os
from core.bt_connect import bt_remove_devices
from core.audio_sinks import cleanup_modules

def delete_speaker_state_file():
    if os.path.exists("speaker_state.json"):
        os.remove("speaker_state.json")


def factory_reset():
    bt_remove_devices()
    cleanup_modules()
    delete_speaker_state_file()


################################
######### TEST STACK ###########
################################

if __name__ == "__main__":
    factory_reset()
