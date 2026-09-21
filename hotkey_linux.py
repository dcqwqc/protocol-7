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
        # Widened from 0.4: a double tap that lands slower than this is read as
        # two separate first-taps and nothing happens, which is most of what
        # 'sometimes it works' felt like.
        self.double_tap_threshold = 0.6  # seconds
        # Guards the tap counters. One listener thread runs per input device,
        # and they all share this state -- two devices reporting the same key,
        # or a virtual keyboard echoing it, could otherwise interleave and
        # leave the count somewhere neither tap expected.
        self._tap_lock = __import__('threading').Lock()
        self.tap_count = 0
        
        # For multi-key combos
        self.pressed_keys = set()
        
    def find_keyboards(self):
        keyboards = []
        for path in evdev.list_devices():
            try:
                dev = evdev.InputDevice(path)
                capabilities = dev.capabilities()
                if evdev.ecodes.EV_KEY in capabilities:
                    if evdev.ecodes.KEY_A in capabilities[evdev.ecodes.EV_KEY]:
                        keyboards.append(dev)
            except Exception:
                continue
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
                                fire = False
                                with self._tap_lock:
                                    time_diff = current_time - self.last_tap_time
                                    # A tighter dead zone: 50ms was wide enough
                                    # to swallow a genuinely quick second tap.
                                    if time_diff < 0.03:
                                        pass
                                    elif time_diff < self.double_tap_threshold:
                                        self.tap_count += 1
                                        self.last_tap_time = current_time
                                        if self.tap_count >= len(self.keycode):
                                            self.tap_count = 0
                                            fire = True
                                    else:
                                        self.tap_count = 1
                                        self.last_tap_time = current_time
                                if fire:
                                    self.on_trigger_callback()
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

    def _watchdog(self):
        active_threads = {}
        while self.running:
            try:
                keyboards = self.find_keyboards()
                current_paths = {kb.path: kb for kb in keyboards}
                
                # Start threads for new keyboards
                for path, kb in current_paths.items():
                    if path not in active_threads or not active_threads[path].is_alive():
                        t = threading.Thread(target=self._listen_device, args=(kb,), daemon=True)
                        t.start()
                        active_threads[path] = t
            except Exception as e:
                pass # Prevent any OS/udev race conditions from killing the watchdog
                
            time.sleep(2.0)  # Check every 2 seconds for new/reconnected devices

    def start(self):
        self.running = True
        t = threading.Thread(target=self._watchdog, daemon=True)
        t.start()

    def stop(self):
        self.running = False
