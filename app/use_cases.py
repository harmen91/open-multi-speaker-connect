# use_cases.py
import time
from core.bluetoothctl import bluetooth_connect_speakers, all_connected, bluetoothctl_scan_stop
from core.audio_sinks import combine_speakers, unload_audio_modules, is_combined_sink_active
from core.audio_manager import AudioManager
 
 
### THIS FILE HOLDS MIXED FUNCTIONALITY FROM CORE FOR BOTH WEB AND TUI APPS TO UTILIZE IN MAIN
 
## THIS FUNCTION IS THE TOP-LEVEL USE CASE THAT CONNECTS ALL SPEAKERS OVER BLUETOOTH AND THEN COMBINES THEM INTO ONE SYNCED SINK
def connect_and_combine_all(
    audio_mgr: AudioManager,
    controller_output: str,
    output_devices: list,
    combined_sink_name: str
) -> tuple[bool, list]:
    """
    Orchestrates Bluetooth connection and combined sink creation.
    Returns (all_connected, connected_devices_list).
    """
    ## THESE VARIABLES HOLD WHETHER EVERY OUTPUT DEVICE CONNECTED SUCCESSFULLY AND THE LIST OF DEVICES THAT DID CONNECT
    all_connected, connected_list = bluetooth_connect_speakers(
        controller_output, output_devices
    )
 
    print("##################### ARE ALL DEVICES CONNECTED? #######################")
    print(all_connected)
    print("##################### LIST ALL CONNECTED DEVICES #######################")
    print(connected_list)
    print("#################### FINISHED CONNECTING DEVICES ######################")
 
    # This sleep is a core concern (PipeWire sink reliability), so it stays here.
    time.sleep(5)
 
    bluetoothctl_scan_stop()
    print("#################### BLUETOOTH BACKGROUND SCAN OFF ######################")
 
    ## THIS CHECK ONLY PROCEEDS TO BUILD THE COMBINED SINK IF EVERY SPEAKER CONNECTED SUCCESSFULLY
    if all_connected:
        ## THIS CHECK SKIPS RE-COMBINING IF THE COMBINED SINK IS ALREADY ACTIVE, OTHERWISE TEARS DOWN OLD MODULES AND REBUILDS
        if not is_combined_sink_active(combined_sink_name):
            unload_audio_modules()
            audio_mgr.speakers = combine_speakers(combined_sink_name)
            audio_mgr.persist_state()
        else:
            print(f"Already combined as {combined_sink_name}")
    else:
        print("Bluetooth initialization failed")
 
    return all_connected, connected_list
 
