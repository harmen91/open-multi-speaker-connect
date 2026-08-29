from interfaces.tui.engine import log
import threading
 
## THIS FACTORY FUNCTION BUILDS A MENU ACTION CLOSURE THAT APPLIES A NEW LATENCY TO A SPEAKER AND PERSISTS STATE IN THE BACKGROUND
def _wrap_set_latency(speaker, audio_mgr):
    ## THIS INNER FUNCTION IS THE ACTUAL MENU-BOUND ACTION: IT SETS THE LATENCY, THEN KICKS OFF A NON-BLOCKING SAVE
    def action(latency_ms: int):
        result = speaker.set_latency(latency_ms)
        # Save happens AFTER the action returns, without blocking the UI
        threading.Thread(target=audio_mgr.persist_state, daemon=True).start()
        return result
    return action
 
## THIS FUNCTION RENDERS A TEXT-BASED VOLUME BAR STRING (E.G. "[====......] 40%") FOR LOGGING TO THE TUI
def _volume_bar(name: str, level: int, width: int = 20) -> str:
    ## THIS VARIABLE HOLDS THE NUMBER OF "FILLED" CHARACTERS PROPORTIONAL TO THE VOLUME LEVEL
    filled = int((level / 100) * width)
    ## THIS VARIABLE HOLDS THE ASSEMBLED BAR STRING, FILLED CHARACTERS FOLLOWED BY EMPTY CHARACTERS
    bar = "=" * filled + "." * (width - filled)
    return f"[{name}] Level: [{bar}] {level}%"
 
## THIS FACTORY FUNCTION BUILDS A MENU ACTION CLOSURE THAT SETS A SINGLE SPEAKER'S VOLUME AND LOGS A VOLUME BAR
def _wrap_speaker_volume(speaker):
    ## THIS INNER FUNCTION IS THE ACTUAL MENU-BOUND ACTION: IT CLAMPS THE LEVEL, APPLIES IT, AND LOGS THE RESULT
    def action(level: int):
        level = max(0, min(100, level))
        result = speaker.set_volume(level)
        log(_volume_bar(speaker.name, level))
        return result
    return action
 
## THIS FACTORY FUNCTION BUILDS A MENU ACTION CLOSURE THAT RAISES A SINGLE SPEAKER'S VOLUME BY 10% AND LOGS A VOLUME BAR
def _wrap_volume_up(speaker):
    ## THIS INNER FUNCTION IS THE ACTUAL MENU-BOUND ACTION: IT BUMPS THE VOLUME UP AND LOGS THE RESULT
    def action():
        result = speaker.volume_up()
        log(_volume_bar(speaker.name, speaker.volume))
        return result
    return action
 
## THIS FACTORY FUNCTION BUILDS A MENU ACTION CLOSURE THAT LOWERS A SINGLE SPEAKER'S VOLUME BY 10% AND LOGS A VOLUME BAR
def _wrap_volume_down(speaker):
    ## THIS INNER FUNCTION IS THE ACTUAL MENU-BOUND ACTION: IT DROPS THE VOLUME DOWN AND LOGS THE RESULT
    def action():
        result = speaker.volume_down()
        log(_volume_bar(speaker.name, speaker.volume))
        return result
    return action
 
## THIS FACTORY FUNCTION BUILDS A MENU ACTION CLOSURE THAT SETS THE COMBINED SINK'S MASTER VOLUME AND LOGS A VOLUME BAR
def _wrap_master_volume(audio_mgr):
    ## THIS INNER FUNCTION IS THE ACTUAL MENU-BOUND ACTION: IT CLAMPS THE LEVEL, APPLIES IT VIA AudioManager, AND LOGS THE RESULT
    def action(level: int):
        level = max(0, min(100, level))
        result = audio_mgr.set_master_volume(level)
        log(_volume_bar("Master", level))
        return result
    return action
 
## THIS FUNCTION ASSEMBLES THE FULL NESTED DICTIONARY CONFIG CONSUMED BY interfaces/tui/engine.py'S build_menu() TO CONSTRUCT THE TUI
def build_app_config(audio_mgr, connect_all_fn, factory_reset_fn, unload_modules_fn, bluetoothctl_remove_devices_fn, delete_speaker_state_file_fn):
    ## THIS VARIABLE HOLDS THE SUBMENU CONFIG FOR EACH CONNECTED SPEAKER, KEYED BY "Speaker: <name>"
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
 
    ## THIS RETURN VALUE IS THE TOP-LEVEL MENU CONFIG: CONNECT/COMBINE, PER-SPEAKER CONTROLS, MASTER VOLUME, AND SYSTEM ACTIONS
    return {
        "BLUETOOTHCTL Connect All & Combine": connect_all_fn,
        "Speaker Controls": speaker_controls if speaker_controls else {
            "No speakers active (Run Setup)": lambda: "Run Audio Setup first."
        },
        "Master Volume (0-100)": _wrap_master_volume(audio_mgr),
        "System": {
            "Full Factory Reset": factory_reset_fn,
            "Unload Modules": unload_modules_fn,
            "Unpair Bluetooth Devices": bluetoothctl_remove_devices_fn,
            "Delete Speaker State JSON File": delete_speaker_state_file_fn,
        },
    }
 
