# Multi-Speaker Bluetooth Sync (WIP)

**Status: work in progress, not stable.**

CLI tool for Linux (PipeWire + BlueZ) that connects multiple Bluetooth
speakers at once and combines them into a single synced audio output.

## What it does

- Automates `bluetoothctl` trust/pair/connect for a set of known speakers
- Retries connections until they succeed (Bluetooth pairing is flaky)
- Maps connected devices to their PipeWire sink names via `pactl`
- Builds a combined sink from all connected speakers
- Adds per-speaker latency calibration to correct sync drift between
  devices (e.g. wired output vs Bluetooth output)

## Why

Bluetooth speakers introduce inconsistent latency compared to wired
output. Combining multiple speakers into one sink without correction
causes audible timing drift. This project aims to automate connection
setup and let each speaker's delay be tuned individually so everything
plays in sync.

## Requirements

- Linux with PipeWire and BlueZ
- Python 3
- Bluetooth speaker MAC addresses configured in a `.env` file

## Configuration

This project currently requires manually looking up the MAC addresses
of your Bluetooth hardware controllers and speakers, and storing them
in a `.env` file in the project root.

To find your controller MAC addresses:

    bluetoothctl list

To find a speaker's MAC address, put it in pairing mode and run:

    bluetoothctl scan on

Create a `.env` file in the project root with the following layout:

    # Controller used for audio output (speakers) and input (phone)
    CONTROLLER_OUTPUT=AA:BB:CC:DD:EE:FF
    CONTROLLER_INPUT=AA:BB:CC:DD:EE:FF

    # Speakers
    DIY_SPEAKER_1=AA:BB:CC:DD:EE:FF
    DIY_SPEAKER_2=AA:BB:CC:DD:EE:FF
    BOSE_SOUNDLINK=AA:BB:CC:DD:EE:FF

    # Phone (used as audio input source)
    PHONE_IPHONE=AA:BB:CC:DD:EE:FF

Add or remove entries to match your own hardware. Unused lines can be
commented out with `#` rather than deleted, which is useful when
switching between different machines or hardware setups.

There is currently no automated device discovery — all MAC addresses
must be identified and entered manually before running the tool.

## Status

Core Bluetooth connection logic and sink identification are working.
Combined sink creation and per-speaker latency control are in active
development.
