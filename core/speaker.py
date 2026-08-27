import time
from core.pactl import pactl

# BLUETOOTH SPEAKER CLASS
class BluetoothSpeaker:
    def __init__(self, mac, name, sink_id, latency_ms=0, loopback_module_id=None, null_sink_module_id=None, volume=100):
        self.mac = mac
        self.name = name
        self.sink_id = sink_id
        self.latency_ms = latency_ms
        self.loopback_module_id = loopback_module_id
        self.null_sink_name = None
        self.null_sink_module_id = null_sink_module_id
        self.loopback_sink_name = None
        self.loopback_sink_module_id = None
        self.volume = volume
        self.ismute = None

    def to_dict(self):
        return {
            "mac": self.mac,
            "name": self.name,
            "sink_id": self.sink_id,
            "latency_ms": self.latency_ms,
            "null_sink_module_id": self.null_sink_module_id,
            "loopback_module_id": self.loopback_module_id,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            mac=data["mac"],
            name=data["name"],
            sink_id=data["sink_id"],
            latency_ms=data.get("latency_ms", 0),
            loopback_module_id=data.get("loopback_module_id"),
            null_sink_module_id=data.get("null_sink_module_id"),
        )
    
    def create_null_sink(self):
        self.null_sink_name = self.name + "_null_delayed"
        self.null_sink_module_id = pactl(f"load-module module-null-sink sink_name={self.null_sink_name}")

    def create_loopback(self):
        self.loopback_name = self.name + "_loopback"
        self.loopback_module_id = pactl(f"load-module module-loopback source={self.null_sink_name}.monitor sink={self.name} latency_msec={self.latency_ms}")
    
    def get_null_sink_name(self):
        return self.null_sink_name 
    
    def set_volume(self, level: int):
        self.volume = max(0, min(100, level))
        pactl(f"set-sink-volume {self.name} {self.volume}%")
        return 

    def volume_up(self):
        return self.set_volume(self.volume + 10)  

    def volume_down(self):
        return self.set_volume(self.volume - 10) 
 

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

    def _wait_for_loopback_ready(self, module_id: str, timeout: float = 2.0, interval: float = 0.02) -> bool:
        """Poll pactl list sink-inputs until the loopback module has actually wired a sink-input."""
        target = module_id.strip()
        deadline = time.time() + timeout
        while time.time() < deadline:
            out = pactl("list sink-inputs")
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

    def __repr__(self):
        return f"BluetoothSpeaker(name={self.name!r}, mac={self.mac!r}, sink_id={self.sink_id!r}, null_sink_name={self.null_sink_name}, null_sink_module_id={self.null_sink_module_id})"
