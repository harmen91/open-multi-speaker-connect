import os

os.environ.setdefault('ESCDELAY', '25')

import curses
import inspect
import queue
import threading
import time

LOG_QUEUE = queue.Queue()
BUSY_EVENT = threading.Event()

ACTIVE_APP = None

def get_active_menu():
    global ACTIVE_APP
    return ACTIVE_APP

def log(msg):
    LOG_QUEUE.put(str(msg))

BANNER = r"""
                                                                                       
    ██  ██     ▄▄▄▄▄    ▄▄▄▄▄▄▄ ▄▄▄      ▄▄▄  ▄▄▄▄▄▄▄       ██  ██   ▄▄▄▄  ▄▄▄▄   ▄▄▄▄ 
   ██  ██    ▄███████▄ █████▀▀▀ ████▄  ▄████ ███▀▀▀▀▀      ██  ██    ▀███  ███▀ ▄█████ 
  ██  ██     ███   ███  ▀████▄  ███▀████▀███ ███          ██  ██      ███  ███     ███ 
 ██  ██      ███▄▄▄███    ▀████ ███  ▀▀  ███ ███         ██  ██       ███▄▄███     ███ 
██  ██        ▀█████▀  ███████▀ ███      ███ ▀███████   ██  ██         ▀████▀ ██   ███ 
                                                                                       
                                                                                       
"""

def _draw_banner(win, banner=BANNER):
    win.erase()
    max_y, max_x = win.getmaxyx()
    lines = banner.strip("\n").splitlines()
 
    for i, line in enumerate(lines):
        if i >= max_y:
            break
        # Clip to max_x - 1 so we never write into the window's bottom-right corner cell (curses raises on that)
        win.addstr(i, 0, line[:max_x - 1])
 
    win.refresh()
 
class MenuItem:
    def __init__(self, label, action=None, submenu=None, needs_input=False, blocking=True):
        assert action or submenu, "MenuItem needs an action or a submenu"
        self.label = label
        self.action = action
        self.submenu = submenu
        self.needs_input = needs_input
        self.blocking = blocking

    def is_submenu(self):
        return self.submenu is not None

def non_blocking(fn):
    fn._blocking = False
    return fn

class Menu:
    def __init__(self, title, items):
        self.title = title
        self.items = items
    
    def update_config(self, new_config):
        """Replaces current menu items with a freshly parsed config."""
        new_menu = build_menu(self.title, new_config)
        self.items = new_menu.items

    def run(self, menu_win, log_win):
        sel = 0
        menu_win.timeout(50)

        while True:
            self._draw(menu_win, sel)
            self._drain_logs(log_win)

            key = menu_win.getch()

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

def build_menu(title, config):
    items = []
    for label, target in config.items():
        if isinstance(target, Menu):
            # Supports passing Menu instances (like DeviceSelectionMenu) directly
            items.append(MenuItem(label, submenu=target))
        elif isinstance(target, dict):
            submenu = build_menu(label, target)
            items.append(MenuItem(label, submenu=submenu))
        elif callable(target):
            sig = inspect.signature(target)
            needs_input = len(sig.parameters) > 0
            blocking = getattr(target, "_blocking", True)
            items.append(MenuItem(label, action=target, needs_input=needs_input, blocking=blocking))
    return Menu(title, items)


def start_app(title="Main Menu", menu_config=None, banner=BANNER):
    global ACTIVE_APP
    if menu_config is None:
        menu_config = {}
 
    nav_info = " || Hit ESC to go back. Press Q to quit."
    ACTIVE_APP = build_menu(f"{title} {nav_info}", menu_config)
 
    def _main(stdscr):
        curses.curs_set(0)
        max_y, max_x = stdscr.getmaxyx()
 
        banner_lines = banner.strip("\n").splitlines()
        banner_height = len(banner_lines)
 
        menu_height = 12
 
        if max_y < banner_height + menu_height + 1:
            banner_height = 0
 
        if banner_height > 0:
            banner_win = curses.newwin(banner_height, max_x, 0, 0)
            _draw_banner(banner_win, banner)
 
        menu_win = curses.newwin(menu_height, max_x, banner_height, 0)
        menu_win.keypad(True)
 
        log_height = max_y - menu_height - banner_height
        log_win = curses.newwin(log_height, max_x, banner_height + menu_height, 0)
        log_win.scrollok(True)
 
        log("System initialized. Ready.")
        ACTIVE_APP.run(menu_win, log_win)
 
    curses.wrapper(_main)

