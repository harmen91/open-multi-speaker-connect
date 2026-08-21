import subprocess
import threading
import time
from load_env import env

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

#SINGLE CALL TO BLUETOOTHCTL, WAIT FOR OUTPUT, OR TERMINATE AFTER FIXED TIMEROUT
def bt_bluetoothctl(args, timeout=5):
    try:
        timeout = timeout
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
            print(f"IGNORE THIS ERROR FOR NOW >>> PAIRING ERROR OUTPUT_DEVICE {exc.cmd[2]}")
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

def bt_select_default_controller(controller):
    script=f"select {controller}\nagent on\ndefault-agent"
    proc = subprocess.run(
        ["bluetoothctl"], input=script, capture_output=True, text=True
    )
    return proc.stdout + proc.stderr

# BLUETOOTH BACKGROUND SCAN PROCESS AND FILL SCAN_LINES FOR DURATION --timeout
scan_lines = []
def bt_background_scan_on():
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
            
            print(line)
            scan_lines.append(line)

    
    threading.Thread(target=read_output, daemon=True).start()

    return scan_process

# TERMINATE ALL LINGERING BLUETOOTHCTL --timeout PROCESSES // USE TO STOP BACKGROUND SCAN PROCESS
def bt_scan_stop_all():
    subprocess.run(["pkill", "-f", "bluetoothctl --timeout"])
    print("Terminated any lingering bluetoothctl scan processes")

# REMOVE DEVICE
def bt_remove_device(mac, timeout=5):
    bt_bluetoothctl(f"remove {mac}", timeout)

# CHECK IF SINGLE DEVICE IS TRUSTED
def check_if_trusted(mac, verbose = False):
    timeout = 10
    trusted = mac in bt_bluetoothctl("devices Trusted", timeout).stdout
    if trusted:
        if verbose:
            print(f"{mac} trusted")
    else:
        if verbose:
            print(f"{mac} not trusted")
        return False
    return True

# CHECK IF SINGLE DEVICE IS PAIRED
def check_if_paired(mac, verbose = False):
    timeout = 10
    paired = mac in bt_bluetoothctl("devices Paired", timeout).stdout
    if paired:
        if verbose:
            print(f"{mac} paired")
    else:
        if verbose:
            print(f"{mac} unpaired")
        return False
    return True

# CHECK IF SINGLE DEVICE IS CONNECTED
def check_if_connected(mac, verbose = False):
    timeout = 10
    connected = mac in bt_bluetoothctl("devices Connected", timeout).stdout
    if connected:
        if verbose:
            print(f"{mac} connected")
    else:
        if verbose:
            print(f"{mac} disconnected")
        return False
    return True

# CHECK IF ALL DEVICES ARE CONNECTED, RETURN LIST OF CONNECTED DEVICES FROM BLUETOOTHCTL DEVICES CONNECTED OUTPUT
def check_if_all_connected(verbose = True) -> (bool, list):
    timeout = 10
    connected = bt_bluetoothctl("devices Connected", timeout).stdout
    list_connected = []
    
    for mac in OUTPUT_DEVICES:
        if mac in connected:
            if verbose:
                print(f"{mac} Connected")
            list_connected.append(mac)
        else:
            return False, list_connected
    return True, list_connected

# TRUST INDIVIDUAL DEVICE
def trust_device(mac):
    bt_bluetoothctl(f"trust {mac}", timeout=10)

# PAIR INDIVIDUAL DEVICE
def pair_device(mac):
    bt_bluetoothctl(f"pair {mac}", timeout=10)

# TRUST AND PAIR ALL DEVICES IN OUTPUT_DEVICES 
def trust_and_pair_devices(OUTPUT_DEVICES):
    for mac in OUTPUT_DEVICES:
        trusted = check_if_trusted(mac)
        paired = check_if_paired(mac)

        # IF MAC NOT PAIRED > CHECK IF TRUSTED
        max_pairing_attempts = 0
        while not paired and max_pairing_attempts < 10:
            
            # IF MAC NOT TRUSTED > WAIT FOR MAC TO APPEAR IN SCAN_LINES > TRUST
            max_trusting_attempts = 0
            while not trusted and max_trusting_attempts < 10:
                
                # WHILE MAC DID NOT APPEAR YET WAIT 1 SECOND, RIGHT NOW INFINITE LOOP !!
                while not any(mac in line for line in scan_lines):
                    print(f"Waiting for {mac} to appear in scan_lines")
                    time.sleep(1)

                # BROKE OUT OF INNER WHILE LOOP FOR MAC APPEAR IN SCAN_LINES > ATTEMPTING TO TRUST
                max_trusting_attempts += 1
                print(f"Attempting to trust with {mac}. Trusting attempt: {max_trusting_attempts}")
                trust_device(mac)
                trusted  = check_if_trusted(mac)
            
            # BROKE OUT OF NOT TRUSTED WHILE LOOP > ATTEMPTING TO PAIR
            max_pairing_attempts += 1
            print(f"Attempting to pair with {mac}. Pairing attempt: {max_pairing_attempts}")
            pair_device(mac)
            paired = check_if_paired(mac)
            

def connect_device(mac):
    bt_bluetoothctl(f"connect {mac}", timeout=10)



                









## STACK



bt_bluetoothctl("power on")
bt_bluetoothctl("agent on")
time.sleep(2)
bt_select_default_controller(CONTROLLER_OUTPUT) ## improve test against bluetoothctl list to check if agent is already [default]
bt_bluetoothctl("agent on") ## can remove later after controller check

bt_background_scan_on() #Start background scan for --timeout set in function


print("#####################  DEBUG LINE 1 #######################")
trust_and_pair_devices(OUTPUT_DEVICES)
print("#####################  DEBUG LINE 2 #######################")


print("#####################  DEBUG LINE 3 #######################")


bt_scan_stop_all() ## RFKILL LINGERING BACKGROUND SERVICES // 