### TIPS FOR ARCHITECTURE

Separating your UI layer from your core business logic is a fundamental software design principle called Separation of Concerns (often implemented via the Controller/Service Pattern or Hexagonal Architecture).

Here is how you organize your project structure so the exact same logic can power a Curses TUI, a REST/WebSocket Web App (e.g., FastAPI/Flask), or a CLI:

## Recommended Folder Structure

```
open_speaker_connect/
│
├── core/                       # 1. PURE BUSINESS LOGIC (No Curses, No Web code)
│   ├── __init__.py
│   ├── speaker.py              # Speaker entity & hardware commands
│   ├── bluetooth.py            # BT scanning / pairing logic
│   └── service.py              # High-level controller & app_config definitions
│
├── interfaces/                 # 2. PRESENTATION LAYERS (Interchangeable UIs)
│   ├── tui/                    # Terminal UI
│   │   ├── __init__.py
│   │   └── engine.py           # Your current curses Menu/Window code
│   └── web/                    # Future Web UI
│       ├── __init__.py
│       └── app.py              # FastAPI / Flask router consuming core/
│
├── main_tui.py                 # Launches the TUI
└── main_web.py                 # Launches the Web App
```

## How It Works Across Both Interfaces
# 1. In core/service.py (Universal Configuration)

Define your backend operations and expose a standard schema/dictionary:

```
# core/service.py
from core.speaker import SpeakerController
from core.bluetooth import BluetoothManager

class AudioService:
    def __init__(self):
        self.speaker = SpeakerController()
        self.bt = BluetoothManager()

    def get_actions(self):
        """Standard action registry usable by TUI, Web, or CLI."""
        return {
            "System Check": self.speaker.system_check,
            "Scan Bluetooth": self.bt.scan,
            "Audio Controls": {
                "Set Volume": self.speaker.set_volume,
                "Volume Up": self.speaker.volume_up,
                "Volume Down": self.speaker.volume_down,
            },
        }
```

# 2. In main_tui.py (TUI Interface)

```
# main_tui.py
from core.service import AudioService
from interfaces.tui.engine import start_app

if __name__ == "__main__":
    service = AudioService()
    start_app(title="OPEN SPEAKER CONNECT", menu_config=service.get_actions())
```

# 3. In main_web.py (Future Web App with FastAPI/Flask)

Because your actions are standard Python functions with type hints (level: int, confirm: bool), a web framework can automatically map them to JSON endpoints:

```
# main_web.py
from fastapi import FastAPI
from core.service import AudioService

app = FastAPI()
service = AudioService()

@app.post("/api/volume")
def set_volume(level: int):
    # Same exact function called by the TUI!
    return {"result": service.speaker.set_volume(level)}

@app.post("/api/scan")
def scan_devices():
    return {"result": service.bt.scan()}
```

## Key Rule for Core Logic:

Never import curses inside your core/ files. Have core/ functions accept normal arguments and return normal strings or data objects.
