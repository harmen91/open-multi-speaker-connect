import os
import json
from core.audio_sinks import combine_speakers
from core.reset import unload_audio_modules
from core.speaker import BluetoothSpeaker
from core.pactl import pactl
from core.load_env import COMBINED_OUTPUT_SINK
from core.audio_calibrator import AudioCalibrator

STATE_FILE = "speaker_state.json"

class AudioManager:
    def __init__(self, volume=50):
        self.volume = volume
        self.speakers = []
        self.combined_sink_name = COMBINED_OUTPUT_SINK
        self.restore_state()

    def persist_state(self):
        data = {
            "combined_sink_name": self.combined_sink_name,
            "speakers": [spk.to_dict() for spk in self.speakers]
        }

        with open(STATE_FILE, "w") as f:
            json.dump(data, f, indent=4)

        print("Speaker configuration saved to disk.")

    def restore_state(self):
        if not os.path.exists(STATE_FILE):
            return False

        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)

            self.combined_sink_name = data.get(
                "combined_sink_name",
                f"{COMBINED_OUTPUT_SINK}"
            )
            self.speakers = [
                BluetoothSpeaker.from_dict(d)
                for d in data.get("speakers", [])
            ]

            print(f"Loaded {len(self.speakers)} speakers from {STATE_FILE}")
            return True
        except Exception as e:
            print(f"Failed to load state: {e}")
            return False

    def set_master_volume(self, level: int):
        level = max(0, min(100, level))
        pactl(f"set-sink-volume {self.combined_sink_name} {level}%")
        print(f"Master volume set to {level}%")

    def set_volume(self, level: int):
        self.volume = max(0, min(100, level))
        pactl(f"set-sink-volume {self.combined_sink_name} {self.volume}%")
        return

    def volume_up(self):
        return self.set_volume(self.volume + 10)

    def volume_down(self):
        return self.set_volume(self.volume - 10)

    def calibrate(self):
        if not self.speakers:
            print(
                "No speakers loaded. Make sure speaker_state.json exists and has speakers."
            )
            return None

        print(f"Found {len(self.speakers)} speaker(s):")
        for s in self.speakers:
            print(f" - {s.name} (current latency: {s.latency_ms}ms)")

        print(
            "\nStarting calibration... Make sure your microphone is ready and not muted."
        )

        calibrator = AudioCalibrator(self.speakers)
        results = calibrator.calibrate()

        self.persist_state()

        print("\nCalibration Complete!")

        print("\nUpdated speaker values:")
        for s in self.speakers:
            print(f" - {s.name}: {s.latency_ms}ms")

        return