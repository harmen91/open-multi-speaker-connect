import time
import sys
import builtins

from core.load_env import CONTROLLER_INPUT, CONTROLLER_OUTPUT, INPUT_DEVICES, OUTPUT_DEVICES, COMBINED_OUTPUT_SINK
from core.bt_connect import bluetooth_connect_speakers, check_if_all_connected, bt_remove_devices, bt_scan_stop_all
from core.audio_manager import AudioManager
from core.factory_reset import factory_reset
from core.audio_sinks import combine_speakers, cleanup_modules, check_if_combined, pactl, build_speakers

from app.use_cases import connect_all

from interfaces.tui.presenter import build_app_config
from interfaces.tui.engine import start_app, log, non_blocking, get_active_menu

# INSTANTIATE AUDIOMANAGER
audio_mgr = AudioManager()

def tui_connect_all():
    """Thin wrapper: runs the use case, then tells the TUI to refresh."""
    connect_all(audio_mgr, CONTROLLER_OUTPUT, OUTPUT_DEVICES, COMBINED_OUTPUT_SINK)
    get_active_menu().update_config(
        build_app_config(audio_mgr, tui_connect_all, tui_factory_reset, bt_remove_devices)
    )
    return "Connect and combine complete!"

# COMBINED FACTORY RESET FUNCTION TO WORK WITHIN CLI_APP
def tui_factory_reset():
    factory_reset()
    audio_mgr.speakers = []
    get_active_menu().update_config(
        build_app_config(audio_mgr, tui_connect_all, tui_factory_reset, bt_remove_devices)
    )
    return "Factory reset complete."

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
