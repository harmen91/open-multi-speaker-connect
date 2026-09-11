import json
import os

# loads simple KEY=VALUE settings from a file (default ./.env), skipping blank lines and comments
# values are kept as raw strings; only the first '=' splits key from value so values may contain '='
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

# parse the .env file once at import time — everything below is read from it
env = load_settings()

# the mac addresses of the two bluetooth controllers: one for audio output, one for capturing input
CONTROLLER_OUTPUT = env["CONTROLLER_OUTPUT"]
CONTROLLER_INPUT = env["CONTROLLER_INPUT"]

# name of the combined sink, with spaces stripped since pactl/pipewire names can't contain them
COMBINED_OUTPUT_SINK = env["COMBINED_OUTPUT_SINK"].replace(" ", "")

# collect every INPUT_DEVICE<N>= entry from the .env into a single list of macs
# currently not in use
INPUT_DEVICES = [v for k, v in env.items() if k.startswith("INPUT_DEVICE")]

# load output devices from selected_devices.json if it exists, otherwise fall back to .env
DEVICES_JSON_PATH = "./selected_devices.json"

# prefer the saved device selection (selected_devices.json, stored as a dict keyed by mac);
# if it doesn't exist, fall back to collecting all OUTPUT_DEVICE_ entries from the .env
def get_output_devices():
    if os.path.isfile(DEVICES_JSON_PATH):
        with open(DEVICES_JSON_PATH, "r", encoding="utf-8") as f:
            return list(json.load(f).keys())

    return [v for k, v in env.items() if k.startswith("OUTPUT_DEVICE")]

# resolved at import time: the mac addresses of all speakers this session should drive
OUTPUT_DEVICES = get_output_devices()