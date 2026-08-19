import time
from bt_connect import CONTROLLER_OUTPUT
from bt_connect import setup_controller, pair_all_devices, connect_all_devices, check_if_connected, check_if_paired, remove_devices, bt_scan_stop_all
from audio_sinks import combine_speakers, cleanup_modules

def main():

    cleanup_modules()
    remove_devices() # TEST CODE TO REMOVE DEVICES, not necessary here in final, it also lives in pair_all_device()
    time.sleep(2)


    # # INITIAL BLUETOOTH CONTROLLER SETUP
    setup_controller(CONTROLLER_OUTPUT)

    # CHECK IF OUTPUT_DEVICES ARE TRUSTED AND PAIRED
    if not check_if_paired(verbose=False):
        pair_all_devices()

    # CHECK IF OUT_PUT_DEVICES ARE CONNECTED
    if not check_if_connected(verbose=False)[0]:
        connect_all_devices()
        # bt_scan_stop_all()
    

    # COMBINE SPEAKERS INTO ONE AUDIO OUTPUT
    if check_if_connected()[0]:
        print("All devices are connected, ready to combine speakers")
        combine_speakers()  
        
    else:
        print("Bluetooth initialization failed")


    

main()