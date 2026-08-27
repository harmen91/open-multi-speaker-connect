import os

## THIS LINE SETS THE ESCAPE KEY DELAY TO 25MS BEFORE CURSES IMPORTS SO EXITING MENUS IS INSTANT WITHOUT DELAY
os.environ.setdefault('ESCDELAY', '25')

import curses
import inspect
import queue
import threading
import time

## THIS OBJECT HOLDS A THREAD-SAFE MESSAGE QUEUE USED BY ALL BACKGROUND WORKERS TO PASS LOG STRINGS SAFELY TO THE TUI
LOG_QUEUE = queue.Queue()

## THIS FLAG SYNCHRONIZES THREAD STATE TO SIGNAL WHEN A BLOCKING BACKGROUND TASK IS ACTIVELY RUNNING AND LOCKING THE UI
BUSY_EVENT = threading.Event()

ACTIVE_APP = None

def get_active_menu():
    global ACTIVE_APP
    return ACTIVE_APP

## THIS FUNCTION SENDS TEXT MESSAGES INTO THE THREAD-SAFE QUEUE SO THEY CAN BE CONSUMED AND PRINTED IN THE BOTTOM LOG WINDOW
def log(msg):
    LOG_QUEUE.put(str(msg))


## THIS CLASS REPRESENTS A SINGLE ENTRY IN A MENU HOLDING ITS DISPLAY LABEL, ITS ACTION CALLBACK OR SUBMENU, AND EXECUTION SETTINGS
class MenuItem:
    ## THIS CONSTRUCTOR INITIALIZES THE MENU ITEM ATTRIBUTES AND ENSURES EITHER AN ACTION FUNCTION OR SUBMENU IS PROVIDED
    def __init__(self, label, action=None, submenu=None, needs_input=False, blocking=True):
        assert action or submenu, "MenuItem needs an action or a submenu"
        self.label = label
        self.action = action
        self.submenu = submenu
        self.needs_input = needs_input
        self.blocking = blocking

    ## THIS METHOD CHECKS IF THIS SPECIFIC ITEM OPENS ANOTHER SUBMENU RATHER THAN RUNNING A TERMINAL ACTION
    def is_submenu(self):
        return self.submenu is not None


## THIS DECORATOR ATTACHES A NON-BLOCKING ATTRIBUTE FLAG TO A TARGET FUNCTION SO THE MENU DOES NOT LOCK WHILE IT RUNS IN THE BACKGROUND
def non_blocking(fn):
    fn._blocking = False
    return fn


## THIS CLASS MANAGES DRAWING AND HANDLING KEYBOARD EVENTS FOR A COLLECTION OF MENU ITEMS INSIDE A DEDICATED CURSES WINDOW
class Menu:
    ## THIS CONSTRUCTOR INITIALIZES THE MENU TITLE AND ITS LIST OF MENU ITEMS
    def __init__(self, title, items):
        self.title = title
        self.items = items
    
    def update_config(self, new_config):
        """Replaces current menu items with a freshly parsed config."""
        new_menu = build_menu(self.title, new_config)
        self.items = new_menu.items

    ## THIS METHOD RUNS THE INTERACTIVE EVENT LOOP WHICH CONTINUOUSLY DRAWS THE MENU, CHECKS FOR KEYPRESSES, AND DRAINS LOG MESSAGES
    def run(self, menu_win, log_win):
        sel = 0
        menu_win.timeout(50)

        while True:
            self._draw(menu_win, sel)
            self._drain_logs(log_win)

            key = menu_win.getch()

            ## THIS CHECK PREVENTS USER NAVIGATION AND ACTION SELECTION WHENEVER A BLOCKING BACKGROUND TASK IS RUNNING
            if BUSY_EVENT.is_set():
                continue

            if key in (curses.KEY_UP, ord('k')):
                sel = (sel - 1) % len(self.items)
            elif key in (curses.KEY_DOWN, ord('j')):
                sel = (sel + 1) % len(self.items)
            elif key in (10, 13):
                self._select(menu_win, log_win, self.items[sel])
            elif key in (27, curses.KEY_BACKSPACE, 127, 8):
                return
            elif key == ord('q'):
                raise SystemExit

    ## THIS METHOD HANDLES WHAT HAPPENS WHEN AN ITEM IS SELECTED BY EITHER OPENING A SUBMENU OR RUNNING ITS ACTION IN A BACKGROUND THREAD
    def _select(self, menu_win, log_win, item):
        if item.is_submenu():
            item.submenu.run(menu_win, log_win)
        else:
            args = []
            prompt_y = len(self.items) + 3

            if item.needs_input:
                sig = inspect.signature(item.action)

                for param in sig.parameters.values():
                    # 1. Confirmation prompt (includes previous inputs if available)
                    if param.annotation is bool or "confirm" in param.name.lower():
                        if args:
                            preview = ", ".join(f"'{a}'" for a in args)
                            msg = f"Confirm {item.label} with {preview}?"
                        else:
                            msg = f"Confirm {item.label}?"

                        val = prompt_confirm(menu_win, msg, y=prompt_y)
                        if not val:
                            log(f"[Cancelled] '{item.label}' aborted.")
                            return
                        args.append(True)

                    # 2. String input
                    elif param.annotation is str:
                        val = prompt_str(menu_win, f"Enter {param.name}: ", y=prompt_y)
                        if val is None:
                            return
                        args.append(val)

                    # 3. Integer input
                    else:
                        val = prompt_int(menu_win, f"Enter {param.name}: ", y=prompt_y)
                        if val is None:
                            return
                        args.append(val)

            ## THIS INTERNAL WORKER FUNCTION EXECUTES THE ACTION IN A THREAD, OPTIONALLY RAISING THE BUSY LOCK AND LOGGING ANY RETURN VALUES
            def _worker():
                try:
                    if item.blocking:
                        BUSY_EVENT.set()
                    result = item.action(*args)
                    if result is not None:
                        log(f"[Result] {result}")
                except Exception as e:
                    log(f"[Error] {e}")
                finally:
                    if item.blocking:
                        BUSY_EVENT.clear()

            threading.Thread(target=_worker, daemon=True).start()

    ## THIS METHOD RENDERS THE MENU TITLE, BUSY INDICATOR, AND HIGHLIGHTED/DIMMED MENU ITEMS TO THE TOP MENU WINDOW
    def _draw(self, menu_win, sel):
        menu_win.erase()

        status = " [BUSY - PLEASE WAIT]" if BUSY_EVENT.is_set() else ""
        menu_win.addstr(0, 2, self.title + status, curses.A_BOLD)

        for i, item in enumerate(self.items):
            if BUSY_EVENT.is_set():
                attr = curses.A_DIM
            else:
                attr = curses.A_REVERSE if i == sel else 0

            label = item.label + (" >" if item.is_submenu() else "")
            menu_win.addstr(2 + i, 4, label, attr)
        menu_win.refresh()

    ## THIS METHOD CONSUMES ALL PENDING MESSAGES FROM THE LOG QUEUE AND PRINTS THEM LINE BY LINE INTO THE SCROLLING BOTTOM LOG WINDOW
    def _drain_logs(self, log_win):
        updated = False
        while not LOG_QUEUE.empty():
            try:
                msg = LOG_QUEUE.get_nowait()
                log_win.addstr(f"{msg}\n")
                updated = True
            except queue.Empty:
                break
        if updated:
            log_win.refresh()

def prompt_str(win, prompt, y=4):
    curses.noecho()
    curses.curs_set(1)
    win.timeout(-1)
    win.addstr(y, 4, prompt)
    win.refresh()
    buf = ""
    while True:
        ch = win.getch()
        if ch in (10, 13):
            # Only submit if at least one non-whitespace character was entered
            if buf.strip():
                break
        elif ch == 27:  # Esc to cancel
            curses.curs_set(0)
            win.timeout(50)
            return None
        elif ch in (curses.KEY_BACKSPACE, 127, 8):
            buf = buf[:-1]
        elif 32 <= ch <= 126:
            buf += chr(ch)

        win.addstr(y, 4 + len(prompt), " " * 30)
        win.addstr(y, 4 + len(prompt), buf)
        win.refresh()

    curses.curs_set(0)
    win.timeout(50)
    return buf.strip()


## THIS FUNCTION PROMPTS THE USER FOR A NUMERICAL INTEGER INPUT WITH IN-PLACE EDITING, BACKSPACE SUPPORT, AND ESCAPE CANCELLATION
def prompt_int(win, prompt, y=4):
    curses.noecho()
    curses.curs_set(1)
    win.timeout(-1)
    win.addstr(y, 4, prompt)
    win.refresh()
    buf = ""
    while True:
        ch = win.getch()
        if ch in (10, 13):
            # Only submit if at least one digit was entered
            if buf:
                break
        elif ch == 27:  # Esc to cancel
            curses.curs_set(0)
            win.timeout(50)
            return None
        elif ch in (curses.KEY_BACKSPACE, 127, 8):
            buf = buf[:-1]
        elif 0 <= ch <= 255 and chr(ch).isdigit():
            buf += chr(ch)

        win.addstr(y, 4 + len(prompt), " " * 15)
        win.addstr(y, 4 + len(prompt), buf)
        win.refresh()

    curses.curs_set(0)
    win.timeout(50)
    return int(buf)

def prompt_confirm(win, prompt, y=4):
    """Waits for Y/N. Returns True for Y, False for N or Esc."""
    win.timeout(-1)
    curses.curs_set(0)
    win.addstr(y, 4, f"{prompt} [y/N]: ", curses.A_BOLD)
    win.refresh()
    
    confirmed = False
    while True:
        ch = win.getch()
        if ch in (ord('y'), ord('Y')):
            confirmed = True
            break
        elif ch in (ord('n'), ord('N'), 10, 13, 27):  # N, Enter (default No), or Esc
            confirmed = False
            break

    win.timeout(50)
    return confirmed

## THIS FUNCTION PARSES A NESTED CONFIG DICTIONARY AND RECURSIVELY CREATES MENU AND MENUITEM INSTANCES WITH AUTOMATIC PARAMETER DETECTION
def build_menu(title, config):
    items = []
    for label, target in config.items():
        if isinstance(target, dict):
            submenu = build_menu(label, target)
            items.append(MenuItem(label, submenu=submenu))
        elif callable(target):
            sig = inspect.signature(target)
            needs_input = len(sig.parameters) > 0
            blocking = getattr(target, "_blocking", True)
            items.append(MenuItem(label, action=target, needs_input=needs_input, blocking=blocking))
    return Menu(title, items)


## THIS FUNCTION IS THE TOP-LEVEL PUBLIC LAUNCHER THAT SPLITS THE TERMINAL SCREEN INTO TOP AND BOTTOM PANELS AND RUNS THE CURSES EVENT LOOP
def start_app(title="Main Menu", menu_config=None):
    global ACTIVE_APP
    if menu_config is None:
        menu_config = {}

    nav_info = " || Hit ESC to go back. Press Q to quit."
    ACTIVE_APP = build_menu(f"{title} {nav_info}", menu_config)

    ## THIS INTERNAL WRAPPER FUNCTION CREATES AND CONFIGURES THE CURSES WINDOW OBJECTS AND STARTS THE MAIN EVENT LOOP
    def _main(stdscr):
        curses.curs_set(0)
        max_y, max_x = stdscr.getmaxyx()

        ## THIS SPLITS THE TERMINAL INTO A TOP FIXED WINDOW FOR THE MENU AND A BOTTOM SCROLLABLE WINDOW FOR LOG MESSAGES
        menu_height = 12
        menu_win = curses.newwin(menu_height, max_x, 0, 0)
        menu_win.keypad(True)

        log_height = max_y - menu_height
        log_win = curses.newwin(log_height, max_x, menu_height, 0)
        log_win.scrollok(True)

        log("System initialized. Ready.")
        ACTIVE_APP.run(menu_win, log_win)

    curses.wrapper(_main)


################################
######### TEST STACK ###########
################################


## TEST SPEAKER CONTROLLER CLASS >> THIS IS COOL IMPLEMENT THIS IN AUDIO_SINKS??
class SpeakerController:
    def __init__(self, name="Living Room Speaker", initial_volume=50):
        self.name = name
        self.volume = initial_volume

    def set_volume(self, level: int):
        # 1. Clamp/validate range between 0 and 100
        if not (0 <= level <= 100):
            return f"Error: Volume {level}% out of range (must be 0-100)."

        self.volume = level

        # 2. Render visual progress bar: [========..........] 50%
        bar_width = 20
        filled = int((self.volume / 100) * bar_width)
        bar = "=" * filled + "." * (bar_width - filled)
        
        log(f"[{self.name}] Level: [{bar}] {self.volume}%")
        return f"Volume set to {self.volume}%"

    def volume_up(self):
        return self.set_volume(min(100, self.volume + 10))

    def volume_down(self):
        return self.set_volume(max(0, self.volume - 10))



## THIS BLOCK EXECUTES THE TEST STACK WHEN RUN DIRECTLY AS A STANDALONE SCRIPT
if __name__ == "__main__":

    ## TEST SPEAKER CONTROLLER OBJECT
    speaker = SpeakerController()


    ## TEST FUNCTION TO SIMULATE NAMING A DEVICE
    def name_device(name: str, confirm: bool):
        return f"Device succesfvully renamed to '{name}'."

    ## THIS TEST FUNCTION SIMULATES A LONG BLOCKING TASK THAT LOCKS THE MENU WHILE STREAMING INCREMENTAL LOGS TO THE BOTTOM PANEL
    def test_count():
        max_count = 10
        count = 0
        while count < max_count:
            count += 1
            time.sleep(0.3)
            log(f"Counting (blocked menu): {count}")
        return "Counting finished."


    ## THIS TEST FUNCTION SIMULATES A NON-BLOCKING BACKGROUND WORKER THAT ALLOWS THE USER TO CONTINUE BROWSING THE MENU WHILE LOGS STREAM
    @non_blocking
    def background_scanner():
        log("Background scanner started (menu interactive!)...")
        for i in range(1, 11):
            time.sleep(1)
            log(f"[Background Task] Scan event #{i}")
        return "Background scan completed."
    
    app_config = {
        "Rename Device": name_device,
        "Count (Blocks Menu)": test_count,
        "Background Task (Interactive)": background_scanner,
        "System Check": lambda: "All systems nominal.",
        "Audio Controls": {
            "Set Volume (0-100)": speaker.set_volume,
            "Volume +10%": speaker.volume_up,
            "Volume -10%": speaker.volume_down,
        }
    }

    start_app(title="OPEN SPEAKER CONNECT", menu_config=app_config)




    ### HOW IT WORKS ###

    """ 
    1. Initialization & Layout Setup

        start_app() & curses.wrapper(_main):
            curses.wrapper safely initializes your terminal (disabling cursor echo, setting cbreak mode) and restores it upon exit or crash.
        Window Splitting:
            menu_win: A fixed top window (1212 rows high) dedicated to rendering the title, menu items, and input prompts.
            log_win: A dynamic bottom window filling the remaining screen space (max_y - 12), configured with scrollok(True) to automatically scroll logs upwards.

    2. Auto-Discovery & Menu Tree (build_menu)

        When you provide app_config:
            If a value is a nested dictionary, it creates a submenu MenuItem and recursively instantiates a child Menu.
            If a value is a callable function, inspect.signature(target) detects if the function accepts parameters (needs_input=True) and checks if it was marked with @non_blocking.

    3. The Interactive Loop (Menu.run)

    The menu runs a continuous non-blocking loop checked every 50ms (menu_win.timeout(50)):

        _draw(): Erases and renders the menu items. The active index (sel) gets curses.A_REVERSE (highlighted), or curses.A_DIM if the system is busy.
        _drain_logs(): Checks the thread-safe LOG_QUEUE and writes any pending logs into log_win.
        menu_win.getch():
            Up/Down arrows (k/j): Cycles through selections (sel = (sel ± 1) % total).
            Enter: Triggers _select() for the highlighted item.
            Esc / Backspace: Exits the current submenu (or app from root).
            q: Terminates the program.
            Busy Guard: If BUSY_EVENT.is_set() is True, keystrokes are ignored to prevent accidental commands.

    4. Dynamic Input Handling (_select)

    When an action is triggered:

        The code inspects the function parameters and dynamically calls:
            prompt_str() for string inputs (e.g., name: str).
            prompt_int() for numeric values (e.g., level: int).
            prompt_confirm() for boolean confirmations (e.g., confirm: bool).
        If the user cancels with Esc, input returns None and execution safely aborts without running the action.

    5. Multithreaded Execution & Logging (_worker)

        Actions execute in a background daemon thread (threading.Thread).
        Blocking Tasks (Default): Sets BUSY_EVENT, locking menu navigation until completion.
        @non_blocking Tasks: Leaves BUSY_EVENT unset, keeping the menu interactive.
        Logging: Any thread calling log("message") pushes text into LOG_QUEUE, which the main loop flushes to log_win during its 50ms cycle.
    """