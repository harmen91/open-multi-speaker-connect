import os
from core.bt_connect import bt_remove_devices
from core.audio_sinks import cleanup_modules

def factory_reset():
    bt_remove_devices()
    cleanup_modules()
    if os.path.exists("speaker_state.json"):
        os.remove("speaker_state.json")

################################
######### TEST STACK ###########
################################

if __name__ == "__main__":
    factory_reset()
