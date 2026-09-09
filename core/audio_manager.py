import os
import json
from core.audio_sinks import combine_speakers
from core.reset import unload_audio_modules
from core.speaker import BluetoothSpeaker
from core.pactl import pactl
from core.load_env import COMBINED_OUTPUT_SINK
from core.audio_calibrator import AudioCalibrator
 
## THIS VARIABLE STORES THE FILENAME USED TO PERSIST AND RESTORE SPEAKER STATE BETWEEN RUNS
# STATE FILE 
STATE_FILE = "speaker_state.json"
 
## THIS CLASS OWNS THE LIST OF ACTIVE BluetoothSpeaker OBJECTS, THE COMBINED SINK NAME, AND THEIR JSON PERSISTENCE
class AudioManager:
    ## THIS CONSTRUCTOR INITIALIZES AN EMPTY SPEAKER LIST, SETS THE COMBINED SINK NAME FROM ENV, THEN ATTEMPTS TO RESTORE SAVED STATE
    def __init__(self):
        ## THIS VARIABLE HOLDS THE LIST OF BluetoothSpeaker OBJECTS CURRENTLY MANAGED BY THIS INSTANCE
        self.speakers = []
        ## THIS VARIABLE STORES THE NAME OF THE COMBINED OUTPUT SINK, DEFAULTED FROM THE .env CONFIG
        self.combined_sink_name = COMBINED_OUTPUT_SINK
        self.restore_state()
 
    def persist_state(self):
        ## THIS VARIABLE HOLDS THE DICTIONARY THAT WILL BE SERIALIZED TO JSON, BUILT FROM THE CURRENT SINK NAME AND SPEAKER LIST
        data = {
            "combined_sink_name": self.combined_sink_name,
            "speakers": [spk.to_dict() for spk in self.speakers]
        }
        with open(STATE_FILE, "w") as f:
            json.dump(data, f, indent=4)
        print("Speaker configuration saved to disk.")
 
    ## THIS METHOD LOADS A PREVIOUSLY SAVED STATE FILE, IF ONE EXISTS, AND REBUILDS THE COMBINED SINK NAME AND SPEAKER LIST FROM IT
    def restore_state(self):
        if not os.path.exists(STATE_FILE):
            return False
 
        try:
            with open(STATE_FILE, "r") as f:
                ## THIS VARIABLE HOLDS THE RAW DICTIONARY PARSED FROM THE STATE FILE'S JSON CONTENT
                data = json.load(f)
            self.combined_sink_name = data.get("combined_sink_name", f"{COMBINED_OUTPUT_SINK}")
            self.speakers = [BluetoothSpeaker.from_dict(d) for d in data.get("speakers", [])]
            print(f"Loaded {len(self.speakers)} speakers from {STATE_FILE}")
            return True
        except Exception as e:
            print(f"Failed to load state: {e}")
            return False
 
    ## THIS METHOD CLAMPS AND APPLIES A NEW MASTER VOLUME LEVEL TO THE COMBINED SINK VIA PACTL
    def set_master_volume(self, level: int):
        level = max(0, min(100, level))
        pactl(f"set-sink-volume {self.combined_sink_name} {level}%")
        print(f"Master volume set to {level}%")

    ## METHOD TO AUTO CALIBRATE SPEAKER LATENCY
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

        # Save updated latencies to JSON
        self.persist_state()

        print("\nCalibration Complete!")
        # print(results)

        print("\nUpdated speaker values:")
        for s in self.speakers:
            print(f" - {s.name}: {s.latency_ms}ms")

        return
    



