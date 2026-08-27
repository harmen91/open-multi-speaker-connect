import time
import sys
from pathlib import Path
import builtins

from core.load_env import CONTROLLER_INPUT

from core.load_env import CONTROLLER_INPUT, CONTROLLER_OUTPUT, INPUT_DEVICES, OUTPUT_DEVICES, COMBINED_OUTPUT_SINK
from core.bt_connect import bluetooth_connect_speakers, check_if_all_connected, bt_remove_devices, bt_scan_stop_all
from core.audio_manager import AudioManager
from core.factory_reset import factory_reset
from core.audio_sinks import combine_speakers, cleanup_modules, check_if_combined, pactl, build_speakers

from interfaces.tui.engine import start_app, log, non_blocking, get_active_menu



# INSTANTIATE AUDIOMANAGER
audio_mgr = AudioManager()


### PRESENTATION HELPERS FOR TERMINAL_CLI

def _volume_bar(name: str, level: int, width: int = 20) -> str:
    filled = int((level / 100) * width)
    bar = "=" * filled + "." * (width - filled)
    return f"[{name}] Level: [{bar}] {level}%"

def _wrap_speaker_volume(speaker):
    """Returns a CLI action that sets volume and renders a progress bar."""
    def action(level: int):
        level = max(0, min(100, level))
        result = speaker.set_volume(level)   # pure core call
        log(_volume_bar(speaker.name, level))
        return result
    return action

def _wrap_master_volume(audio_mgr):
    def action(level: int):
        level = max(0, min(100, level))
        result = audio_mgr.set_master_volume(level)   # pure core call
        log(_volume_bar("Master", level))
        return result
    return action


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
# def get_app_config():
#     return {
#         "BLUETOOTHCTL Connect All & Combine": connect_all,
#         "Speaker Controls": audio_mgr.build_menu_config(),
#         "Master Volume (0-100)": audio_mgr.set_master_volume,
#         "System": {
#             "Full Factory Reset": full_factory_reset,
#             "Unpair Bluetooth Devices": bt_remove_devices,
#         },
#     }

def get_app_config():
    speaker_controls = {}
    for spk in audio_mgr.speakers:
        speaker_controls[f"Speaker: {spk.name}"] = {
            "Set Latency (ms)": spk.set_latency,
            "Set Volume (0-100)": _wrap_speaker_volume(spk),
            "Toggle Mute": spk.toggle_mute,
        }

    return {
        "BLUETOOTHCTL Connect All & Combine": connect_all,
        "Speaker Controls": speaker_controls if speaker_controls else {
            "No speakers active (Run Setup)": lambda: "Run Audio Setup first."
        },
        "Master Volume (0-100)": _wrap_master_volume(audio_mgr),
        "System": {
            "Full Factory Reset": full_factory_reset,
            "Unpair Bluetooth Devices": bt_remove_devices,
        },
    }


# TERMINAL USER INTERFACE
def tui():
    # RE-ATTACH AUDIO MANAGER SPEAKER OBJECT CREATION AT STARTUP TO RUNNING SINKS, IF EXIST, OTHERWISE DO NOTHING
    if check_if_combined(audio_mgr.combined_sink_name):
        if not audio_mgr.speakers:
            audio_mgr.speakers = build_speakers()
            audio_mgr.save_state()

    # START TERMINAL CLI_APP
    start_app(title="OPEN SPEAKER CONNECT", menu_config=get_app_config())

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
