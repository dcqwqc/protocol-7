#!/bin/bash
set -e

echo "======================================"
echo "    Whisper Flow Installer            "
echo "======================================"

# Detect OS
if [ -f /etc/debian_version ]; then
    echo "Detected Debian/Ubuntu-based system."
    echo "Installing system dependencies..."
    sudo apt update
    sudo apt install -y wtype python3-venv python3-gi gir1.2-gtk-4.0 gir1.2-gtk4layershell-1.0 libcairo2-dev libgirepository1.0-dev portaudio19-dev python3-dev
elif [ -f /etc/arch-release ]; then
    echo "Detected Arch Linux."
    echo "Installing system dependencies..."
    sudo pacman -Sy --noconfirm wtype python-virtualenv python-gobject gtk4 gtk4-layer-shell cairo gobject-introspection portaudio
elif [ -f /etc/fedora-release ]; then
    echo "Detected Fedora."
    echo "Installing system dependencies..."
    sudo dnf install -y wtype python3-virtualenv python3-gobject gtk4 gtk4-layer-shell cairo-devel gobject-introspection-devel portaudio-devel python3-devel
else
    echo "Unsupported Linux distribution. Please install dependencies manually:"
    echo "wtype, python3-venv, gtk4, gtk4-layer-shell, cairo-dev, gobject-introspection-dev, portaudio-dev"
fi

# Setup input group
echo "Adding user to input group for global hotkey support..."
sudo usermod -aG input $USER
echo "[IMPORTANT] If hotkeys do not work immediately, you may need to logout and log back in, or reboot, for the group permission to apply!"

# Setup virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "======================================"
echo "    Installation Complete!            "
echo "======================================"
echo "To run the application, execute: ./venv/bin/python main.py"
