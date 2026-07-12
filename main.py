import sys
import threading
import subprocess
from gi.repository import GLib

from config import load_config
from hotkey import HotkeyListener
from audio import AudioRecorder
from whisper_engine import WhisperEngine
from ui import UIManager
from llm_rewriter import LLMRewriter

class TrayIcon:
    def __init__(self, app):
        self.app = app
        self.process = None

    def start(self):
        if not self.app.config.get("show_tray", True):
            return
        import subprocess
        import sys
        import os
        APP_DIR = os.path.dirname(os.path.abspath(__file__))
        tray_path = os.path.join(APP_DIR, "tray.py")
        self.tray_log = open(os.path.join(APP_DIR, "tray_crash.log"), "w")
        self.process = subprocess.Popen([sys.executable, tray_path, str(os.getpid())], cwd=APP_DIR, stdout=self.tray_log, stderr=subprocess.STDOUT)

    def stop(self):
        if self.process:
            self.process.terminate()

class WhisperFlowApp:
    def __init__(self):
        self.config = load_config()
        self.audio_recorder = AudioRecorder(device_id=self.config.get("input_device"))
        self.whisper_engine = WhisperEngine(self.config)
        self.llm_rewriter = LLMRewriter(self.config)
        self.ui_manager = UIManager(self.config, self.audio_recorder)
        self.tray = TrayIcon(self)
        
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
        import time
        import traceback
        start_time = time.time()
        
        try:
            audio_data = self.audio_recorder.stop_recording()
            audio_time = time.time()
            print(f"[Timer] Audio collected and resampled in {audio_time - start_time:.2f}s (Array length: {len(audio_data)})")
            
            if len(audio_data) > 0:
                transcribe_start = time.time()
                text = self.whisper_engine.transcribe(audio_data)
                transcribe_end = time.time()
                print(f"[Timer] Whisper Transcription took {transcribe_end - transcribe_start:.2f}s")
                
                if text:
                    print(f"Transcribed: {text}")
                    
                    llm_start = time.time()
                    clean_text = self.llm_rewriter.rewrite(text)
                    llm_end = time.time()
                    print(f"[Timer] LLM Rewriting took {llm_end - llm_start:.2f}s")
                    
                    if clean_text != text:
                        print(f"Rewritten to: {clean_text}")
                    
                    # Hide UI before pasting so Wayland compositor restores focus to terminal
                    GLib.idle_add(self.ui_manager.hide)
                    time.sleep(0.4) # Wait 400ms to ensure the user has physically released the Ctrl key
                    
                    if clean_text.strip():
                        from config import add_history
                        add_history(clean_text)
                        
                        paste_start = time.time()
                        self.paste_text(clean_text)
                        print(f"[Timer] Paste operation took {time.time() - paste_start:.2f}s")
                    
                    print(f"[Timer] Total Pipeline Execution Time: {time.time() - start_time:.2f}s")
                    return
                else:
                    print("No text transcribed.")
            else:
                print("No audio data recorded.")
                
            print(f"[Timer] Pipeline Failed/Empty, Total Time: {time.time() - start_time:.2f}s")
            
        except Exception as e:
            print(f"[ERROR] Fatal error in audio processing pipeline: {e}")
            traceback.print_exc()
        finally:
            # ALWAYS hide the UI, no matter what happens, to prevent infinite loading animation!
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
        
        # Pre-load models in background
        threading.Thread(target=self.whisper_engine._load_model, daemon=True).start()
        threading.Thread(target=self.llm_rewriter.load_model, daemon=True).start()
        
        # Start hotkey and tray
        self.hotkey.start()
        self.tray.start()
        
        # Run GTK main loop (blocks until app exits)
        try:
            self.ui_manager.run()
        except KeyboardInterrupt:
            print("Exiting...")
        finally:
            self.hotkey.stop()
            self.tray.stop()
            
    def quit(self):
        self.ui_manager.app.quit()
        
    def open_settings(self):
        import subprocess
        subprocess.Popen([sys.executable, sys.argv[0], "--settings"])

if __name__ == "__main__":
    from config import load_config
    config = load_config()
    
    if "--settings" in sys.argv:
        from settings_ui import run_settings
        run_settings(config)
        sys.exit(0)
        
    app = WhisperFlowApp()
    app.run()
