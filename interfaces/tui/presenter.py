from interfaces.tui.engine import log, MenuItem
from interfaces.tui.device_menu import DeviceSelectionMenu
import threading
 
def _wrap_set_latency(speaker, audio_mgr):
    def action(latency_ms: int):
        result = speaker.set_latency(latency_ms)
        # Non-blocking state persistence to prevent UI freeze
        threading.Thread(target=audio_mgr.persist_state, daemon=True).start()
        return result
    return action

def _wrap_update_channel(speaker, audio_mgr):
    def action(channel_str: str):
        result = speaker.update_channel(channel_str)
        # Non-blocking state persistence to prevent UI freeze
        threading.Thread(target=audio_mgr.persist_state, daemon=True).start()
        return result
    return action
 
def _volume_bar(name: str, level: int, width: int = 20) -> str:
    filled = int((level / 100) * width)
    bar = "=" * filled + "." * (width - filled)
    return f"[{name}] Level: [{bar}] {level}%"
 
def _wrap_speaker_volume(speaker):
    def action(level: int):
        level = max(0, min(100, level))
        result = speaker.set_volume(level)
        log(_volume_bar(speaker.name, level))
        return result
    return action
 
def _wrap_volume_up(speaker):
    def action():
        result = speaker.volume_up()
        log(_volume_bar(speaker.name, speaker.volume))
        return result
    return action
 
def _wrap_volume_down(speaker):
    def action():
        result = speaker.volume_down()
        log(_volume_bar(speaker.name, speaker.volume))
        return result
    return action
 
def _wrap_master_volume(audio_mgr):
    def action(level: int):
        level = max(0, min(100, level))
        result = audio_mgr.set_volume(level)
        log(_volume_bar("Master", level))
        return result
    return action

def _wrap_master_volume_up(audio_mgr):
    def action():
        result = audio_mgr.volume_up()
        log(_volume_bar("Master", audio_mgr.volume))
        return result
    return action
 
def _wrap_master_volume_down(audio_mgr):
    def action():
        result = audio_mgr.volume_down()
        log(_volume_bar("Master", audio_mgr.volume))
        return result
    return action
 
from interfaces.tui.device_menu import DeviceSelectionMenu

def build_app_config(
    audio_mgr,
    device_selection_menu,
    connect_all_fn,
    factory_reset_fn,
    unload_modules_fn,
    bluetoothctl_remove_devices_fn,
    delete_speaker_state_file_fn,
    delete_selected_devices_state_file_fn,
):
    speaker_controls = {}
    for spk in audio_mgr.speakers:
        speaker_controls[f"Speaker: {spk.name}"] = {
            "Set Latency (ms)": _wrap_set_latency(spk, audio_mgr),
            "Set Channel (STEREO, FL, FR)": _wrap_update_channel(spk, audio_mgr),
            "Set Volume (0-100)": _wrap_speaker_volume(spk),
            "Volume Up 10%": _wrap_volume_up(spk),
            "Volume Down 10%": _wrap_volume_down(spk),
            "Mute On": spk.mute_on,
            "Mute Off": spk.mute_off,
        }
 
    return {
        "Audio Setup": {
            "Scan & Select Bluetooth Devices": device_selection_menu,
            "Auto connect & combine": connect_all_fn,
            "Auto calibrate speakers": audio_mgr.calibrate,
        },
        "Speaker controls": speaker_controls if speaker_controls else {
            "No speakers active (Run Setup)": lambda: "Run Audio Setup first."
        },
        "Master Volume (0-100)": _wrap_master_volume(audio_mgr),
        "Master Volume Up 10%": _wrap_master_volume_up(audio_mgr),
        "Master Volume Down 10%": _wrap_master_volume_down(audio_mgr),
        "System Reset": {
            "Full Factory Reset": factory_reset_fn,
            "Unload All Created Audio Sinks": unload_modules_fn,
            "Unpair Bluetooth Devices": bluetoothctl_remove_devices_fn,
            "Delete Speaker State JSON File": delete_speaker_state_file_fn,
            "Delete Selected Devices JSON File": delete_selected_devices_state_file_fn,
        },
    }