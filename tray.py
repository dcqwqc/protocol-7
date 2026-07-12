import os
import sys
import pystray
import subprocess
import time
import sounddevice as sd
from PIL import Image, ImageDraw
from config import load_config, save_config

APP_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_PY = os.path.join(APP_DIR, "main.py")

def create_image():
    config = load_config()
    accent = config.get("accent_color", "#00ffcc").lstrip('#')
    try:
        rgb = tuple(int(accent[i:i+2], 16) for i in (0, 2, 4))
    except Exception:
        rgb = (0, 255, 204) # fallback
        
    image = Image.new('RGBA', (64, 64), color = (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    d.ellipse((20, 10, 44, 38), fill=rgb)
    d.rectangle((30, 48, 34, 58), fill=rgb)
    d.rectangle((20, 56, 44, 60), fill=rgb)
    d.arc((14, 20, 50, 48), start=0, end=180, fill=rgb, width=4)
    return image

def on_settings(icon, item):
    subprocess.Popen([sys.executable, MAIN_PY, "--settings"], cwd=APP_DIR)

def do_restart(parent_pid):
    time.sleep(0.5) # Give the GTK main loop time to completely destroy the icon
    import signal
    if parent_pid > 0:
        try:
            os.kill(parent_pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    time.sleep(0.5) # Give main.py time to die
    subprocess.Popen([sys.executable, MAIN_PY], cwd=APP_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, start_new_session=True)
    os._exit(0)

def restart_app(icon):
    import threading
    parent_pid = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    threading.Thread(target=do_restart, args=(parent_pid,), daemon=False).start()
    icon.stop()

def on_quit(icon, item):
    icon.stop()
    if len(sys.argv) > 1:
        parent_pid = int(sys.argv[1])
        try:
            import signal
            os.kill(parent_pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    os._exit(0)

def set_device(device_id, icon):
    config = load_config()
    config["input_device"] = device_id
    save_config(config)
    restart_app(icon)

def make_device_callback(device_id):
    def callback(icon, item):
        set_device(device_id, icon)
    return callback

def get_history_items():
    from config import load_history
    import subprocess
    history = load_history()
    
    def copy_to_clipboard(text):
        try:
            subprocess.run(['wl-copy'], input=text.encode('utf-8'))
        except Exception:
            pass

    def make_history_callback(text):
        return lambda icon, item: copy_to_clipboard(text)
        
    items = []
    for entry in history[:10]:
        text = entry.get("text", "")
        if not text:
            continue
        display_text = text if len(text) < 40 else text[:37] + "..."
        items.append(pystray.MenuItem(display_text, make_history_callback(text)))
        
    if not items:
        items.append(pystray.MenuItem("No history yet", lambda icon, item: None, enabled=False))
        
    return items

def build_menu():
    devices = []
    try:
        for i, dev in enumerate(sd.query_devices()):
            if dev['max_input_channels'] > 0:
                devices.append((i, dev['name']))
    except Exception:
        pass
        
    config = load_config()
    
    mic_items = []
    # Default
    mic_items.append(pystray.MenuItem(
        "Default",
        make_device_callback(None),
        checked=lambda item: load_config().get("input_device", None) is None,
        radio=True
    ))
    
    for idx, name in devices:
        mic_items.append(pystray.MenuItem(
            f"{idx}: {name}",
            make_device_callback(idx),
            checked=lambda item, i=idx: load_config().get("input_device", None) == i,
            radio=True
        ))
        
    return pystray.Menu(
        pystray.MenuItem('History', pystray.Menu(get_history_items)),
        pystray.MenuItem('Microphone', pystray.Menu(*mic_items)),
        pystray.MenuItem('Settings', on_settings),
        pystray.MenuItem('Restart', restart_app),
        pystray.MenuItem('Quit', on_quit)
    )

if __name__ == "__main__":
    icon = pystray.Icon("WhisperFlow", create_image(), "Whisper Flow", build_menu())
    icon.run()
