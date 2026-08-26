from bt_connect import bt_remove_devices
from audio_sinks import cleanup_modules

def factory_reset():
    bt_remove_devices()
    cleanup_modules()

################################
######### TEST STACK ###########
################################

if __name__ == "__main__":
    factory_reset()
    cleanup_modules()
