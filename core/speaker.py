import time
from core.pactl import pactl
from core.pwlink import pwlink
from core.load_env import COMBINED_OUTPUT_SINK

## THIS CLASS REPRESENTS A SINGLE BLUETOOTH SPEAKER AND OWNS ITS PIPEWIRE NULL-SINK, LOOPBACK, LATENCY, VOLUME AND MUTE STATE
# BLUETOOTH SPEAKER CLASS
class BluetoothSpeaker:
    ## THIS CONSTRUCTOR INITIALIZES THE SPEAKER'S IDENTITY (MAC, NAME, SINK ID) AND ITS DEFAULT LATENCY, MODULE ID AND VOLUME STATE
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

    ## THIS METHOD REBUILDS A BluetoothSpeaker OBJECT FROM A PREVIOUSLY SAVED STATE DICTIONARY
    ## THIS DECORATOR MARKS from_dict AS AN ALTERNATE CONSTRUCTOR THAT BUILDS A SPEAKER FROM THE CLASS ITSELF RATHER THAN AN INSTANCE
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

    ## THIS METHOD LOADS A module-null-sink FOR THIS SPEAKER AND RECORDS ITS NAME AND PACTL MODULE ID
    def create_null_sink(self):
        self.null_sink_name = self.name + "_null_delayed"
        self.null_sink_module_id = pactl(f"load-module module-null-sink sink_name={self.null_sink_name}")

    ## THIS METHOD LOADS A module-loopback BRIDGING THIS SPEAKER'S NULL SINK MONITOR TO ITS REAL SINK, APPLYING THE CURRENT LATENCY
    def create_loopback(self):
        self.loopback_module_id = pactl(f"load-module module-loopback source={self.null_sink_name}.monitor sink={self.name} latency_msec={self.latency_ms}")

    ## THIS METHOD RETURNS THIS SPEAKER'S NULL SINK NAME FOR USE WHEN BUILDING THE COMBINED SINK'S SLAVE LIST
    def get_null_sink_name(self):
        return self.null_sink_name 

    def set_channel(self, channel):
        channel = channel.upper()

        if channel not in ("FL", "FR", "STEREO"):
            raise ValueError("channel must be 'FL', 'FR', or 'STEREO'")

        return channel

    # METHOD FOR UPDATING AUDIO CHANNEL FRONT RIGHT, FRONT LEFT, STEREO USING PIPEWIRE pw-link
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

                pwlink(["-d", source, destination]) #disconnect channel with pw-link -d

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
            
            pwlink([source, destination]) #connect channel with pw-link

        self.channel = new_channel

    ## THIS METHOD CLAMPS AND APPLIES A NEW VOLUME LEVEL TO THIS SPEAKER'S SINK VIA PACTL
    def set_volume(self, level: int):
        self.volume = max(0, min(100, level))
        pactl(f"set-sink-volume {self.name} {self.volume}%")
        return 

    ## THIS METHOD RAISES THIS SPEAKER'S VOLUME BY 10%, CLAMPED TO 100%
    def volume_up(self):
        return self.set_volume(self.volume + 10)  

    ## THIS METHOD LOWERS THIS SPEAKER'S VOLUME BY 10%, CLAMPED TO 0%
    def volume_down(self):
        return self.set_volume(self.volume - 10) 
 
    ## THIS METHOD SAFELY RETUNES THIS SPEAKER'S LATENCY BY MUTING, SWAPPING THE LOOPBACK MODULE, WAITING FOR IT TO BE LIVE, THEN UNMUTING
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

    ## THIS METHOD POLLS `pactl list sink-inputs` UNTIL THE GIVEN LOOPBACK MODULE HAS AN ACTIVE SINK-INPUT, OR TIMES OUT
    def _wait_for_loopback_ready(self, module_id: str, timeout: float = 2.0, interval: float = 0.02) -> bool:
        """Poll pactl list sink-inputs until the loopback module has actually wired a sink-input."""
        ## THIS VARIABLE STORES THE STRIPPED MODULE ID WE'RE WAITING TO SEE WIRED UP AS A SINK-INPUT
        target = module_id.strip()
        ## THIS VARIABLE MARKS THE ABSOLUTE TIME AT WHICH POLLING SHOULD GIVE UP AND RETURN FALSE
        deadline = time.time() + timeout
        while time.time() < deadline:
            out = pactl("list sink-inputs")
            ## THESE VARIABLES TRACK THE MODULE ID AND DRIVER OF THE SINK-INPUT BLOCK CURRENTLY BEING PARSED
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

   ## THIS METHOD RETURNS A DEBUG-FRIENDLY STRING REPRESENTATION OF THE SPEAKER'S KEY IDENTIFYING FIELDS
    def __repr__(self):
        return f"BluetoothSpeaker(name={self.name!r}, mac={self.mac!r}, sink_id={self.sink_id!r}, null_sink_name={self.null_sink_name}, null_sink_module_id={self.null_sink_module_id})"
