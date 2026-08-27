import time
import sys
import builtins

from core.load_env import CONTROLLER_INPUT, CONTROLLER_OUTPUT, INPUT_DEVICES, OUTPUT_DEVICES, COMBINED_OUTPUT_SINK
from core.bt_connect import bluetooth_connect_speakers, check_if_all_connected, bt_remove_devices, bt_scan_stop_all
from core.audio_manager import AudioManager
from core.factory_reset import factory_reset
from core.audio_sinks import combine_speakers, cleanup_modules, check_if_combined, pactl, build_speakers

from interfaces.tui.presenter import build_app_config
from interfaces.tui.engine import start_app, log, non_blocking, get_active_menu

# INSTANTIATE AUDIOMANAGER
audio_mgr = AudioManager()


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


    return "Connect and combine complete!"

def tui_connect_all():
    connect_all()
    # ONE COMMAND TO RELOAD THE ACTIVE MENU AND HAVE SPEAKER OBJECTS REBUILT
    get_active_menu().update_config(get_app_config())
    return result

# COMBINED FACTORY RESET FUNCTION TO WORK WITHIN CLI_APP
def tui_factory_reset():
    factory_reset() # CLEANUP PIPEWIRE SINK MODULES & BLUETOOTHCTL REMOVE DEVICE EACH MAC FROM ENV
    audio_mgr.speakers = [] # EMPTY SPEAKER OBJECT FROM AUDIOMNG >> MOVE TO FACTORY_RESET MAYBE? ()
    get_active_menu().update_config(get_app_config()) #RELOAD ACTIVE MENU TO GET RID OF OLD SPEAKER OBJECTS
    return "Factory reset complete"

# TERMINAL USER INTERFACE
def tui():
    if check_if_combined(audio_mgr.combined_sink_name) and not audio_mgr.speakers:
        audio_mgr.speakers = build_speakers()
        audio_mgr.save_state()

    config = build_app_config(
        audio_mgr,
        tui_connect_all,
        tui_factory_reset,
        bt_remove_devices
    )
    start_app(title="OPEN SPEAKER CONNECT", menu_config=config)

# WEB USER INTERFACE
def web():
    print("I have to be built still..")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--tui":
        ## HIJACKING PRINT STATEMENTS HACK GLOBALLY ACROSS ALL IMPORTED MODULES FOR RENDERING IN CLI_APP
        builtins.print = log
        tui()
    elif len(sys.argv) > 1 and sys.argv[1] == "--web":
        web()
    else:
        print("please run this script with either --tui or --web arguments")
