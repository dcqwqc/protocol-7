import evdev
import threading
import time
import os

class HotkeyListener:
    def __init__(self, keycode, on_trigger_callback):
        self.keycode = keycode
        self.on_trigger_callback = on_trigger_callback
        self.running = False
        self.last_tap_time = 0
        self.double_tap_threshold = 0.4  # seconds
        self.tap_count = 0
        
        # For multi-key combos
        self.pressed_keys = set()
        
    def find_keyboards(self):
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        keyboards = []
        for dev in devices:
            capabilities = dev.capabilities()
            if evdev.ecodes.EV_KEY in capabilities:
                if evdev.ecodes.KEY_A in capabilities[evdev.ecodes.EV_KEY]:
                    keyboards.append(dev)
        return keyboards

    def _listen_device(self, device):
        try:
            for event in device.read_loop():
                if not self.running:
                    break
                if event.type == evdev.ecodes.EV_KEY:
                    # Update pressed keys state
                    if event.value == 1:
                        self.pressed_keys.add(event.code)
                    elif event.value == 0:
                        self.pressed_keys.discard(event.code)
                        
                    # If it's a list (combo or sequence)
                    if isinstance(self.keycode, list):
                        # Detect if it's a multi-key sequence of the SAME key (Double Tap / Triple Tap)
                        if len(set(self.keycode)) == 1:
                            if event.value == 1 and event.code == self.keycode[0]:
                                current_time = time.time()
                                time_diff = current_time - self.last_tap_time
                                if time_diff < 0.05:
                                    pass
                                elif time_diff < self.double_tap_threshold:
                                    self.tap_count += 1
                                    self.last_tap_time = current_time
                                    if self.tap_count >= len(self.keycode):
                                        self.tap_count = 0
                                        self.on_trigger_callback()
                                else:
                                    self.tap_count = 1
                                    self.last_tap_time = current_time
                        else:
                            # It's a simultaneous combo (e.g. Ctrl + Shift + R)
                            if event.value == 1 and all(k in self.pressed_keys for k in self.keycode):
                                self.on_trigger_callback()
                            
                    # If it's a single key (single tap)
                    elif isinstance(self.keycode, int):
                        if event.value == 1 and event.code == self.keycode:
                            # SINGLE TAP triggers immediately
                            self.on_trigger_callback()
        except OSError:
            pass  # Device disconnected

    def start(self):
        self.running = True
        keyboards = self.find_keyboards()
        if not keyboards:
            print("Warning: No keyboards found or insufficient permissions to read /dev/input/event*.")
            print("Please ensure your user is in the 'input' group: sudo usermod -aG input $USER")
            return
            
        for kb in keyboards:
            t = threading.Thread(target=self._listen_device, args=(kb,), daemon=True)
            t.start()

    def stop(self):
        self.running = False
