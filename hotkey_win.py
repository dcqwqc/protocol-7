import keyboard
import time
import os
import threading
import ctypes

def log_debug(msg):
    log_path = os.path.join(os.environ.get("TEMP", "/tmp"), "protocol7_debug.log")
    try:
        with open(log_path, "a") as f:
            f.write(f"[HOTKEY_WIN] {msg}\n")
    except:
        pass

class HotkeyListener:
    def __init__(self, key_combo, on_trigger_callback):
        if isinstance(key_combo, int) or "keycode" in str(key_combo).lower():
            self.key_combo = "ctrl"
        else:
            self.key_combo = key_combo.lower()
            
        self.on_trigger_callback = on_trigger_callback
        self.running = False
        self.last_tap_time = 0
        self.double_tap_threshold = 0.8  
        self.poller_thread = None

    def start(self):
        self.running = True
        log_debug(f"Starting HotkeyListener for {self.key_combo}")
        try:
            if "+" in self.key_combo:
                keyboard.add_hotkey(self.key_combo, self.on_trigger_callback)
                log_debug("Added combination hotkey via keyboard module")
            else:
                # Use robust ctypes hardware polling for single keys instead of OS hooks.
                # This bypasses all UAC privilege dropping, UI blocking, or hook failures.
                self.poller_thread = threading.Thread(target=self._poll_hardware_keys, daemon=True)
                self.poller_thread.start()
                log_debug("Added hardware polling double-tap release hook")
        except Exception as e:
            log_debug(f"Error registering hotkey: {e}")
            self.key_combo = "ctrl"
            self.poller_thread = threading.Thread(target=self._poll_hardware_keys, daemon=True)
            self.poller_thread.start()

    def _poll_hardware_keys(self):
        # Map basic modifiers to Virtual Key Codes
        vk_code = 0x11 # VK_CONTROL
        if self.key_combo == "shift":
            vk_code = 0x10 # VK_SHIFT
        elif self.key_combo == "alt":
            vk_code = 0x12 # VK_MENU (Alt)
            
        was_down = False
        
        while self.running:
            try:
                # High bit is set if the key is currently physically down
                is_down = (ctypes.windll.user32.GetAsyncKeyState(vk_code) & 0x8000) != 0
                
                if is_down and not was_down:
                    was_down = True
                elif not is_down and was_down:
                    was_down = False
                    # Key was just physically released
                    current_time = time.time()
                    log_debug(f"Hardware KEY_UP matched. Time diff: {current_time - self.last_tap_time:.2f}s")
                    
                    if current_time - self.last_tap_time < self.double_tap_threshold:
                        log_debug("--- HARDWARE DOUBLE TAP TRIGGERED ---")
                        self.on_trigger_callback()
                        self.last_tap_time = 0 # reset
                    else:
                        self.last_tap_time = current_time
                        
                time.sleep(0.01) # 100 times a second poll rate
            except Exception as e:
                log_debug(f"Poller error: {e}")
                time.sleep(1)

    def stop(self):
        self.running = False
        try:
            keyboard.unhook_all()
        except Exception:
            pass
