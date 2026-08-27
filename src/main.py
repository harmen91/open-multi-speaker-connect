import time
import sys
import builtins

from load_env import CONTROLLER_INPUT, CONTROLLER_OUTPUT, INPUT_DEVICES, OUTPUT_DEVICES, COMBINED_OUTPUT_SINK
from bt_connect import bluetooth_connect_speakers, check_if_all_connected, bt_remove_devices, bt_scan_stop_all
from audio_manager import AudioManager
from factory_reset import factory_reset
from audio_sinks import combine_speakers, cleanup_modules, check_if_combined, pactl, build_speakers
from cli_app import start_app, log, non_blocking, get_active_menu

## HIJACKING PRINT STATEMENTS HACK GLOBALLY ACROSS ALL IMPORTED MODULES FOR RENDERING IN CLI_APP
builtins.print = log

# INSTANTIATE AUDIOMANAGER
audio_mgr = AudioManager()

# CONNECT ALL DEVICES CURRENTLY LISTED IN ENV USING CONTROLLER OUTPUT
def connect_all():
    all_connected, connected_list = bluetooth_connect_speakers(CONTROLLER_OUTPUT, OUTPUT_DEVICES)
    
    print("##################### ARE ALL DEVICES CONNECTED? #######################")
    print(all_connected)
    print("##################### LIST ALL CONNECTED DEVICES #######################")
    print(connected_list)
    print("#################### FINISHED CONNECTING DEVICES ######################")

    time.sleep(5)   ## TIME.SLEEP IS SOMEHOW IMPORTANT TO GET A RELIABLE SINK CREATION 
                    ## TEST FIGURE OUT WHY ?? IMPLEMENT CHECK TO SEE IF REGULAR AUDIO SINKS ARE CREATED
    print(bt_scan_stop_all) # STOP BACKGROUND SCANNING THREADS > IMPORTANT FOR OLD HARDWARE 
    print("#################### BLUETOOTH BACKGROUND SCAN OFF ######################")
    
    # FETCH NAME FOR THE COMBINED SINK FROM ENV
    name_combined_speakers = COMBINED_OUTPUT_SINK
    
    if all_connected:
        if not check_if_combined(name_combined_speakers):
            cleanup_modules()
            
            # 1. Store speakers on audio_mgr
            audio_mgr.speakers = combine_speakers(name_combined_speakers)
            # 2. Save state immediately to JSON!
            audio_mgr.save_state()
        else:
            print(f"Already combined as {name_combined_speakers}")
    else:
        print("Bluetooth initialization failed")

    # ONE COMMAND TO RELOAD THE ACTIVE MENU AND HAVE SPEAKER OBJECTS REBUILT
    get_active_menu().update_config(get_app_config())
    
    return "Connect and combine complete!"

# COMBINED FACTORY RESET FUNCTION TO WORK WITHIN CLI_APP
def full_factory_reset():
    factory_reset() # CLEANUP PIPEWIRE SINK MODULES & BLUETOOTHCTL REMOVE DEVICE EACH MAC FROM ENV
    audio_mgr.speakers = [] # EMPTY SPEAKER OBJECT FROM AUDIOMNG >> MOVE TO FACTORY_RESET MAYBE? ()
    get_active_menu().update_config(get_app_config()) #RELOAD ACTIVE MENU TO GET RID OF OLD SPEAKER OBJECTS
    return "Factory reset complete."

# MENU CONFIGURATION FOR CLI APP
def get_app_config():
    return {
        "BLUETOOTHCTL Connect All & Combine": connect_all,
        "Speaker Controls": audio_mgr.build_menu_config(),
        "Master Volume (0-100)": audio_mgr.set_master_volume,
        "System": {
            "Full Factory Reset": full_factory_reset,
            "Unpair Bluetooth Devices": bt_remove_devices,
        },
    }

# MAIN
def main():
    # RE-ATTACH AUDIO MANAGER SPEAKER OBJECT CREATION AT STARTUP TO RUNNING SINKS, IF EXIST, OTHERWISE DO NOTHING
    if check_if_combined(audio_mgr.combined_sink_name):
        if not audio_mgr.speakers:
            audio_mgr.speakers = build_speakers()
            audio_mgr.save_state()

    # START TERMINAL CLI_APP
    start_app(title="OPEN SPEAKER CONNECT", menu_config=get_app_config())

if __name__ == "__main__":
    main()
