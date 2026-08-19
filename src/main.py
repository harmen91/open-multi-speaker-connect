import time
from bt_connect import CONTROLLER_OUTPUT
from bt_connect import setup_controller, pair_all_devices, connect_all_devices, check_if_connected, check_if_paired, remove_devices, bt_scan_stop_all

def main():

    # remove_devices() # TEST CODE TO REMOVE DEVICES, not necessary here in final, it also lives in pair_all_device()
    # time.sleep(2)


    # # initial setup
    setup_controller(CONTROLLER_OUTPUT)

    # check if speakers are trusted & paired
    if not check_if_paired(verbose=False):
        pair_all_devices()

    # check if speakers are connected
    if not check_if_connected(verbose=False)[0]:
        connect_all_devices()
        bt_scan_stop_all()
    
    if check_if_connected()[0]:
        print("All devices are connected")
    

main()