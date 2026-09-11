import time
from core.pactl import pactl
from core.pwlink import pwlink
from core.load_env import COMBINED_OUTPUT_SINK

# this class represents a single bluetooth speaker and owns its pipewire null-sink, loopback, latency, volume and mute state
# bluetooth speaker class
class BluetoothSpeaker:
    # this constructor initializes the speaker's identity (mac, name, sink id) and its default latency, module id and volume state
    def __init__(self, mac, name, sink_id, latency_ms=0, loopback_module_id=None, null_sink_module_id=None, volume=100, 
        channel="STEREO",):
        self.mac = mac
        self.name = name
        self.sink_id = sink_id
        self.latency_ms = latency_ms
        self.loopback_module_id = loopback_module_id
        self.null_sink_name = None
        self.null_sink_module_id = null_sink_module_id
         
        self.volume = volume
        self.ismute = None
        self.channel = channel

    def to_dict(self):
        return {
            "mac": self.mac,
            "name": self.name,
            "sink_id": self.sink_id,
            "latency_ms": self.latency_ms,
            "null_sink_module_id": self.null_sink_module_id,
            "loopback_module_id": self.loopback_module_id,
            "channel": self.channel,
        }

    # rebuilds a BluetoothSpeaker object from a previously saved state dictionary
    # this decorator marks from_dict as an alternate constructor that builds a speaker from the class itself rather than an instance
    @classmethod
    def from_dict(cls, data):
        return cls(
            mac=data["mac"],
            name=data["name"],
            sink_id=data["sink_id"],
            latency_ms=data.get("latency_ms", 0),
            loopback_module_id=data.get("loopback_module_id"),
            null_sink_module_id=data.get("null_sink_module_id"),
            channel=data.get("channel", "STEREO"),
        )

    # loads a module-null-sink for this speaker and records its name and pactl module id
    def create_null_sink(self):
        self.null_sink_name = self.name + "_null_delayed"
        self.null_sink_module_id = pactl(f"load-module module-null-sink sink_name={self.null_sink_name}")

    # loads a module-loopback bridging this speaker's null sink monitor to its real sink, applying the current latency
    def create_loopback(self):
        self.loopback_module_id = pactl(f"load-module module-loopback source={self.null_sink_name}.monitor sink={self.name} latency_msec={self.latency_ms}")

    # returns this speaker's null sink name for use when building the combined sink's slave list
    def get_null_sink_name(self):
        return self.null_sink_name 

    # checks if this speaker's null-sink module id is still a live, matching module-null-sink
    def _null_sink_ok(self, live_modules: dict) -> bool:
        self.null_sink_name = self.name + "_null_delayed"  # deterministic — not persisted, always recomputed here
        entry = live_modules.get(str(self.null_sink_module_id).strip()) if self.null_sink_module_id else None
        return bool(entry) and entry["name"] == "module-null-sink" and f"sink_name={self.null_sink_name}" in entry["argument"]

    # checks if this speaker's loopback module id is still a live, matching module-loopback
    def _loopback_ok(self, live_modules: dict) -> bool:
        entry = live_modules.get(str(self.loopback_module_id).strip()) if self.loopback_module_id else None
        expected_source = f"source={self.null_sink_name}.monitor"
        expected_sink = f"sink={self.name}"
        return bool(entry) and entry["name"] == "module-loopback" and expected_source in entry["argument"] and expected_sink in entry["argument"]

    # returns whether both of this speaker's modules are still valid, without changing anything
    def verify_alive(self, live_modules: dict) -> bool:
        return self._null_sink_ok(live_modules) and self._loopback_ok(live_modules)

    # recreates only whichever part (null-sink and/or loopback) failed verification — other speakers are untouched
    def repair(self, live_modules: dict):
        if not self._null_sink_ok(live_modules):
            self.create_null_sink()
            time.sleep(0.3)
        if not self._loopback_ok(live_modules):
            self.create_loopback()

    def set_channel(self, channel):
        channel = channel.upper()

        if channel not in ("FL", "FR", "STEREO"):
            raise ValueError("channel must be 'FL', 'FR', or 'STEREO'")

        return channel

    # method for updating audio channel (front right, front left, stereo) using pipewire pw-link
    def update_channel(self, channel):
        combined_sink_name = COMBINED_OUTPUT_SINK
        new_channel = self.set_channel(channel)

        # Remove all possible links.
        for source_channel in ("FL", "FR"):
            for destination_channel in ("FL", "FR"):
                source = (
                    f"output.{combined_sink_name}_{self.name}_null_delayed:"
                    f"output_{source_channel}"
                )
                destination = (
                    f"{self.name}_null_delayed:playback_{destination_channel}"
                )

                pwlink(["-d", source, destination]) # disconnect channel with pw-link -d

        if new_channel == "STEREO":
            routes = [("FL", "FL"), ("FR", "FR")]
        else: 
            routes = [
                (new_channel, "FL"),
                (new_channel, "FR"),
            ]

        for source_channel, destination_channel in routes:
            source = (
                f"output.{combined_sink_name}_{self.name}_null_delayed:"
                f"output_{source_channel}"
            )
            destination = (
                f"{self.name}_null_delayed:playback_{destination_channel}"
            )
            
            pwlink([source, destination]) # connect channel with pw-link

        self.channel = new_channel

    # clamps and applies a new volume level to this speaker's sink via pactl
    def set_volume(self, level: int):
        self.volume = max(0, min(100, level))
        pactl(f"set-sink-volume {self.name} {self.volume}%")
        return 

    # raises this speaker's volume by 10%, clamped to 100%
    def volume_up(self):
        return self.set_volume(self.volume + 10)  

    # lowers this speaker's volume by 10%, clamped to 0%
    def volume_down(self):
        return self.set_volume(self.volume - 10) 
 
    # safely retunes this speaker's latency by muting, swapping the loopback module, waiting for it to be live, then unmuting
    def set_latency(self, latency_ms: int):
        self.latency_ms = latency_ms

        # 1. Hard mute (state-safe, not toggle)
        pactl(f"set-sink-mute {self.name} 1")

        # 2. Tear down old loopback
        if self.loopback_module_id:
            pactl(f"unload-module {self.loopback_module_id.strip()}")

        # 3. Load new loopback
        out = pactl(
            f"load-module module-loopback "
            f"source={self.null_sink_name}.monitor "
            f"sink={self.name} "
            f"latency_msec={self.latency_ms}"
        )
        self.loopback_module_id = out.strip()

        # 4. POLL: wait until the loopback's sink-input is actually live
        self._wait_for_loopback_ready(self.loopback_module_id)

        # 5. NOW unmute — the audio path is confirmed ready
        pactl(f"set-sink-mute {self.name} 0")

        return f"Updated {self.name} latency to {latency_ms}ms"

    def mute_on(self):
        pactl(f"set-sink-mute {self.name} 1") 

    def mute_off(self):
        pactl(f"set-sink-mute {self.name} 0") 

    # polls `pactl list sink-inputs` until the given loopback module has an active sink-input, or times out
    def _wait_for_loopback_ready(self, module_id: str, timeout: float = 2.0, interval: float = 0.02) -> bool:
        """Poll pactl list sink-inputs until the loopback module has actually wired a sink-input."""
        ## stripped module id we're waiting to see wired up as a sink-input
        target = module_id.strip()
        ## absolute time at which polling gives up and returns False
        deadline = time.time() + timeout
        while time.time() < deadline:
            out = pactl("list sink-inputs")
            ## track the module id and driver of the sink-input block currently being parsed
            current_module = None
            current_driver = None
            for line in out.splitlines():
                if line.strip().startswith("Sink Input #"):
                    current_module = None
                    current_driver = None
                elif "Owner Module:" in line:
                    current_module = line.split(":", 1)[1].strip()
                elif "Driver:" in line:
                    current_driver = line.split(":", 1)[1].strip()
                    if current_driver == "module-loopback.c" and current_module == target:
                        return True
            time.sleep(interval)
        return False

   # debug-friendly string representation of the speaker's key identifying fields
    def __repr__(self):
        return f"BluetoothSpeaker(name={self.name!r}, mac={self.mac!r}, sink_id={self.sink_id!r}, null_sink_name={self.null_sink_name}, null_sink_module_id={self.null_sink_module_id})"