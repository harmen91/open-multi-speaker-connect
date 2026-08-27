from interfaces.tui.engine import log
import threading

def _wrap_set_latency(speaker, audio_mgr):
    def action(latency_ms: int):
        result = speaker.set_latency(latency_ms)
        # Save happens AFTER the action returns, without blocking the UI
        threading.Thread(target=audio_mgr.save_state, daemon=True).start()
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
        result = audio_mgr.set_master_volume(level)
        log(_volume_bar("Master", level))
        return result
    return action

def build_app_config(audio_mgr, connect_all_fn, factory_reset_fn, cleanup_modules_fn, unpair_fn, delete_speaker_state_file_fn):
    speaker_controls = {}
    for spk in audio_mgr.speakers:
        speaker_controls[f"Speaker: {spk.name}"] = {
            "Set Latency (ms)": _wrap_set_latency(spk, audio_mgr),
            "Set Volume (0-100)": _wrap_speaker_volume(spk),
            "Volume Up 10%": _wrap_volume_up(spk),
            "Volume Down 10%": _wrap_volume_down(spk),
            "Mute On": spk.mute_on,
            "Mute Off": spk.mute_off,
        }

    return {
        "BLUETOOTHCTL Connect All & Combine": connect_all_fn,
        "Speaker Controls": speaker_controls if speaker_controls else {
            "No speakers active (Run Setup)": lambda: "Run Audio Setup first."
        },
        "Master Volume (0-100)": _wrap_master_volume(audio_mgr),
        "System": {
            "Full Factory Reset": factory_reset_fn,
            "Unload Modules": cleanup_modules_fn,
            "Unpair Bluetooth Devices": unpair_fn,
            "Delete Speaker State JSON File": delete_speaker_state_file_fn,
        },
    }