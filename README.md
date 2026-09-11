<img src="./screenshots/osmcv1.png">

**Status: work in progress, not stable.**

# Open Multi Speaker Connect

Open-source Linux software for connecting multiple Bluetooth speakers and using them as a single synchronized audio system.

The project uses BlueZ for Bluetooth, PipeWire for audio routing, and acoustic measurement to determine and compensate for differences in speaker latency.

Status: work in progress.

## Features

* Discover nearby Bluetooth devices
* Select and save the speakers to use
* Automatically trust, pair and connect speakers
* Connect multiple Bluetooth speakers through BlueZ
* Map Bluetooth devices to their PipeWire audio sinks
* Create one combined PipeWire output
* Automatically measure speaker latency with a microphone
* Automatically compensate for different speaker latencies
* Set latency manually per speaker
* Route a speaker as:

  * `STEREO`
  * `FL`
  * `FR`
* Control individual speaker volume
* Mute individual speakers
* Control master volume
* Persist speaker and PipeWire configuration
* Detect and repair missing or stale PipeWire modules
* Reset Bluetooth and PipeWire state from the TUI

## How it works

Each Bluetooth speaker has its own playback latency.

Simply sending the same audio stream to several Bluetooth sinks does not guarantee that the speakers will reproduce the sound simultaneously.

The project therefore creates a separate PipeWire path for each speaker:

```text
                         Combined sink
                              |
             +----------------+----------------+
             |                |                |
             v                v                v
       Speaker A path    Speaker B path    Speaker C path
             |                |                |
        null sink          null sink          null sink
             |                |                |
        loopback          loopback          loopback
             |                |                |
             v                v                v
       Bluetooth A       Bluetooth B       Bluetooth C
```

Each speaker has its own virtual null sink and loopback.

The loopback provides the per-speaker delay. The null sinks are then combined into a single `module-combine-sink`, which becomes the default audio output.

## Automatic latency calibration

The calibration system measures the actual acoustic delay of every connected speaker.

The process is:

1. Generate a known calibration chirp.
2. Record audio from the default microphone.
3. Play the chirp directly to one Bluetooth speaker with `pw-play`.
4. Locate the chirp in the microphone recording using signal correlation.
5. Repeat for every speaker.
6. Find the speaker with the greatest measured delay.
7. Use that speaker as the timing reference.
8. Add the required delay to every faster speaker.

The current calibration parameters are:

* Sample rate: 48 kHz
* Chirp duration: 100 ms
* Frequency sweep: 1 kHz to 5 kHz
* Window: Tukey
* Microphone recording: 1.5 seconds
* Correlation: SciPy `correlate`
* Playback: `pw-play`

The resulting compensation is applied to each speaker's PipeWire loopback.

The calibration measures the complete practical playback path rather than trying to infer latency from Bluetooth protocol information.

### Calibration requirements

A working microphone is required.

The microphone should be able to hear each speaker clearly during calibration. Speaker placement, room reflections and background noise can affect the measurement.

The current implementation performs one measurement per speaker. Repeated measurements and statistical filtering are planned improvements.

## Requirements

Linux with:

* BlueZ
* PipeWire
* `bluetoothctl`
* `pactl`
* `pw-play`
* `pw-link`
* Python 3
* A working microphone for automatic calibration

Python dependencies:

```text
numpy>=1.24.0
scipy>=1.10.0
sounddevice>=0.4.6
```

For Debian, Ubuntu and Raspberry Pi OS, PortAudio is also required:

```bash
sudo apt install libportaudio2
```

## Installation

Clone the repository:

```bash
git clone https://github.com/harmen91/open-multi-speaker-connect.git
cd open-multi-speaker-connect
```

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

Install the required system audio/Bluetooth packages for your Linux distribution.

## Configuration

The application currently uses a `.env` file for Bluetooth controller configuration and for compatibility as a fallback source of speaker addresses.

Example:

```text
CONTROLLER_OUTPUT=AA:BB:CC:DD:EE:FF
CONTROLLER_INPUT=AA:BB:CC:DD:EE:FF

COMBINED_OUTPUT_SINK=multi_speaker_sync

OUTPUT_DEVICE_SPEAKER_1=AA:BB:CC:DD:EE:FF
OUTPUT_DEVICE_SPEAKER_2=AA:BB:CC:DD:EE:FF

INPUT_DEVICE_PHONE=AA:BB:CC:DD:EE:FF
```

`COMBINED_OUTPUT_SINK` is the name given to the PipeWire combined sink.

Output devices can now normally be selected through the TUI. When `selected_devices.json` exists, it takes precedence over `OUTPUT_DEVICE_*` entries in `.env`. If it does not exist, the application falls back to the `.env` output-device entries.

## Running

Start the TUI with:

```bash
./tui.sh
```

or:

```bash
python3 main.py --tui
```

`tui.sh` is simply a convenience wrapper around the second command.

## TUI

The application is controlled through a curses-based terminal interface.

### Navigation

```text
Up / k       Move selection up
Down / j     Move selection down
Enter        Select
Esc          Back
Backspace    Back
Q            Quit
```

Blocking operations run in a worker thread. While one is running, the interface displays:

```text
[BUSY - PLEASE WAIT]
```

Core output is routed into the TUI log pane so that Bluetooth, PipeWire and application status messages remain visible while operations run.

## Audio Setup

The main setup menu contains:

```text
Audio Setup
├── Scan & Select Bluetooth Devices
├── Auto connect & combine
└── Auto calibrate speakers
```

### Scan & Select Bluetooth Devices

The scanner:

1. Loads known Bluetooth devices.
2. Clears stale scan results.
3. Powers the Bluetooth controller off and on.
4. Starts discovery.
5. Collects discovered devices.
6. Displays device name and MAC address.
7. Allows devices to be selected.
8. Saves the selection to `selected_devices.json`.

Scanning runs in the background while the device-selection menu remains interactive.

The device list looks conceptually like:

```text
[x] Living Room Speaker (AA:BB:CC:DD:EE:FF)
[ ] Portable Speaker   (11:22:33:44:55:66)

[ Save & Exit ]
```

Press Enter or Space to toggle a device.

### Auto connect & combine

This operation:

1. Connects the selected Bluetooth speakers.
2. Waits for their real PipeWire sinks to appear.
3. Stops the Bluetooth scan.
4. Creates the per-speaker PipeWire audio paths.
5. Creates the combined sink.
6. Sets the combined sink as the default output.
7. Saves the resulting speaker configuration.

The application deliberately waits for PipeWire sinks before stopping the Bluetooth scan. This avoids a race where Bluetooth reports a connection before PipeWire has created the corresponding audio sink.

The operation only creates the combined sink when all requested speakers connected successfully.

### Auto calibrate speakers

Runs the acoustic calibration described above.

Calibration should be performed after the speakers are connected and the combined audio system has been created.

## Speaker controls

Once speakers are active, the TUI creates a control section for each speaker.

```text
Speaker controls
├── Speaker: <name>
│   ├── Set Latency (ms)
│   ├── Set Channel (STEREO, FL, FR)
│   ├── Set Volume (0-100)
│   ├── Volume Up 10%
│   ├── Volume Down 10%
│   ├── Mute On
│   └── Mute Off
```

### Latency

`Set Latency (ms)` directly changes the additional PipeWire delay applied to that speaker.

The speaker is muted while its loopback module is replaced, preventing audible artifacts during the change. The new loopback is then allowed to become active before the speaker is unmuted.

### Channel routing

Each speaker can operate in one of three modes:

```text
STEREO
FL
FR
```

`STEREO` sends left to left and right to right.

`FL` sends the front-left channel to both speaker channels.

`FR` sends the front-right channel to both speaker channels.

Routing is implemented using `pw-link`.

This allows the same physical speaker system to be used for stereo playback or as part of a multi-channel layout.

### Volume

Individual speaker volume can be set from 0 to 100.

The TUI also provides:

```text
Volume Up 10%
Volume Down 10%
Mute On
Mute Off
```

The TUI displays a simple volume bar in the log pane after volume changes.

## Master volume

The TUI provides:

```text
Master Volume (0-100)
Master Volume Up 10%
Master Volume Down 10%
```

Master volume is applied to the combined PipeWire sink rather than individually changing every Bluetooth speaker.

## State persistence

The application stores speaker state in:

```text
speaker_state.json
```

Saved information includes:

* Bluetooth MAC address
* Speaker name
* PipeWire sink ID
* Latency
* Null-sink module ID
* Loopback module ID
* Channel assignment

The state is restored when the application starts.

## PipeWire state reconciliation

PipeWire module IDs are not permanent, so the application does not blindly trust the IDs stored in `speaker_state.json`.

On reconciliation, each speaker's saved null-sink and loopback modules are checked against the currently running PipeWire modules.

If a module is missing or no longer matches its expected configuration, only the affected speaker path is repaired.

If necessary, the combined sink is then rebuilt using the current speaker null sinks and restored as the default output.

This allows the application to recover from situations where PipeWire has restarted or previously created modules have disappeared.

## System Reset

The TUI provides:

```text
System Reset
├── Full Factory Reset
├── Unload All Created Audio Sinks
├── Unpair Bluetooth Devices
├── Delete Speaker State JSON File
└── Delete Selected Devices JSON File
```

### Full Factory Reset

Removes the currently configured Bluetooth devices, unloads the project's PipeWire modules and deletes the saved selected-device configuration.

### Unload All Created Audio Sinks

Removes the project's:

* `module-null-sink`
* `module-loopback`
* `module-combine-sink`

modules.

This is useful when the PipeWire state needs to be rebuilt from scratch.

### Unpair Bluetooth Devices

Removes the currently configured Bluetooth devices through `bluetoothctl`.

### Delete Speaker State JSON File

Deletes:

```text
speaker_state.json
```

### Delete Selected Devices JSON File

Deletes:

```text
selected_devices.json
```

The next device scan can then create a new selection.

## Architecture

```text
open-multi-speaker-connect/
│
├── main.py
│
├── core/
│   ├── audio_calibrator.py
│   ├── audio_manager.py
│   ├── audio_sinks.py
│   ├── bluetooth_scanner.py
│   ├── bluetoothctl.py
│   ├── connect_and_combine.py
│   ├── load_env.py
│   ├── pactl.py
│   ├── pwlink.py
│   ├── reset.py
│   └── speaker.py
│
├── interfaces/
│   └── tui/
│       ├── device_menu.py
│       ├── engine.py
│       └── presenter.py
│
├── screenshots/
│
├── requirements.txt
├── selected_devices.json
├── tui.sh
├── web.sh
└── README.md
```

### Core

`bluetoothctl.py`

Low-level Bluetooth controller interaction using `bluetoothctl`. Handles controller selection, scanning, pairing, trusting, connecting and removing devices.

`bluetooth_scanner.py`

Provides the device discovery and selection layer and persists the selected Bluetooth addresses.

`connect_and_combine.py`

Coordinates the complete connection workflow from Bluetooth connection through PipeWire sink creation and combined-sink construction.

`audio_sinks.py`

Maps Bluetooth devices to PipeWire sinks and creates the null-sink, loopback and combined-sink topology.

`speaker.py`

Represents an individual Bluetooth speaker and owns its PipeWire null sink, loopback, latency, volume, mute and channel-routing state.

`audio_manager.py`

Manages the speaker collection, state persistence, PipeWire reconciliation, master volume and calibration.

`audio_calibrator.py`

Performs acoustic latency measurement and applies per-speaker compensation.

`pactl.py`

Wrapper around `pactl` for PipeWire/PulseAudio operations.

`pwlink.py`

Wrapper around `pw-link` for explicit PipeWire channel connections.

`reset.py`

Handles cleanup and factory-reset operations.

`load_env.py`

Loads `.env` configuration and resolves the active speaker list from `selected_devices.json` or `.env`.

### TUI

`interfaces/tui/engine.py`

Generic curses menu engine. It handles navigation, prompts, background actions, busy state and log output.

`interfaces/tui/presenter.py`

Builds the application's actual menu structure and connects menu actions to the core functionality.

`interfaces/tui/device_menu.py`

Implements the Bluetooth discovery and device-selection screen.

## Web interface

A web entry point exists:

```bash
./web.sh
```

or:

```bash
python3 main.py --web
```

The web interface is not implemented yet.

## Limitations

The project is still under development.

Current limitations include:

* Bluetooth reconnection after a speaker disappears is not yet fully robust.
* Acoustic calibration currently uses a single measurement per speaker.
* Calibration accuracy depends on microphone placement, room acoustics and background noise.
* PipeWire and Bluetooth behavior can vary between Linux distributions and hardware.
* The web interface is not implemented.
* The combined-sink health check is not a complete validation of the underlying Bluetooth speaker state.

## Project status

The core workflow is operational:

```text
Bluetooth discovery
        ↓
Speaker selection
        ↓
Bluetooth connection
        ↓
PipeWire sink detection
        ↓
Per-speaker PipeWire paths
        ↓
Combined sink
        ↓
Acoustic latency calibration
        ↓
Per-speaker latency compensation
        ↓
Synchronized multi-speaker output
```

The project remains experimental and is intended primarily for development, testing and real-world experimentation with multi-speaker Bluetooth audio on Linux.

## License

MIT License
