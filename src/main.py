import time
# from bt_connect import CONTROLLER_OUTPUT
# from bt_connect import setup_controller, pair_all_devices, connect_all_devices, check_if_connected, check_if_paired, remove_devices, bt_scan_stop_all
from bt_connect_v3 import CONTROLLER_OUTPUT, OUTPUT_DEVICES
from bt_connect_v3 import bluetooth_connect_speakers, check_if_all_connected
from factory_reset import factory_reset

from audio_sinks import combine_speakers, cleanup_modules, check_if_combined

def main():

    # RUN BT_CONNECT_v3 CONNECT ALL OUTPUT_DEVICES TO CONTROLLER_OUTPUT
    bluetooth_connect_speakers(CONTROLLER_OUTPUT, OUTPUT_DEVICES)

    # NAME YOUR COMBINED SPEAKER OUTPUT AUDIO SINK
    name_combined_speakers = "klumpil sakkus lumpil"
    
    # COMBINE CONNECTED SPEAKERS INTO ONE AUDIO OUTPUT
    if check_if_all_connected()[0]:
        print("All devices are connected")
        if not check_if_combined(name_combined_speakers.replace(" ", "")):
            cleanup_modules()
            combine_speakers(name_combined_speakers.replace(" ", "")) 
        else:
            print(f"Already combined as {name_combined_speakers}")
    else:
        print("Bluetooth initialization failed")


    

main()