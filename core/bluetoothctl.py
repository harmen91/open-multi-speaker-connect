import subprocess
import threading
import queue
import time
import re
from core.load_env import CONTROLLER_INPUT, CONTROLLER_OUTPUT, INPUT_DEVICES
import core.load_env

def current_devices():
    return core.load_env.OUTPUT_DEVICES

# strip color codes from piped output
ANSI_ESCAPE_RE = re.compile(r'\x1b\[[0-9;]*m')
def strip_ansi(line: str) -> str:
    return ANSI_ESCAPE_RE.sub('', line)

# single call to bluetoothctl, wait for output, or terminate after a fixed timeout
def bluetoothctl_run(args, timeout=5):
    try:
        completed_process = subprocess.run(
            ["bluetoothctl"] + args.split(),
            timeout=timeout,
            capture_output=True,
            text=True,
            check=True
        )
        # print(completed_process)
        return completed_process

    except subprocess.CalledProcessError as exc:
        if exc.cmd[1] == "pair":
            print(f"ignore this error for now >>> pairing error output_device {exc.cmd[2]}")
        elif exc.cmd[1] == "scan":
            print(f"IGNORE THIS ERROR FOR NOW >>> SCAN ON/OFF TOGGLE ISSUE")
        else:
            print(
            f"Process failed because did not return a successful return code. "
            f"Returned {exc.returncode}\n{exc}"
        )
        print(exc)
        return exc

    except subprocess.TimeoutExpired as exc:
        print(f"Process times out.\n{exc}")
        return exc    

# select default bluetooth controller
def bluetoothctl_select_controller(controller):
    script=f"select {controller}\nagent on\ndefault-agent\n pairable on"
    proc = subprocess.run(
        ["bluetoothctl"], input=script, capture_output=True, text=True
    )
    return proc.stdout + proc.stderr

# bluetooth background scan process, fills scan_queue for duration --timeout
scan_queue = queue.Queue()
def bluetoothctl_scan_start():
    print("Starting background scan...")

    scan_process = subprocess.Popen(
        ["bluetoothctl", "--timeout", "300", "scan", "on"],
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    def read_output():
        for line in scan_process.stdout:
            line = line.rstrip()    
            clean = strip_ansi(line)   
            print(clean) # >>>>>>>>> disable this in the future <<<<<<<<<<<<
            scan_queue.put(clean)
    threading.Thread(target=read_output, daemon=True).start()

    return scan_process

# terminate any lingering bluetoothctl --timeout processes // use to stop the background scan process
def bluetoothctl_scan_stop():
    bluetoothctl_run("scan off")
    subprocess.run(["pkill", "-f", "bluetoothctl --timeout"])
    print("Terminated any lingering bluetoothctl background scan processes")

# remove device
def bluetoothctl_remove_device(mac, timeout=5):
    bluetoothctl_run(f"remove {mac}", timeout)

# remove all trusted, paired and connected bluetooth devices
def bluetoothctl_remove_devices():
    for mac in current_devices():
        bluetoothctl_run((f"remove {mac}"))

# check if a single device is trusted
def is_trusted(mac, verbose = False):
    timeout = 10
    trusted = mac in bluetoothctl_run("devices Trusted", timeout).stdout
    if trusted:
        if verbose:
            print(f"{mac} trusted")
    else:
        if verbose:
            print(f"{mac} not trusted")
        return False
    return True

# check if a single device is paired
def is_paired(mac, verbose = False):
    timeout = 10
    paired = mac in bluetoothctl_run("devices Paired", timeout).stdout
    if paired:
        if verbose:
            print(f"{mac} paired")
    else:
        if verbose:
            print(f"{mac} unpaired")
        return False
    return True

# check if a single device is connected
def is_connected(mac, verbose = False):
    timeout = 10
    connected = mac in bluetoothctl_run("devices Connected", timeout).stdout
    if connected:
        if verbose:
            print(f"{mac} connected")
    else:
        if verbose:
            print(f"{mac} disconnected")
        return False
    return True

# check if all devices are trusted
def all_trusted():
    timeout = 10
    trusted = bluetoothctl_run("devices Trusted", timeout).stdout    
    for mac in current_devices():
        if mac in trusted:
            continue
        else:
            return False
    return True

# check if all devices are connected, return list of connected devices from bluetoothctl devices connected output
def all_connected(verbose = True) -> (bool, list):
    timeout = 10
    connected = bluetoothctl_run("devices Connected", timeout).stdout
    list_connected = []
    
    for mac in current_devices():
        if mac in connected:
            if verbose:
                print(f"{mac} Connected")
            list_connected.append(mac)
        else:
            return False, list_connected
    return True, list_connected

# trust an individual device
def bluetoothctl_trust(mac):
    bluetoothctl_run(f"trust {mac}", timeout=10)

# pair an individual device
def bluetoothctl_pair(mac):
    bluetoothctl_run(f"pair {mac}", timeout=10)

# trust and pair all devices in output_devices 
def trust_and_pair_devices(devices):
    local_scan_lines = []

    while True:
        try:
            local_scan_lines.append(scan_queue.get_nowait())
        except queue.Empty:
            break

    for mac in current_devices():
        trusted = is_trusted(mac)
        paired = is_paired(mac)

        # if mac not paired > check if trusted
        max_pairing_attempts = 0
        while not paired and max_pairing_attempts < 10:
            
            # if mac not trusted > wait for mac to appear in local_scan_lines > trust
            max_trusting_attempts = 0
            while not trusted and max_trusting_attempts < 10:
                
                waited = 0
                restart_after = 10
                while not any(mac in line for line in local_scan_lines):
                    try:
                        line = scan_queue.get(timeout=1) # line becomes latest queue.get
                        local_scan_lines.append(line)
                        waited = 0 # device activity detected

                    except queue.Empty:
                        waited += 1
                        print(f"Waiting for {mac} to appear") # waiting for new entry in queue to appear

                        if waited >= restart_after:
                            print("Restarting Bluetooth scan...")

                            bluetoothctl_scan_stop()
                            bluetoothctl_run("power off")
                            time.sleep(2)
                            bluetoothctl_run("power on")
                            time.sleep(2)
                            bluetoothctl_scan_start()

                            waited = 0

                # broke out of inner while loop, mac appeared in local_scan_lines > attempting to trust
                max_trusting_attempts += 1
                print(f"Attempting to trust with {mac}. Trusting attempt: {max_trusting_attempts}")
                bluetoothctl_trust(mac)
                time.sleep(1)
                trusted  = is_trusted(mac)
            
            # broke out of the not-trusted while loop > attempting to pair
            max_pairing_attempts += 1
            print(f"Attempting to pair with {mac}. Pairing attempt: {max_pairing_attempts}")
            bluetoothctl_pair(mac)
            paired = is_paired(mac)
            # trying to connect right after pairing seems to improve connectivity with bose soundlink mini
            bluetoothctl_connect(mac)
            

# connect an individual device
def bluetoothctl_connect(mac):
    bluetoothctl_run(f"connect {mac}", timeout=10)

# connect all devices
def connect_devices(devices):
    trusted = all_trusted()
    connected, _ = all_connected()

    # check if all connected
    if not connected:
        print(f"Not all devices are connected, checking if Trusted.")
        # check if all trusted
        if trusted:
            print(f"All devices are trusted, attempting to connect all devices.")

            # all trusted and ready to connect each device
            for mac in current_devices():
                trusted = is_trusted(mac)
                connected = is_connected(mac)
                # attempt to connect to device up to max connecting attempts
                connecting_attempts = 0
                while trusted and not connected and connecting_attempts < 10:
                    time.sleep(1)
                    connecting_attempts += 1
                    print(f"Attempting to connect with {mac}. Connecting attempt: {connecting_attempts}")
                    bluetoothctl_connect(mac)
                    connected = is_connected(mac)


# final function call 
def bluetooth_connect_speakers(CONTROLLER_OUTPUT, devices=None):

    if devices is None:
        devices = core.load_env.OUTPUT_DEVICES

    if not all_connected()[0]:

        print("Turning on bluetooth..")
        bluetoothctl_run("power on")
        time.sleep(3)

        print(f"Setting default controller to: {CONTROLLER_OUTPUT}...")
        bluetoothctl_select_controller(CONTROLLER_OUTPUT) ## todo: check against bluetoothctl list to see if agent is already [default]
        time.sleep(1)

        print("Starting bluetoothctl scan background service...")
        print("Capturing all incoming bluetooth messages..")
        bluetoothctl_scan_start() 
        time.sleep(3)

        print("Attempting to trust and pair all devices..")
        trust_and_pair_devices(devices)
        time.sleep(1)

        print("Attempting to connect to all paired devices..")
        connect_devices(devices)

    return all_connected()