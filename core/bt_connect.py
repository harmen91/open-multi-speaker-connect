import subprocess
import threading
import queue
import time
from core.load_env import CONTROLLER_INPUT, CONTROLLER_OUTPUT, INPUT_DEVICES, OUTPUT_DEVICES

# SINGLE CALL TO BLUETOOTHCTL, WAIT FOR OUTPUT, OR TERMINATE AFTER FIXED TIMEOUT
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

# SELECT DEFAULT BLUETOOTH CONTROLLER
def bt_select_default_controller(controller):
    script=f"select {controller}\nagent on\ndefault-agent\n pairable on"
    proc = subprocess.run(
        ["bluetoothctl"], input=script, capture_output=True, text=True
    )
    return proc.stdout + proc.stderr

# BLUETOOTH BACKGROUND SCAN PROCESS AND FILL SCAN_QUEUE FOR DURATION --timeout
scan_queue = queue.Queue()
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
            print(line) # >>>>>>>>> DISABLE THIS IN THE FUTURE <<<<<<<<<<<<
            scan_queue.put(line)
    threading.Thread(target=read_output, daemon=True).start()

    return scan_process

# TERMINATE ALL LINGERING BLUETOOTHCTL --timeout PROCESSES // USE TO STOP BACKGROUND SCAN PROCESS
def bt_scan_stop_all():
    bt_bluetoothctl("scan off")
    subprocess.run(["pkill", "-f", "bluetoothctl --timeout"])
    print("Terminated any lingering bluetoothctl background scan processes")

# REMOVE DEVICE
def bt_remove_device(mac, timeout=5):
    bt_bluetoothctl(f"remove {mac}", timeout)

# REMOVE ALL TRUSTED, PAIRED and CONNECTED BLUETOOTH DEVICES
def bt_remove_devices():
    for mac in OUTPUT_DEVICES:
        bt_bluetoothctl((f"remove {mac}"))


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

# CHECK IF ALL DEVICES ARE TRUSTED
def check_if_all_trusted():
    timeout = 10
    trusted = bt_bluetoothctl("devices Trusted", timeout).stdout    
    for mac in OUTPUT_DEVICES:
        if mac in trusted:
            continue
        else:
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
    local_scan_lines = []

    while True:
        try:
            local_scan_lines.append(scan_queue.get_nowait())
        except queue.Empty:
            break

    for mac in OUTPUT_DEVICES:
        trusted = check_if_trusted(mac)
        paired = check_if_paired(mac)

        # IF MAC NOT PAIRED > CHECK IF TRUSTED
        max_pairing_attempts = 0
        while not paired and max_pairing_attempts < 10:
            
            # IF MAC NOT TRUSTED > WAIT FOR MAC TO APPEAR IN local_scan_lines > TRUST
            max_trusting_attempts = 0
            while not trusted and max_trusting_attempts < 10:
                
                # WHILE MAC DID NOT APPEAR YET WAIT 1 SECOND, RIGHT NOW INFINITE LOOP !! 
                ## Idea??>> DO SOMETHING WITH POWER OFF ON OR TOGGLE SCAN ON ??? >> CHECK SCAN LINE FOR "[CHG] Controller C4:3D:1A:00:BE:68 Discovering: no"
                while not any(mac in line for line in local_scan_lines):
                    try:
                        line = scan_queue.get(timeout=1) #line becomes latest queue.get

                        ### >> ADD IF STATEMENT FOR LOSING CONNECTION > POWER OFF / ON CYCLE
                        ### >> DELETE BCKGRND SCAN > START BACKGROUND SCAN
                        ### >> TEST AND ADD TIMESLEEP ???? MAKE SURE IT DOES NOT CRASH ON SLOW HARDWARE



                        local_scan_lines.append(line)
                    except queue.Empty:
                        print(f"Waiting for {mac} to appear") #waiting for new entry in queue to appear

                # BROKE OUT OF INNER WHILE LOOP FOR MAC APPEAR IN local_scan_lines > ATTEMPTING TO TRUST
                max_trusting_attempts += 1
                print(f"Attempting to trust with {mac}. Trusting attempt: {max_trusting_attempts}")
                trust_device(mac)
                time.sleep(1)
                trusted  = check_if_trusted(mac)
            
            # BROKE OUT OF NOT TRUSTED WHILE LOOP > ATTEMPTING TO PAIR
            max_pairing_attempts += 1
            print(f"Attempting to pair with {mac}. Pairing attempt: {max_pairing_attempts}")
            pair_device(mac)
            paired = check_if_paired(mac)
            # FIRST TIME TRYING TO CONNECT RIGHT AFTER PAIRING SUCCESFULLY - IMPROVED CONNECTIVITY ISSUES WITH BOSE SOUNDLINK MINI 
            connect_device(mac)
            

# CONNECT INDIVIDUAL DEVICE
def connect_device(mac):
    bt_bluetoothctl(f"connect {mac}", timeout=10)

# CONNECT ALL DEVICES
def connect_devices(OUTPUT_DEVICES):
    all_trusted = check_if_all_trusted()
    all_connected = check_if_all_connected()[0]

    # CHECK IF ALL CONNECTED
    if not all_connected:
        print(f"Not all devices are connected, checking if Trusted.")
        # CHECK IF ALL TRUSTED
        if all_trusted:
            print(f"All devices are trusted, attempting to connect all devices.")

            # ALL TRUSTED AND READY TO CONNECT EACH DEVICE
            for mac in OUTPUT_DEVICES:
                trusted = check_if_trusted(mac)
                connected = check_if_connected(mac)
                # ATTEMPT TO CONNECT TO DEVICE FOR MAX CONNECTING_ATTEMPTS
                connecting_attempts = 0
                while trusted and not connected and connecting_attempts < 10:
                    time.sleep(1)
                    connecting_attempts += 1
                    print(f"Attempting to connect with {mac}. Connecting attempt: {connecting_attempts}")
                    connect_device(mac)
                    connected = check_if_connected(mac)


#########################################
######### FINAL FUNCTION CALL ###########
#########################################

def bluetooth_connect_speakers(CONTROLLER_OUTPUT, OUTPUT_DEVICES):

    if not check_if_all_connected(OUTPUT_DEVICES)[0]:

        print("#####################  TURNING ON BLUETOOTH #######################")
        bt_bluetoothctl("power on")
        time.sleep(3)

        print(f"#####################  SET DEFAULT OUTPUT CONTROLLER TO {CONTROLLER_OUTPUT} #######################")
        bt_select_default_controller(CONTROLLER_OUTPUT) ## improve test against bluetoothctl list to check if agent is already [default]
        time.sleep(1)

        print("#####################  START BLUETOOTHCTL SCAN BACKGROUND SERVICE #######################")
        print("#####################  CAPTURING ALL INCOMING BLUETOOTH MESSAGES #######################")
        bt_background_scan_on() 
        time.sleep(3)

        print("#####################  TRUST AND PAIR DEVICES #######################")
        trust_and_pair_devices(OUTPUT_DEVICES)
        time.sleep(1)

        print("#####################  CONNECT ALL DEVICES #######################")
        connect_devices(OUTPUT_DEVICES)

        # print("#####################  TERMINATE ALL LINGERING BACKGROUND SCAN SERVICES #######################")    
        # bt_scan_stop_all()

    return check_if_all_connected(OUTPUT_DEVICES)




################################
######### TEST STACK ###########
################################

if __name__ == "__main__":

    bluetooth_connect_speakers(CONTROLLER_OUTPUT, OUTPUT_DEVICES)




################################
######### TO DO ################
################################

## -- BLUETOOTH SCAN TRUST / PAIR while loop improvement :
## -- ERROR HANDLING >> Controller {CONTROLLER OUTPUT} Discovering: no   << TRIGGER BLUETOOTH RESTART OFF WAIT ON WAIT SCAN ON FUNC
## -- ERROR HANDLING >> NO SCAN INPUT FOR x time                         << TRIGGER BLUETOOTH RESTART OFF WAIT ON WAIT SCAN ON FUNC


## -- LOSING A SPEAKER E.G. BATTERY RUNNING OUT / WHATEVER
## -- upon disconnecting bluetoothctl scan receives 'Device {mac} Connected: no'
## -- 
## -- RECONNECTING WORKS WITHOUT SCAN IF PREVIOUSLY CONNECTED, BUT :
## --   - 'pairable on' needs to be set for automatic reconnection
## --   - buggy reconnection status 'bluetoothctl devices Connected' no longer reliably list connected devices, causing script to hang