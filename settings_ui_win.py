import customtkinter as ctk
import tkinter as tk
from tkinter import colorchooser
import sounddevice as sd
from config import save_config
import os

LANGUAGES = {
    "Auto Detect": "auto", "English": "en", "Spanish": "es", "French": "fr", "German": "de", "Italian": "it",
    "Portuguese": "pt", "Russian": "ru", "Japanese": "ja", "Korean": "ko", "Chinese": "zh",
    "Arabic": "ar", "Hindi": "hi", "Dutch": "nl", "Turkish": "tr", "Polish": "pl",
    "Swedish": "sv", "Danish": "da", "Finnish": "fi", "Norwegian": "no", "Greek": "el",
    "Thai": "th", "Vietnamese": "vi", "Indonesian": "id", "Hebrew": "he", "Bengali": "bn",
    "Romanian": "ro", "Czech": "cs", "Ukrainian": "uk", "Hungarian": "hu", "Malay": "ms"
}

TRANSLATE_TARGETS = {
    "None (Keep Original)": "",
    "English": "English", "Spanish": "Spanish", "French": "French", "German": "German",
    "Italian": "Italian", "Portuguese": "Portuguese", "Russian": "Russian", "Japanese": "Japanese",
    "Korean": "Korean", "Chinese": "Chinese", "Arabic": "Arabic", "Hindi": "Hindi",
    "Dutch": "Dutch", "Turkish": "Turkish", "Polish": "Polish", "Swedish": "Swedish",
    "Danish": "Danish", "Finnish": "Finnish", "Norwegian": "Norwegian", "Greek": "Greek",
    "Thai": "Thai", "Vietnamese": "Vietnamese", "Indonesian": "Indonesian", "Hebrew": "Hebrew",
    "Bengali": "Bengali", "Romanian": "Romanian", "Czech": "Czech", "Ukrainian": "Ukrainian",
    "Hungarian": "Hungarian", "Malay": "Malay"
}

def _load_downloaded_whisper_models():
    models = {
        "tiny.en (Fastest, English-only)": "tiny.en",
        "tiny (Fastest, Multi-language)": "tiny",
        "base.en (Fast, English-only)": "base.en",
        "base (Fast, Multi-language)": "base",
        "small.en (Balanced, English-only)": "small.en",
        "small (Balanced, Multi-language)": "small",
        "medium (Accurate, Multi-language)": "medium",
        "large-v3 (Most Accurate, Slowest)": "large-v3"
    }
    try:
        hf_hub_path = os.path.expanduser("~/.cache/huggingface/hub")
        if os.path.exists(hf_hub_path):
            for d in os.listdir(hf_hub_path):
                if d.startswith("models--"):
                    repo_id = d.replace("models--", "").replace("--", "/")
                    if "whisper" in repo_id.lower() and not any(repo_id.endswith(x) for x in ["tiny.en", "tiny", "base.en", "base", "small.en", "small", "medium", "large-v3", "large-v2"]):
                        models[repo_id + " (Downloaded)"] = repo_id
    except Exception:
        pass
    return models

MODELS = _load_downloaded_whisper_models()

class SettingsWindow(ctk.CTk):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.title("Protocol-7 Settings")
        self.geometry("650x850")
        
        ctk.set_appearance_mode("dark")
        self.accent = self.config.get("accent_color", "#00ffcc")
        self.card_color = "#2b2b2b"
        
        # Main scrollable frame
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.recording_hotkey = False
        # Normalize config hotkey
        old_name = self.config.get("hotkey_name", "ctrl").lower()
        if "keycode" in old_name:
            old_name = "ctrl" # fallback from old linux config
        self.current_keycode = old_name
        self.recorded_keys = []
        self.currently_held_keys = set()

        # -- Model Library --
        card1 = self.create_card("AI Models & Speed (Whisper)")
        
        self.whisper_type_combo = self.create_dropdown(card1, values=["Downloaded Models", "New Download (Custom HF Repo)"], command=self.on_whisper_type_changed)
        self.add_row(card1, "Source:", self.whisper_type_combo)
        
        self.whisper_container = ctk.CTkFrame(card1, fg_color="transparent")
        self.whisper_container.pack(fill="x")
        
        self.whisper_builtin_frame = ctk.CTkFrame(self.whisper_container, fg_color="transparent")
        self.model_keys = list(MODELS.keys())
        self.model_combo = self.create_dropdown(self.whisper_builtin_frame, values=self.model_keys)
        self.model_combo.pack(side="left", fill="x", expand=True)
        self.add_inner_row(self.whisper_builtin_frame, "Select Model:", self.model_combo)
        
        self.whisper_custom_frame = ctk.CTkFrame(self.whisper_container, fg_color="transparent")
        self.custom_whisper_entry = ctk.CTkEntry(self.whisper_custom_frame, placeholder_text="e.g. Systran/faster-whisper-large-v3")
        self.custom_whisper_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        whisper_apply_btn = ctk.CTkButton(self.whisper_custom_frame, text="Apply", width=80, fg_color=self.accent, text_color="black")
        whisper_apply_btn.pack(side="left")
        self.add_inner_row(self.whisper_custom_frame, "Repo ID:", self.custom_whisper_entry)
        
        is_whisper_custom = self.config.get("whisper_is_custom", False)
        if is_whisper_custom:
            self.whisper_type_combo.set("New Download (Custom HF Repo)")
            self.custom_whisper_entry.insert(0, self.config.get("custom_model", ""))
        else:
            self.whisper_type_combo.set("Downloaded Models")
            active_model = self.config.get("model_size", "tiny.en")
            for k, v in MODELS.items():
                if v == active_model:
                    self.model_combo.set(k)
                    break
        self.on_whisper_type_changed(self.whisper_type_combo.get())

        # -- Hotkey Configuration --
        card2 = self.create_card("Hotkey Configuration")
        self.hotkey_btn = ctk.CTkButton(card2, text=f"Click to Record Hotkey (Current: {self.current_keycode})", fg_color=self.accent, text_color="black", font=ctk.CTkFont(weight="bold"), command=self.on_record_hotkey)
        self.add_row(card2, "Dictation Key:", self.hotkey_btn)

        # -- Input Device --
        card3 = self.create_card("Microphone")
        self.devices = []
        try:
            host_apis = sd.query_hostapis()
            for i, dev in enumerate(sd.query_devices()):
                if dev['max_input_channels'] > 0:
                    api_name = host_apis[dev['hostapi']]['name']
                    if api_name in ("Windows WASAPI", "MME"):
                        name = dev['name'].replace(", Windows WASAPI", "").replace(", MME", "").strip()
                        if "Microsoft Sound Mapper" in name:
                            continue
                            
                        api_label = "WASAPI" if api_name == "Windows WASAPI" else "MME"
                        self.devices.append((i, f"[{api_label}] {name}"))
        except Exception:
            pass
            
        dev_strings = ["Default"] + [d[1] for d in self.devices]
        self.device_combo = self.create_dropdown(card3, values=dev_strings)
        
        active_dev = self.config.get("input_device", None)
        if active_dev is not None:
            for i, d in enumerate(self.devices):
                if d[0] == active_dev:
                    self.device_combo.set(d[1])
                    break
        self.add_row(card3, "Input Device:", self.device_combo)

        # -- Language & Translation --
        card4 = self.create_card("Language & Translation")
        self.lang_keys = list(LANGUAGES.keys())
        self.lang_combo = self.create_dropdown(card4, values=self.lang_keys)
        active_lang = "auto" if self.config.get("auto_detect_language", True) else self.config.get("language", "en")
        for k, v in LANGUAGES.items():
            if v == active_lang:
                self.lang_combo.set(k)
                break
        self.add_row(card4, "Spoken Language:", self.lang_combo)

        self.trans_keys = list(TRANSLATE_TARGETS.keys())
        self.trans_combo = self.create_dropdown(card4, values=self.trans_keys)
        active_trans = self.config.get("translate_target", "")
        if not active_trans and self.config.get("translate", False):
            active_trans = "English"
        for k, v in TRANSLATE_TARGETS.items():
            if v == active_trans:
                self.trans_combo.set(k)
                break
        self.add_row(card4, "Translate To:", self.trans_combo)

        # -- AI Grammar Engine Backend --
        card5 = self.create_card("AI Grammar Engine")
        self.backend_combo = self.create_dropdown(card5, values=["Built-in (Llama.cpp)", "Ollama Server"], command=self.on_backend_changed)
        self.add_row(card5, "Engine Type:", self.backend_combo)

        self.backend_container = ctk.CTkFrame(card5, fg_color="transparent")
        self.backend_container.pack(fill="x", pady=5)

        # Llama.cpp Settings
        self.llama_frame = ctk.CTkFrame(self.backend_container, fg_color="transparent")
        self.llama_repo_entry = ctk.CTkEntry(self.llama_frame)
        self.llama_repo_entry.insert(0, self.config.get("llama_repo", "bartowski/Llama-3.2-3B-Instruct-GGUF"))
        self.add_inner_row(self.llama_frame, "HF Repo ID:", self.llama_repo_entry)
        
        self.llama_file_entry = ctk.CTkEntry(self.llama_frame)
        self.llama_file_entry.insert(0, self.config.get("llama_filename", "Llama-3.2-3B-Instruct-Q4_K_M.gguf"))
        self.add_inner_row(self.llama_frame, "GGUF Filename:", self.llama_file_entry)

        # Ollama Settings
        self.ollama_frame = ctk.CTkFrame(self.backend_container, fg_color="transparent")
        self.ollama_endpoint_entry = ctk.CTkEntry(self.ollama_frame)
        self.ollama_endpoint_entry.insert(0, self.config.get("ollama_endpoint", "http://127.0.0.1:11434"))
        self.add_inner_row(self.ollama_frame, "Endpoint:", self.ollama_endpoint_entry)
        
        ollama_scan_frame = ctk.CTkFrame(self.ollama_frame, fg_color="transparent")
        self.ollama_entry = ctk.CTkEntry(ollama_scan_frame)
        self.ollama_entry.insert(0, self.config.get("ollama_model", "llama3.2"))
        self.ollama_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.ollama_scan_btn = ctk.CTkButton(ollama_scan_frame, text="Scan", width=80, fg_color=self.accent, text_color="black", command=self.on_scan_clicked)
        self.ollama_scan_btn.pack(side="left")
        self.add_inner_row(self.ollama_frame, "Model:", ollama_scan_frame)

        active_backend = self.config.get("llm_backend", "Built-in (Llama.cpp)")
        self.backend_combo.set(active_backend)
        self.on_backend_changed(active_backend)

        # -- System Prompt --
        card6 = self.create_card("System Prompt")
        default_prompt = """You are an expert Speech-to-Text (STT) editor. Your sole task is to process raw voice transcripts and output the speaker's final, intended message in clean, readable text.

### Core Directives:
1. Eliminate Disfluencies: Remove all filler words (um, uh, ah, like, you know) and stutters/repeated words (e.g., "I I went" becomes "I went").
2. Apply Self-Corrections: When the speaker changes their mind mid-sentence (using phrases like "I mean," "actually," "no wait"), strictly apply their final intent and delete the abandoned thought.
3. Fix Phonetic Typos: Correct obvious transcription errors based on context (e.g., "the dog parked" becomes "the dog barked").
4. Add Mechanics: Apply proper capitalization and punctuation to make the sentence grammatically correct.
5. Preserve Meaning: Do not summarize, paraphrase, or change the user's intended tone or vocabulary. Only fix the mechanics of the speech.
6. Absolute Constraint: Output ONLY the final cleaned text. Do not include introductory phrases, quotes, or explanations. 

### Examples:

Input: uh hey what's up man I I was wondering if you wanted to go
Output: Hey, what's up man? I was wondering if you wanted to go.

Input: set a timer for 10 or actually 15 minutes
Output: Set a timer for 15 minutes.

Input: let's meet at 7 a.m. oh wait i mean 8 a.m. no actually let's do noon in Los Angeles
Output: Let's meet at noon in Los Angeles.

Input: remind me to buy eggs milk and oh wait i don't need milk just eggs and bread
Output: Remind me to buy eggs and bread.

Input: the dog parked loudly at the mailman
Output: The dog barked loudly at the mailman."""
        self.prompt_text = ctk.CTkTextbox(card6, height=150, fg_color="#1e1e1e", border_color="#444", border_width=1)
        self.prompt_text.insert("1.0", self.config.get("llm_system_prompt", default_prompt))
        self.prompt_text.pack(fill="x", pady=10, padx=10)

        # -- Appearance & Integration --
        card7 = self.create_card("Preferences")
        self.color_btn = ctk.CTkButton(card7, text="Pick Accent Color", fg_color=self.accent, text_color="black", font=ctk.CTkFont(weight="bold"), command=self.on_pick_color)
        self.add_row(card7, "Appearance:", self.color_btn)

        self.autostart_check = ctk.CTkCheckBox(card7, text="Autostart on Login", fg_color=self.accent)
        if self.config.get("autostart", False): self.autostart_check.select()
        self.autostart_check.pack(anchor="w", padx=10, pady=(10, 5))
        
        self.tray_check = ctk.CTkCheckBox(card7, text="Show in System Tray", fg_color=self.accent)
        if self.config.get("show_tray", True): self.tray_check.select()
        self.tray_check.pack(anchor="w", padx=10, pady=5)
        
        self.llm_check = ctk.CTkCheckBox(card7, text="Enable AI Smart Clean-up & Correction", fg_color=self.accent)
        if self.config.get("enable_llm_rewrite", True): self.llm_check.select()
        self.llm_check.pack(anchor="w", padx=10, pady=(5, 10))

        # -- Actions --
        action_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        action_frame.pack(fill="x", pady=20)
        
        history_btn = ctk.CTkButton(action_frame, text="View History", command=self.on_view_history, fg_color=self.accent, text_color="black")
        history_btn.pack(side="left", expand=True, fill="x", padx=(0, 5))
        
        logs_btn = ctk.CTkButton(action_frame, text="View Logs", command=self.on_view_logs, fg_color=self.accent, text_color="black")
        logs_btn.pack(side="left", expand=True, fill="x", padx=(5, 0))
        
        save_btn = ctk.CTkButton(self.scroll_frame, text="Save & Exit", height=45, fg_color=self.accent, text_color="black", font=ctk.CTkFont(size=15, weight="bold"), command=self.on_save_clicked)
        save_btn.pack(fill="x", pady=(0, 30))
        
        self.bind("<KeyPress>", self.on_key_pressed)
        self.bind("<KeyRelease>", self.on_key_released)

    def create_dropdown(self, parent, values, command=None):
        return ctk.CTkOptionMenu(
            parent,
            values=values,
            command=command,
            fg_color=self.accent,
            button_color=self.accent,
            button_hover_color=self.accent,
            dropdown_fg_color="#333333",
            dropdown_hover_color=self.accent
        )

    def create_card(self, title):
        card = ctk.CTkFrame(self.scroll_frame, fg_color=self.card_color, corner_radius=10)
        card.pack(fill="x", pady=10)
        lbl = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=16, weight="bold"), text_color=self.accent)
        lbl.pack(anchor="w", padx=15, pady=(15, 5))
        return card

    def add_row(self, parent, label_text, widget):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=15, pady=8)
        lbl = ctk.CTkLabel(frame, text=label_text, width=130, anchor="w")
        lbl.pack(side="left")
        widget.pack(side="left", fill="x", expand=True)

    def add_inner_row(self, parent, label_text, widget):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=4, padx=15)
        lbl = ctk.CTkLabel(frame, text=label_text, width=130, anchor="w")
        lbl.pack(side="left")
        widget.pack(side="left", fill="x", expand=True)

    def on_whisper_type_changed(self, value):
        if value == "Downloaded Models":
            self.whisper_builtin_frame.pack(fill="x")
            self.whisper_custom_frame.pack_forget()
        else:
            self.whisper_custom_frame.pack(fill="x")
            self.whisper_builtin_frame.pack_forget()

    def on_backend_changed(self, value):
        if value == "Built-in (Llama.cpp)":
            self.llama_frame.pack(fill="x")
            self.ollama_frame.pack_forget()
        else:
            self.ollama_frame.pack(fill="x")
            self.llama_frame.pack_forget()

    def on_pick_color(self):
        color = colorchooser.askcolor(title="Choose Accent Color", initialcolor=self.accent)[1]
        if color:
            self.accent = color
            self.color_btn.configure(fg_color=color)

    def on_scan_clicked(self):
        endpoint = self.ollama_endpoint_entry.get().strip().rstrip("/")
        try:
            import urllib.request
            import json
            req = urllib.request.Request(f"{endpoint}/api/tags")
            with urllib.request.urlopen(req, timeout=2.0) as response:
                data = json.loads(response.read().decode('utf-8'))
                models = [m["name"] for m in data.get("models", [])]
                if models:
                    self.ollama_entry.delete(0, 'end')
                    self.ollama_entry.insert(0, models[0])
        except Exception:
            pass

    def on_view_history(self):
        hist_window = ctk.CTkToplevel(self)
        hist_window.title("Dictation History")
        hist_window.geometry("500x400")
        textbox = ctk.CTkTextbox(hist_window)
        textbox.pack(fill="both", expand=True, padx=10, pady=10)
        try:
            from config import load_history
            history = load_history()
            if not history:
                textbox.insert("1.0", "No history found.")
            else:
                import datetime
                lines = []
                for entry in history:
                    text = entry.get("text", "")
                    ts = entry.get("timestamp", 0)
                    dt = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
                    lines.append(f"[{dt}]\n{text}\n")
                textbox.insert("1.0", "\n".join(lines))
        except Exception as e:
            textbox.insert("1.0", f"Error loading history: {e}")

    def on_view_logs(self):
        log_window = ctk.CTkToplevel(self)
        log_window.title("Protocol-7 Logs")
        log_window.geometry("600x400")
        textbox = ctk.CTkTextbox(log_window)
        textbox.pack(fill="both", expand=True, padx=10, pady=10)
        try:
            log_path = os.path.join(os.environ.get("TEMP", "/tmp"), "whisper_log.txt")
            with open(log_path, "r") as f:
                content = f.read()
            textbox.insert("1.0", content)
            textbox.see("end")
        except Exception:
            textbox.insert("1.0", "No logs found yet.")

    def on_record_hotkey(self):
        if self.recording_hotkey:
            return
        self.recording_hotkey = True
        self.recorded_keys = []
        self.currently_held_keys = set()
        self.hotkey_btn.configure(text="Press keys now...", fg_color="#ff3366", text_color="white")
        self.after(3000, self.stop_recording_hotkey)

    def on_key_pressed(self, event):
        if self.recording_hotkey:
            key = event.keysym.lower()
            if "control" in key: key = "ctrl"
            elif "shift" in key: key = "shift"
            elif "alt" in key: key = "alt"
            
            if key not in self.currently_held_keys:
                self.currently_held_keys.add(key)
                self.recorded_keys.append(key)
                
                # Double tap logic display
                if len(self.recorded_keys) > 1 and len(set(self.recorded_keys)) == 1:
                    taps = ["Single", "Double", "Triple", "Quadruple"]
                    idx = min(len(self.recorded_keys) - 1, 3)
                    display = f"{taps[idx]} {self.recorded_keys[0]}"
                else:
                    display = " + ".join(self.recorded_keys)
                self.hotkey_btn.configure(text=f"Recording: {display}")

    def on_key_released(self, event):
        if self.recording_hotkey:
            key = event.keysym.lower()
            if "control" in key: key = "ctrl"
            elif "shift" in key: key = "shift"
            elif "alt" in key: key = "alt"
            self.currently_held_keys.discard(key)

    def stop_recording_hotkey(self):
        self.recording_hotkey = False
        if self.recorded_keys:
            if len(set(self.recorded_keys)) == 1:
                # E.g. "ctrl" (even if double tap, store as ctrl)
                self.current_keycode = self.recorded_keys[0]
            else:
                self.current_keycode = "+".join(self.recorded_keys)
            self.config["hotkey_name"] = self.current_keycode
            
        display_name = self.current_keycode
        if self.recorded_keys and len(self.recorded_keys) > 1 and len(set(self.recorded_keys)) == 1:
            taps = ["Single", "Double", "Triple", "Quadruple"]
            idx = min(len(self.recorded_keys) - 1, 3)
            display_name = f"{taps[idx]} {self.recorded_keys[0]}"
            
        self.hotkey_btn.configure(text=f"Click to Record Hotkey (Current: {display_name})", fg_color=self.accent, text_color="black")

    def on_save_clicked(self):
        self.config["llm_system_prompt"] = self.prompt_text.get("1.0", "end-1c")
        
        is_whisper_custom = self.whisper_type_combo.get() == "New Download (Custom HF Repo)"
        self.config["whisper_is_custom"] = is_whisper_custom
        if is_whisper_custom:
            self.config["model_size"] = self.custom_whisper_entry.get()
            self.config["custom_model"] = self.custom_whisper_entry.get()
        else:
            self.config["model_size"] = MODELS[self.model_combo.get()]
            
        self.config["llama_repo"] = self.llama_repo_entry.get()
        self.config["llama_filename"] = self.llama_file_entry.get()
        self.config["hotkey_name"] = self.current_keycode
        self.config["accent_color"] = self.accent
        
        dev_val = self.device_combo.get()
        if dev_val == "Default":
            self.config["input_device"] = None
        else:
            self.config["input_device"] = int(dev_val.split(":")[0])
            
        lang_val = LANGUAGES[self.lang_combo.get()]
        if lang_val == "auto":
            self.config["auto_detect_language"] = True
            self.config["language"] = "en"
        else:
            self.config["auto_detect_language"] = False
            self.config["language"] = lang_val
            
        trans_val = TRANSLATE_TARGETS[self.trans_combo.get()]
        self.config["translate_target"] = trans_val
        self.config["translate"] = (trans_val == "English")
        
        self.config["autostart"] = self.autostart_check.get() == 1
        self.config["show_tray"] = self.tray_check.get() == 1
        self.config["enable_llm_rewrite"] = self.llm_check.get() == 1
        self.config["llm_backend"] = self.backend_combo.get()
        self.config["ollama_endpoint"] = self.ollama_endpoint_entry.get()
        self.config["ollama_model"] = self.ollama_entry.get()
        
        save_config(self.config)
        
        import subprocess
        import sys
        APP_DIR = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(os.environ.get("TEMP", "/tmp"), "protocol7_restart.bat")
        with open(script_path, "w") as f:
            f.write("@echo off\n")
            f.write("timeout /t 1 /nobreak > nul\n")
            
            pid_file = os.path.join(APP_DIR, "app.pid")
            if os.path.exists(pid_file):
                try:
                    with open(pid_file, "r") as pf:
                        pid = pf.read().strip()
                    if pid:
                        f.write(f"taskkill /PID {pid} /F > nul 2>&1\n")
                except: pass
                
            f.write(f"taskkill /F /IM python.exe /FI \"WINDOWTITLE eq Protocol-7*\" > nul 2>&1\n")
            f.write(f"cd /d \"{APP_DIR}\"\n")
            f.write(f"start \"\" \"{sys.executable}\" main.py\n")
            
        subprocess.Popen([script_path], creationflags=subprocess.CREATE_NO_WINDOW)
        self.destroy()

def run_settings(config):
    app = SettingsWindow(config)
    app.mainloop()
