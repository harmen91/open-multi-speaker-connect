import subprocess
import threading
import time
from load_env import env

OUTPUT_DEVICES = [v for k, v in env.items() if k.startswith("OUTPUT_DEVICE")]

def bluetoothctl(args, timeout):
    try:
        timeout = timeout
        completed_process = subprocess.run(
            ["bluetoothctl"] + args.split(),
            timeout=timeout,
            capture_output=True,
            text=True,
            check=True
        )
        return completed_process
    except subprocess.CalledProcessError as exc:

        if exc.cmd[1] == "pair":
            print(f"Error running pair command for OUTPUT_DEVICE{exc.cmd[2]}\nCheck if already paired")
        else:
            print(
            f"Process failed because did not return a successful return code. "
            f"Returned {exc.returncode}\n{exc}"
        )
        return exc
    except subprocess.TimeoutExpired as exc:
        print(f"Process times out.\n{exc}")
        return exc    

def remove_devices():
    timeout = 10
    for mac in OUTPUT_DEVICES:
        bluetoothctl(f"remove {mac}", timeout)





scan_lines = []
def bt_background_scan_on():
    bluetoothctl("power off", 10)
    bluetoothctl("power on", 10)
    print("Starting background scan...")

    scan_process = subprocess.Popen(
        ["bluetoothctl", "--timeout", "600", "scan", "on"],
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




def bt_scan_stop_all():
    subprocess.run(["pkill", "-f", "bluetoothctl --timeout"])
    print("Terminated any lingering bluetoothctl scan processes")


def check_if_paired(mac, verbose = True):

    timeout = 10
    paired = mac in bluetoothctl("devices Paired", timeout).stdout
    if paired:
        if verbose:
            print(f"{mac} paired")
    else:
        if verbose:
            print(f"{mac} unpaired")
        return False
    return True

def check_if_connected(mac, verbose = True):
    timeout = 10
    connected = mac in bluetoothctl("devices Connected", timeout).stdout
    if connected:
        if verbose:
            print(f"{mac} connected")
    else:
        if verbose:
            print(f"{mac} disconnected")
        return False
    return True

def check_if_all_connected(verbose = True) -> (bool, list):
    timeout = 10
    connected = bluetoothctl("devices Connected", timeout).stdout
    list_connected = []
    
    for mac in OUTPUT_DEVICES:
        if mac in connected:
            if verbose:
                print(f"{mac} Connected")
            list_connected.append(mac)
        else:
            return False, list_connected
    return True, list_connected



def trust_pair_connect_all_devices():
    trust = "trust"
    pair = "pair"
    connect = "connect"
    timeout = 15
    
    for mac in OUTPUT_DEVICES:
        if not check_if_paired(mac):
            count = 0
            max_attempts = 15
            while not any(mac in line for line in scan_lines):
                time.sleep(1)
                count+= 1
                print(f"Waiting for for {mac}.. Restarting background scan in.. {count}/{max_attempts}")
                if count > max_attempts:
                    bt_scan_stop_all()
                    count = 0
                    print("Restarting bluetooth scan")
                    bt_scan_stop_all()
                    time.sleep(2)
                    bt_background_scan_on()
                    time.sleep(1)

            if not check_if_paired(mac):
                bluetoothctl(f"{trust} {mac}", timeout)
                bluetoothctl(f"{pair} {mac}", timeout)

            if not check_if_connected(mac):
                bluetoothctl(f"{connect} {mac}", timeout)

def reconnect_paired_devices(): 
    timeout = 15   
    for mac in OUTPUT_DEVICES: 
        time.sleep(1)
        if not check_if_connected(mac):   
            bluetoothctl(f"connect {mac}", timeout)
        


def bluetooth_connect():
    remove_devices() #to
    bt_background_scan_on()
    trust_pair_connect_all_devices()
    reconnect_paired_devices()
    bt_scan_stop_all()
    check_if_all_connected()

bluetooth_connect()