import os
import json
from core.audio_sinks import combine_speakers, get_live_modules
from core.reset import unload_audio_modules
from core.speaker import BluetoothSpeaker
from core.pactl import pactl
from core.load_env import COMBINED_OUTPUT_SINK
from core.audio_calibrator import AudioCalibrator

# path where the speaker configuration is saved and restored from
STATE_FILE = "speaker_state.json"

# manages the full speaker setup: restores saved speakers, persists changes,
# and reconciles persisted module ids against live pipewire state
class AudioManager:
    def __init__(self, volume=50):
        self.volume = volume
        self.speakers = []
        self.combined_sink_name = COMBINED_OUTPUT_SINK
        self.restore_state()

    # writes the current speaker list and combined sink name to disk as json,
    # so sessions can survive restarts and disconnects
    def persist_state(self):
        data = {
            "combined_sink_name": self.combined_sink_name,
            "speakers": [spk.to_dict() for spk in self.speakers]
        }

        with open(STATE_FILE, "w") as f:
            json.dump(data, f, indent=4)

        print("Speaker configuration saved to disk.")

    # loads speakers from speaker_state.json back into bluetooth speaker objects;
    # returns False if no state file exists or the file couldn't be parsed
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

    # checks each speaker's persisted module ids against live pipewire state,
    # repairs only what's stale, and fixes the combine-sink if needed
    def reconcile(self):
        if not self.speakers:
            return

        live_modules = get_live_modules()
        repaired = False

        for speaker in self.speakers:
            if not speaker.verify_alive(live_modules):
                print(f"Reconcile: repairing {speaker.name} (stale/missing PipeWire module)")
                speaker.repair(live_modules)
                repaired = True

        # check whether a module-combine-sink for this combined sink name is still live
        combine_ok = any(
            m["name"] == "module-combine-sink" and f"sink_name={self.combined_sink_name}" in m["argument"]
            for m in live_modules.values()
        )

        # rebuild the combine-sink if anything was repaired or it's missing:
        # unload stale combine-sink modules, reload with the current slave list, re-set as default
        if repaired or not combine_ok:
            for mod_id, m in live_modules.items():
                if m["name"] == "module-combine-sink" and f"sink_name={self.combined_sink_name}" in m["argument"]:
                    pactl(f"unload-module {mod_id}")
            slaves = ",".join(s.get_null_sink_name() for s in self.speakers)
            pactl(f"load-module module-combine-sink sink_name={self.combined_sink_name} slaves={slaves}")
            pactl(f"set-default-sink {self.combined_sink_name}")

        # persist the new module ids if any speaker was repaired
        if repaired:
            self.persist_state()

    # sets volume on the combined sink itself, affecting all speakers at once
    def set_master_volume(self, level: int):
        level = max(0, min(100, level))
        pactl(f"set-sink-volume {self.combined_sink_name} {level}%")
        print(f"Master volume set to {level}%")

    # clamps and applies the tracked volume level to the combined sink via pactl
    def set_volume(self, level: int):
        self.volume = max(0, min(100, level))
        pactl(f"set-sink-volume {self.combined_sink_name} {self.volume}%")
        return

    # raises volume by 10%, clamped to 100%
    def volume_up(self):
        return self.set_volume(self.volume + 10)

    # lowers volume by 10%, clamped to 0%
    def volume_down(self):
        return self.set_volume(self.volume - 10)

    # interactive latency calibration: prompts the user, runs the audio calibrator,
    # then persists the updated latency values back to disk
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