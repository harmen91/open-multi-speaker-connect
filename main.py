import sys
import builtins

from core.load_env import CONTROLLER_INPUT, CONTROLLER_OUTPUT, INPUT_DEVICES, OUTPUT_DEVICES, COMBINED_OUTPUT_SINK
from core.bluetoothctl import bluetooth_connect_speakers, bluetoothctl_remove_devices
from core.audio_manager import AudioManager
from core.audio_sinks import unload_audio_modules, is_combined_sink_active, build_speaker_list

from app.workflows import factory_reset, delete_speaker_state_file
from app.use_cases import connect_and_combine_all

from interfaces.tui.presenter import build_app_config
from interfaces.tui.engine import start_app, log, non_blocking, get_active_menu

# INSTANTIATE AUDIOMANAGER // LOADS JSON STATE FILE AND BUILDS SPEAKER OBJECTS FROM SPEAKER CLASS
audio_mgr = AudioManager()

def tui_connect_and_combine_all():
    """Thin wrapper: runs the use case, then tells the TUI to refresh."""
    connect_and_combine_all(audio_mgr, CONTROLLER_OUTPUT, OUTPUT_DEVICES, COMBINED_OUTPUT_SINK)
    get_active_menu().update_config(tui_config())
    return "Connect and combine complete!"

# COMBINED FACTORY RESET FUNCTION TO WORK WITHIN CLI_APP
def tui_factory_reset():
    factory_reset()
    audio_mgr.speakers = []
    get_active_menu().update_config(tui_config())
    return "Factory reset complete."

## PASS IN FUNCTIONS TO BE USED WITHIN TUI > interfaces/tui/presenter.py 
def tui_config():
    config = build_app_config(
        audio_mgr,
        tui_connect_and_combine_all,
        tui_factory_reset,
        unload_audio_modules,
        bluetoothctl_remove_devices,
        delete_speaker_state_file
    )
    return config

# START TERMINAL USER INTERFACE
def tui():
    if is_combined_sink_active(audio_mgr.combined_sink_name) and not audio_mgr.speakers:
        audio_mgr.speakers = build_speaker_list()
        audio_mgr.persist_state()
    start_app(title="OPEN SPEAKER CONNECT", menu_config=tui_config())

# START WEB USER INTERFACE
def web():
    print("I have to be built still..")

# DECIDE WHICH APP TO LAUNCH
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--tui":
        ## HIJACKING PRINT STATEMENTS HACK GLOBALLY ACROSS ALL IMPORTED MODULES FOR RENDERING IN CLI_APP
        builtins.print = log
        ## LAUNCH TUI
        tui()
    elif len(sys.argv) > 1 and sys.argv[1] == "--web":
        ## LAUNCH WEBAPP
        web()
    else:
        print("please run this script with either --tui or --web arguments")
