import curses
import threading
from interfaces.tui.engine import Menu, log

class DeviceSelectionMenu(Menu):
    def __init__(self, scanner, on_saved, title="Bluetooth Device Selection"):
        super().__init__(title, items=[])
        self.scanner = scanner
        self.on_saved = on_saved
        self.is_scanning = False

    def _start_scan(self):
        self.is_scanning = True
        log("[Scan] Starting Bluetooth discovery...")

        def _worker():
            try:
                self.scanner.scan(timeout=20)
                log("[Scan] Discovery finished.")
            except Exception as e:
                log(f"[Scan Error] {e}")
            finally:
                self.is_scanning = False

        threading.Thread(target=_worker, daemon=True).start()

    def run(self, menu_win, log_win):
        self._start_scan()
        sel = 0
        menu_win.timeout(50)

        while True:
            # 1. Build dynamic item list: devices + actions
            mac_list = list(self.scanner.devices.keys())
            total_items = len(mac_list) + 1  # +1 for "Save & Exit"

            # Clamp cursor selection
            sel = max(0, min(sel, total_items - 1))

            # 2. Render and drain logs
            self._draw_devices(menu_win, sel, mac_list)
            self._drain_logs(log_win)

            # 3. Handle input
            key = menu_win.getch()

            if key in (curses.KEY_UP, ord('k')):
                sel = (sel - 1) % total_items
            elif key in (curses.KEY_DOWN, ord('j')):
                sel = (sel + 1) % total_items
            elif key in (ord(' '), 10, 13):
                if sel < len(mac_list):
                    mac = mac_list[sel]
                    self.scanner.toggle_device(mac)
                else:
                    # Selected "Save & Exit"
                    self.scanner.save_devices_to_json()
                    self.on_saved()
                    log("[Saved] Device selection saved.")
                    return
            elif key in (27, curses.KEY_BACKSPACE, 127, 8):
                return
            elif key == ord('q'):
                raise SystemExit

    def _draw_devices(self, menu_win, sel, mac_list):
        menu_win.erase()
        max_y, max_x = menu_win.getmaxyx()

        status = " [SCANNING...]" if self.is_scanning else " [IDLE]"
        menu_win.addstr(0, 2, (self.title + status)[:max_x - 3], curses.A_BOLD)

        # Available vertical space for device list (leaving room for title & Save button)
        visible_rows = max_y - 3

        for i, mac in enumerate(mac_list):
            row = 2 + i
            if row >= max_y - 1:
                break  # Prevent writing past window height

            name = self.scanner.devices[mac]
            checked = "[x]" if mac in self.scanner.selected_devices else "[ ]"
            label = f"{checked} {name} ({mac})"
            attr = curses.A_REVERSE if i == sel else 0
            
            # Clip to window width
            menu_win.addstr(row, 4, label[:max_x - 5], attr)

        # Draw "Save & Exit" on the last available row
        save_idx = len(mac_list)
        save_attr = curses.A_REVERSE if sel == save_idx else 0
        save_row = min(2 + len(mac_list), max_y - 1)
        
        if save_row < max_y:
            menu_win.addstr(save_row, 4, "[ Save & Exit ]"[:max_x - 5], save_attr | curses.A_BOLD)

        menu_win.refresh()