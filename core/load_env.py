import json
import os


def load_settings(path="./.env"):
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


env = load_settings()

CONTROLLER_OUTPUT = env["CONTROLLER_OUTPUT"]
CONTROLLER_INPUT = env["CONTROLLER_INPUT"]
COMBINED_OUTPUT_SINK = env["COMBINED_OUTPUT_SINK"].replace(" ", "")

INPUT_DEVICES = [v for k, v in env.items() if k.startswith("INPUT_DEVICE")]

# Load from devices.json if it exists, otherwise fall back to .env
DEVICES_JSON_PATH = "./selected_devices.json"

if os.path.isfile(DEVICES_JSON_PATH):
    with open(DEVICES_JSON_PATH, "r", encoding="utf-8") as f:
        devices_data = json.load(f)
        # Assuming keys are MAC addresses: {"AA:BB:CC:DD:EE:FF": "Device Name"}
        OUTPUT_DEVICES = list(devices_data.keys())
else:
    OUTPUT_DEVICES = [v for k, v in env.items() if k.startswith("OUTPUT_DEVICE")]