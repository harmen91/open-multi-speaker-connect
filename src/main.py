import time
# from bt_connect import CONTROLLER_OUTPUT
# from bt_connect import setup_controller, pair_all_devices, connect_all_devices, check_if_connected, check_if_paired, remove_devices, bt_scan_stop_all
from load_env import CONTROLLER_INPUT, CONTROLLER_OUTPUT, INPUT_DEVICES, OUTPUT_DEVICES
from bt_connect_v3 import bluetooth_connect_speakers, check_if_all_connected
from factory_reset import factory_reset
from audio_sinks import combine_speakers, cleanup_modules, check_if_combined

def main():

    # RUN BT_CONNECT_v3 CONNECT ALL OUTPUT_DEVICES TO CONTROLLER_OUTPUT > RETURNS (BOOL,[LIST])
    # UNPACK RETURN TUPLE IN BOOLEAN AND LIST
    all_connected_bt_speakers, list_connected_bt_speakers = bluetooth_connect_speakers(CONTROLLER_OUTPUT, OUTPUT_DEVICES)
   
    print("#####################  ARE ALL DEVICES CONNECTED? #######################")
    print(all_connected_bt_speakers)
    print("#####################  LIST ALL CONNECTED DEVICES #######################")

    print(list_connected_bt_speakers)
    print("#####################  THE END  #######################")


    time.sleep(5)
    
    # NAME YOUR COMBINED SPEAKER OUTPUT AUDIO SINK
    name_combined_speakers = "klumpil sakkus lumpil"
    
    # COMBINE CONNECTED SPEAKERS INTO ONE AUDIO OUTPUT
    # cleanup_modules()



    if all_connected_bt_speakers:
        if not check_if_combined(name_combined_speakers.replace(" ", "")):
            cleanup_modules()
            combine_speakers(name_combined_speakers.replace(" ", "")) 
        else:
            print(f"Already combined as {name_combined_speakers}")
    else:
        print("Bluetooth initialization failed")


main()

