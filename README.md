# Whisper Flow

A standalone Wayland-native Linux desktop application for AI-powered voice dictation.

## Features
- **Wayland Native**: Uses GTK4 layer-shell to overlay a floating window at the bottom of the screen.
- **Global Hotkey**: Double-tap `Ctrl` to trigger the dictation anywhere in Wayland.
- **Local AI**: Powered by `faster-whisper` for fast, offline transcription.
- **Auto-Paste**: Instantly pastes the transcribed text into your currently focused window using `wtype`.
- **Customizable**: Change themes, languages, translation settings, and models via the settings UI.

## Requirements
- `python3`
- `wtype` (for pasting text)
- GTK4 and GObject Introspection packages
- `gtk4-layer-shell`
- Input group permissions (see Setup)

## Setup

1. Install system dependencies (Ubuntu/Debian example):
   ```bash
   sudo apt install wtype python3-gi gir1.2-gtk-4.0 gir1.2-gtk4layershell-1.0 libcairo2-dev libgirepository1.0-dev portaudio19-dev python3-dev
   ```

2. Add your user to the `input` group to allow global hotkey detection via `evdev`:
   ```bash
   sudo usermod -aG input $USER
   ```
   *Note: You may need to log out and log back in, or reboot, for this group change to take effect.*

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the app:
   ```bash
   python main.py
   ```
   The app will run in the background. Double-tap `Ctrl` to start dictating. Double-tap `Ctrl` again to stop and paste.

## Configuration
Right-click the tray icon or run with `--settings` to access the configuration menu, where you can select the microphone, change the active model, and set translation preferences.
