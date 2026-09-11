import sys
import subprocess
import time
from core.pactl import pactl

try:
    import numpy as np
    import scipy.io.wavfile as wav
    from scipy.signal import chirp, correlate, windows
    import sounddevice as sd
except (ImportError, OSError) as e:
    print("\n[Error] Missing calibration dependencies!")
    print("Please install required libraries:")
    print("  1. System audio:  sudo apt install libportaudio2  (or equivalent)")
    print("  2. Python packages: pip install -r requirements.txt\n")
    sys.exit(1)


class AudioCalibrator:
    def __init__(
        self,
        speakers: list,
        sample_rate: int = 48000,
        chirp_file: str = "/tmp/calibration_chirp.wav",
    ):
        # Stores the list of BluetoothSpeaker instances to measure and calibrate
        self.speakers = speakers
        # Audio sample rate in Hz 
        self.sample_rate = sample_rate
        # Filesystem path where the generated chirp sound file will be saved
        self.chirp_file = chirp_file
        # Generates the test sound on init and holds its raw array in memory as a reference pattern
        self.ref_sig = self._generate_chirp()

    def _generate_chirp(self, duration: float = 0.1) -> np.ndarray:
        num_samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, num_samples, endpoint=False)

        # 1 kHz to 5 kHz sweep
        sig = chirp(t, f0=1000, f1=5000, t1=duration, method="linear").astype(
            np.float32
        )

        # Fade-in and fade-out over 5% of samples to prevent speaker pops
        sig *= windows.tukey(num_samples, alpha=0.1)

        wav.write(self.chirp_file, self.sample_rate, (sig * 32767).astype(np.int16))
        return sig

    def _measure_raw_latency(
        self, speaker, record_duration: float = 1.5
    ) -> float:
        # Total number of mic frames/samples to capture during the measurement window
        num_samples = int(self.sample_rate * record_duration)

        # 1. Asynchronously starts recording 1 channel (mono) from the default mic without blocking Python
        recording = sd.rec(
            num_samples,
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
        )
        # Pauses briefly to allow the audio hardware and PortAudio input ring buffer to fully spin up
        time.sleep(0.05)

        # 2. Plays the chirp WAV file directly to the speaker's PipeWire node ID, bypassing the combined sink
        subprocess.run(
            ["pw-play", "--volume", "1.0", "--target", speaker.sink_id, self.chirp_file],
            check=True,
        )

        # Blocks Python execution until the remaining 1.5s mic capture finishes
        sd.wait()

        # 3. Slides the reference chirp over the mic recording to calculate similarity at every offset (dot product)
        corr = correlate(recording.flatten(), self.ref_sig, mode="valid")
        # Finds the exact index where correlation peaked (the moment the mic heard the chirp)
        delay_samples = np.argmax(corr)

        # Converts sample index delay into milliseconds: (samples / samples_per_sec) * 1000
        return (delay_samples / self.sample_rate) * 1000

    def calibrate(self) -> dict:
        # Dictionary to store measured round-trip latencies: {speaker_name: latency_ms}
        raw_delays = {}

        # 1. Measure acoustic round-trip delay for each speaker individually
        for spk in self.speakers:
            raw_delays[spk.name] = self._measure_raw_latency(spk)
            # Brief pause to let room echoes and Bluetooth buffers settle before testing the next speaker
            time.sleep(0.2)

        # 2. Find the slowest speaker (the one with the largest delay); this becomes our baseline
        slowest_delay = max(raw_delays.values())

        results = {}
        # 3. Add artificial delay to faster speakers so their output lines up with the slowest one
        for spk in self.speakers:
            # Difference between slowest device and this device in milliseconds
            added_latency = int(round(slowest_delay - raw_delays[spk.name]))
            # Reconfigures the speaker's loopback module with the compensating delay
            spk.set_latency(added_latency)
            # Record measurement metadata for display or debugging
            results[spk.name] = {
                "measured_ms": raw_delays[spk.name],
                "applied_latency_ms": added_latency,
            }

        return results

#TODO
# Have an audio calibrator script run over a longer period of time, and take the std dev median (excluding extreme values) to get a more accurate initial calibration
# Ask user to confirm setting the calculated latency instead of applying immediatly