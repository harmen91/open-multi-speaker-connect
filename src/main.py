import time
import sys
import builtins

from load_env import CONTROLLER_INPUT, CONTROLLER_OUTPUT, INPUT_DEVICES, OUTPUT_DEVICES, COMBINED_OUTPUT_SINK
from bt_connect import bluetooth_connect_speakers, check_if_all_connected, bt_remove_devices
from audio_manager import AudioManager
from factory_reset import factory_reset
from audio_sinks import combine_speakers, cleanup_modules, check_if_combined, pactl, build_speakers
from cli_app import start_app, log, non_blocking, get_active_menu

## HIJACKING PRINT STATEMENTS GLOBALLY ACROSS ALL IMPORTED MODULES FOR RENDERING IN CLI_APP
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

    time.sleep(5)
    
    name_combined_speakers = COMBINED_OUTPUT_SINK.replace(" ", "")
    
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

def full_factory_reset():
    factory_reset()
    audio_mgr.speakers = []
    return "Factory reset complete."

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

def main():

    # Re-attach to running sinks if they already exist, otherwise do nothing
    if check_if_combined(audio_mgr.combined_sink_name):
        if not audio_mgr.speakers:
            audio_mgr.speakers = build_speakers()
            audio_mgr.save_state()

    start_app(title="OPEN SPEAKER CONNECT", menu_config=get_app_config())

if __name__ == "__main__":
    main()
