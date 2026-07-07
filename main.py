import sys
import threading
import subprocess
from gi.repository import GLib

from config import load_config
from hotkey import HotkeyListener
from audio import AudioRecorder
from whisper_engine import WhisperEngine
from ui import UIManager

class WhisperFlowApp:
    def __init__(self):
        self.config = load_config()
        self.audio_recorder = AudioRecorder(device_id=self.config.get("input_device"))
        self.whisper_engine = WhisperEngine(self.config)
        self.ui_manager = UIManager(self.config, self.audio_recorder)
        
        self.is_active = False
        
        # KEY_LEFTCTRL is 29
        self.hotkey = HotkeyListener(self.config.get("hotkey_keycode", 29), self.on_hotkey_trigger)
        
    def on_hotkey_trigger(self):
        if not self.is_active:
            # Start dictation
            print("Dictation started")
            self.is_active = True
            self.audio_recorder.start_recording()
            
            # Show UI on main thread
            GLib.idle_add(self.ui_manager.show)
        else:
            # Stop dictation
            print("Dictation stopped")
            self.is_active = False
            
            # Update UI state to processing
            GLib.idle_add(self.ui_manager.set_processing_state)
            
            # Process in background so we don't block GTK main loop
            threading.Thread(target=self.process_audio, daemon=True).start()

    def process_audio(self):
        audio_data = self.audio_recorder.stop_recording()
        
        if len(audio_data) > 0:
            text = self.whisper_engine.transcribe(audio_data)
            if text:
                print(f"Transcribed: {text}")
                self.paste_text(text)
            else:
                print("No text transcribed.")
        else:
            print("No audio data recorded.")
            
        # Hide UI
        GLib.idle_add(self.ui_manager.hide)

    def paste_text(self, text):
        try:
            # We use wtype to simulate keyboard typing/pasting
            # -M ctrl -k v etc can also be used if clipboard is populated, 
            # but wtype text is more direct.
            subprocess.run(["wtype", text], check=True)
        except Exception as e:
            print(f"Error pasting text with wtype: {e}")
            print("Make sure wtype is installed and you are running under a Wayland compositor.")

    def run(self):
        print("Starting Whisper Flow...")
        
        # Pre-load model in background to make first dictation fast
        threading.Thread(target=self.whisper_engine._load_model, daemon=True).start()
        
        # Start hotkey listener
        self.hotkey.start()
        
        # Run GTK main loop (blocks until app exits)
        try:
            self.ui_manager.run()
        except KeyboardInterrupt:
            print("Exiting...")
        finally:
            self.hotkey.stop()

if __name__ == "__main__":
    from config import load_config
    config = load_config()
    
    if "--settings" in sys.argv:
        from settings_ui import run_settings
        run_settings(config)
        sys.exit(0)
        
    app = WhisperFlowApp()
    app.run()
