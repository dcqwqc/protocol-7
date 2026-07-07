import evdev
import threading
import time
import os

class HotkeyListener:
    def __init__(self, keycode, on_trigger_callback):
        """
        keycode: evdev keycode (e.g., evdev.ecodes.KEY_LEFTCTRL)
        on_trigger_callback: function to call when double tap is detected
        """
        self.keycode = keycode
        self.on_trigger_callback = on_trigger_callback
        self.running = False
        self.last_tap_time = 0
        self.double_tap_threshold = 0.4  # seconds

    def find_keyboards(self):
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        keyboards = []
        for dev in devices:
            capabilities = dev.capabilities()
            if evdev.ecodes.EV_KEY in capabilities:
                # Basic check if it has keyboard keys (e.g., KEY_A)
                if evdev.ecodes.KEY_A in capabilities[evdev.ecodes.EV_KEY]:
                    keyboards.append(dev)
        return keyboards

    def _listen_device(self, device):
        try:
            for event in device.read_loop():
                if not self.running:
                    break
                if event.type == evdev.ecodes.EV_KEY:
                    # Key pressed
                    if event.value == 1 and event.code == self.keycode:
                        current_time = time.time()
                        if current_time - self.last_tap_time < self.double_tap_threshold:
                            self.last_tap_time = 0  # Reset
                            self.on_trigger_callback()
                        else:
                            self.last_tap_time = current_time
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
