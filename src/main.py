import time
import sys
import builtins

from load_env import CONTROLLER_INPUT, CONTROLLER_OUTPUT, INPUT_DEVICES, OUTPUT_DEVICES
from bt_connect_v3 import bluetooth_connect_speakers, check_if_all_connected, bt_remove_devices
from factory_reset import factory_reset
from audio_sinks import combine_speakers, cleanup_modules, check_if_combined
from cli_app import start_app, log, non_blocking

## HIJACKING PRINT STATEMENTS GLOBALLY ACROSS ALL IMPORTED MODULES FOR RENDERING IN CLI_APP
builtins.print = log

def connect_all():

    # RUN BT_CONNECT_v3 CONNECT ALL OUTPUT_DEVICES TO CONTROLLER_OUTPUT > RETURNS (BOOL,[LIST])
    # UNPACK RETURN TUPLE IN BOOLEAN AND LIST
    all_connected_bt_speakers, list_connected_bt_speakers = bluetooth_connect_speakers(CONTROLLER_OUTPUT, OUTPUT_DEVICES)
   
    print("#####################  ARE ALL DEVICES CONNECTED? #######################")
    print(all_connected_bt_speakers)
    print("#####################  LIST ALL CONNECTED DEVICES #######################")

    print(list_connected_bt_speakers)
    print("####################  FINISHED CONNECTING DEVICES  ######################")

    time.sleep(5) ## SEEMS NECESSARY SOMETIMES FOR RELIABLE SINK CREATION
    
    # NAME YOUR COMBINED SPEAKER OUTPUT AUDIO SINK
    name_combined_speakers = "klumpil sakkus lumpil"
    
    if all_connected_bt_speakers: ## bug when speakers auto-reconnect and not show up in 'bluetoothctl devices Connected' anymore
        if not check_if_combined(name_combined_speakers.replace(" ", "")):
            cleanup_modules()
            combine_speakers(name_combined_speakers.replace(" ", "")) 
        else:
            print(f"Already combined as {name_combined_speakers}")
    else:
        print("Bluetooth initialization failed")
    
    return 


## TEST STACK ##
def test():
    
    ### TEST MENU ENTRY BLOCKING
    def test_count():
        max_count = 10
        count = 0
        while count < max_count:
            count += 1
            time.sleep(0.3)
            log(f"Counting (blocked menu): {count}")
        return "Counting finished."


    ### TEST MENU ENTRY NON BLOCKING
    @non_blocking
    def background_scanner():
        log("Background scanner started (menu interactive!)...")
        for i in range(1, 11):
            time.sleep(1)
            log(f"[Background Task] Scan event #{i}")
        return "Background scan completed."

    app_config = {
        "Connect all speakers": connect_all,
        "Count (Blocks Menu)": test_count,
        "Background Task (Interactive)": background_scanner,
        "System Check": lambda: "All systems nominal.",

        # Nested Submenu:
        "Settings": {
            "Factory Reset": factory_reset,
            "Cleanup pipewire modules": cleanup_modules,
            "Remove all bluetooth devices": bt_remove_devices,
            "Audio Settings": {
                "Set Volume": lambda: "Placeholder set volume",
            },
        },
    }

    start_app(title="OPEN SPEAKER CONNECT", menu_config=app_config)

## NORMAL STACK EXECUTED BY ./MAIN.SH ##
def normal():
    test()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test()
    else:
        normal()