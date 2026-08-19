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

## Status

Core Bluetooth connection logic and sink identification are working.
Combined sink creation and per-speaker latency control are in active
development.
