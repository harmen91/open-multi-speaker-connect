# use_cases.py
import time
from core.bt_connect import bluetooth_connect_speakers, check_if_all_connected, bt_scan_stop_all
from core.audio_sinks import combine_speakers, cleanup_modules, check_if_combined
from core.audio_manager import AudioManager


### THIS FILE HOLDS MIXED FUNCTIONALITY FROM CORE FOR BOTH WEB AND TUI APPS TO UTILIZE IN MAIN

def connect_all(
    audio_mgr: AudioManager,
    controller_output: str,
    output_devices: list,
    combined_sink_name: str
) -> tuple[bool, list]:
    """
    Orchestrates Bluetooth connection and combined sink creation.
    Returns (all_connected, connected_devices_list).
    """
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

    print(bt_scan_stop_all)
    print("#################### BLUETOOTH BACKGROUND SCAN OFF ######################")

    if all_connected:
        if not check_if_combined(combined_sink_name):
            cleanup_modules()
            audio_mgr.speakers = combine_speakers(combined_sink_name)
            audio_mgr.save_state()
        else:
            print(f"Already combined as {combined_sink_name}")
    else:
        print("Bluetooth initialization failed")

    return all_connected, connected_list