# Protocol 7
Wispr Flow but local kinda

<img width="134" height="57" alt="image" src="https://github.com/user-attachments/assets/9ac9c6e1-4fd1-4c3e-a183-014eacf854b5" />
<img width="1913" height="1078" alt="image" src="https://github.com/user-attachments/assets/8be086a8-bcd9-4c1a-88de-8f56f953d7de" />

A standalone Wayland-native Linux desktop application for AI-powered voice dictation.

## Features
- **Wayland Native**: Uses GTK4 layer-shell to overlay a floating window at the bottom of the screen.
- **Global Hotkey**: Double-tap `Ctrl` to trigger the dictation anywhere in Wayland.
- **Local AI**: Powered by `faster-whisper` for fast, offline transcription.
- **AI Grammar Engine**: Features a real-time LLM backend (Built-in LLaMA.cpp or remote Ollama Server) to correct grammar, phonetic typos, and apply self-corrections on the fly.
- **Auto-Paste**: Instantly pastes the transcribed text into your currently focused window using `wtype`.
- **Customizable**: Change themes, languages, translation settings, and models visually via the Settings UI.

## Requirements
- `python3`
- `wtype` (for pasting text in Wayland)
- GTK4 and GObject Introspection packages
- `gtk4-layer-shell`

## Setup

We provide a universal install script for Debian/Ubuntu, Arch, and Fedora based systems.

1. Clone the repository and run the install script:
   ```bash
   git clone https://github.com/dcqwqc/whisper-flow.git
   cd whisper-flow
   ./install.sh
   ```

2. *Note: The install script adds your user to the `input` group to allow global hotkey detection via `evdev`. You may need to log out and log back in, or reboot, for this group change to take effect.*

3. Run the app:
   ```bash
   ./venv/bin/python main.py
   ```
   The app will run in the background. Double-tap `Ctrl` to start dictating. Double-tap `Ctrl` again to stop and paste.

## Configuration & Custom Models
Right-click the tray icon or run with `--settings` to access the configuration menu.

All model management is handled seamlessly within the Settings UI:
- **Whisper Models**: Choose from built-in models or input any HuggingFace Repo ID (e.g. `Systran/faster-whisper-large-v3`). The app will dynamically scan your HuggingFace cache to populate dropdowns with models you've already downloaded.
- **Local LLM Models**: Select "Built-in (Llama.cpp)" and provide any GGUF filename and HuggingFace Repo.
- **Ollama**: Connect to a local or remote Ollama server. Click the "Scan" button to automatically pull down all models available on your server.
- **AI System Prompt**: Fully rewrite and customize the exact prompt instructions the AI follows using the built-in text editor.
- **Live Logs**: Open the Developer Logs window directly from the settings menu to watch the RAW audio get transcribed and cleaned in real-time.

## License
MIT License
