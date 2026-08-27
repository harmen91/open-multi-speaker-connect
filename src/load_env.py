def load_env(path="./.env"):
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env

env = load_env()

# BLUETOOTH HARDWARE MAC FOR AUDIO OUTPUT (SPEAKER DEVICES)
CONTROLLER_OUTPUT = env["CONTROLLER_OUTPUT"]
# BLUETOOTH HARDWARE MAC FOR AUDIO INPUT (PHONE, COMPUTER, AUDIO STREAM, ETC)
# USEFULL FOR HAVING TWO SEPERATE BLUETOOTH CONTROLERS HANDLE INCOMING AND OUTGOING 
# BLUETOOTH STREAMS FOR IMPROVED PERFORMANCE AND REDUCED LATENCY
CONTROLLER_INPUT = env["CONTROLLER_INPUT"]

# STORED MAC ADDRESSES OF OUTPUT DEVICES IN ENV
OUTPUT_DEVICES = [v for k, v in env.items() if k.startswith("OUTPUT_DEVICE")] 

# STORED MAC ADDRESSES OF INPUT DEVICES IN ENV
INPUT_DEVICES = [v for k, v in env.items() if k.startswith("INPUT_DEVICE")] 

COMBINED_OUTPUT_SINK = env["COMBINED_OUTPUT_SINK"].replace(" ", "")