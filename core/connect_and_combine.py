import time
from core.bluetoothctl import bluetooth_connect_speakers, all_connected, bluetoothctl_scan_stop
from core.audio_sinks import combine_speakers, is_combined_sink_active, map_mac_to_sink
from core.reset import unload_audio_modules
from core.audio_manager import AudioManager

## THIS FUNCTION POLLS PACTL UNTIL EVERY CONNECTED MAC HAS A REAL (NON-NULL-DELAYED) SINK, OR THE TIMEOUT EXPIRES
def wait_for_sinks(connected_list, timeout=10, interval=0.25):
    deadline = time.monotonic() + timeout
    mapped = map_mac_to_sink()
    while time.monotonic() < deadline and not all(mac in mapped for mac in connected_list):
        time.sleep(interval)
        mapped = map_mac_to_sink()
    missing = [mac for mac in connected_list if mac not in mapped]
    if missing:
        print(f"[wait_for_sinks] No sink appeared for: {missing}")
    return mapped
 
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
 
    print("Check: Are all devices connected?")
    print(all_connected)
    print("List all connected devices:")
    print(connected_list)
    print("Finished connecting devices")
 
    # Sinks must exist BEFORE the scan process is killed — scan_stop too early was the root cause of missing sinks
    wait_for_sinks(connected_list)
 
    bluetoothctl_scan_stop()
    print("Bluetooth scan off")
 
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
 
