import time
from core.bluetoothctl import bluetooth_connect_speakers, all_connected, bluetoothctl_scan_stop
from core.audio_sinks import combine_speakers, is_combined_sink_active, map_mac_to_sink
from core.reset import unload_audio_modules
from core.audio_manager import AudioManager

# this function polls pactl until every connected mac has a real (non-null-delayed) sink, or the timeout expires
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
 
# top-level use case: connects all speakers over bluetooth and then combines them into one synced sink
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
    ## these hold whether every output device connected successfully, plus the list of devices that did connect
    all_connected, connected_list = bluetooth_connect_speakers(
        controller_output, output_devices
    )
 
    print("Check: Are all devices connected?")
    print(all_connected)
    print("List all connected devices:")
    print(connected_list)
    print("Finished connecting devices")
 
    # sinks must exist BEFORE the scan process is killed — scan_stop too early was the root cause of missing sinks
    wait_for_sinks(connected_list)
 
    bluetoothctl_scan_stop()
    print("Bluetooth scan off")
 
    ## only proceed to build the combined sink if every speaker connected successfully
    if all_connected:
        ## skip re-combining if the combined sink is already active, otherwise tear down old modules and rebuild
        if not is_combined_sink_active(combined_sink_name):
            unload_audio_modules()
            audio_mgr.speakers = combine_speakers(combined_sink_name)
            audio_mgr.persist_state()
        else:
            print(f"Already combined as {combined_sink_name}")
    else:
        print("Bluetooth initialization failed")
 
    return all_connected, connected_list