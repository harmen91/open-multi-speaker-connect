import os
import json
import time
from core.audio_sinks import build_speakers, combine_speakers, cleanup_modules, pactl, BluetoothSpeaker
from core.load_env import COMBINED_OUTPUT_SINK

# STATE FILE 
STATE_FILE = "speaker_state.json"

class AudioManager:
    def __init__(self):
        self.speakers = []
        self.combined_sink_name = COMBINED_OUTPUT_SINK
        self.load_state()

    def save_state(self):
        data = {
            "combined_sink_name": self.combined_sink_name,
            "speakers": [spk.to_dict() for spk in self.speakers]
        }
        with open(STATE_FILE, "w") as f:
            json.dump(data, f, indent=4)
        print("Speaker configuration saved to disk.")

    def load_state(self):
        if not os.path.exists(STATE_FILE):
            return False

        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
            self.combined_sink_name = data.get("combined_sink_name", f"{COMBINED_OUTPUT_SINK}")
            self.speakers = [BluetoothSpeaker.from_dict(d) for d in data.get("speakers", [])]
            print(f"Loaded {len(self.speakers)} speakers from {STATE_FILE}")
            return True
        except Exception as e:
            print(f"Failed to load state: {e}")
            return False

    def setup_audio(self):
        cleanup_modules()
        self.speakers = combine_speakers(self.combined_sink_name)
        self.save_state()
        print(f"Initialized & saved {len(self.speakers)} speakers.")

    def set_master_volume(self, level: int):
        level = max(0, min(100, level))
        pactl(f"set-sink-volume {self.combined_sink_name} {level}%")
        print(f"Master volume set to {level}%")



    # ## NEEDS TO LEAVE THIS FILE
    # def build_menu_config(self):
    #     speaker_submenus = {}

    #     for spk in self.speakers:
    #         speaker_submenus[f"Speaker: {spk.name}"] = {
    #             "Set Latency (ms)": spk.set_latency,
    #             "Set Volume (0-100)": spk.set_volume,
    #             "Toggle Mute": spk.toggle_mute,
    #         }

    #     return speaker_submenus if speaker_submenus else {
    #         "No speakers active (Run Setup)": lambda: print("Run Audio Setup first.")
    #     }