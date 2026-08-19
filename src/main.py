import time
from bt_connect import CONTROLLER_OUTPUT
from bt_connect import setup_controller, pair_all_devices, connect_all_devices, check_if_connected, check_if_paired, remove_devices

def main():

    # # initial setup
    setup_controller(CONTROLLER_OUTPUT)
    time.sleep(2)


    # remove_devices() # TEST CODE TO REMOVE DEVICES, not necessary here in final, it also lives in pair_all_device()
    # time.sleep(2)

    # check if all speakers are already trusted & paired
    if not check_if_paired():
        pair_all_devices()

    # check if all speakers are already connected
    if not check_if_connected()[0]:
        connect_all_devices()
    elif check_if_connected()[0]:
        print("Succesfully connected all devices")

main()