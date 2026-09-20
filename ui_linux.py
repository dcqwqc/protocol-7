import ctypes
try:
    ctypes.CDLL("libgtk4-layer-shell.so", mode=ctypes.RTLD_GLOBAL)
except Exception:
    pass

import gi
import math
import random
import sys
gi.require_version('Gtk', '4.0')
gi.require_version('Gtk4LayerShell', '1.0')
from gi.repository import Gtk, Gtk4LayerShell, GLib, Gdk, cairo

def hex_to_rgba(hex_code, alpha=1.0):
    hex_code = hex_code.lstrip('#')
    if len(hex_code) == 6:
        r = int(hex_code[0:2], 16) / 255.0
        g = int(hex_code[2:4], 16) / 255.0
        b = int(hex_code[4:6], 16) / 255.0
        return r, g, b, alpha
    return 0.0, 1.0, 0.8, alpha # Default tealish

class Visualizer(Gtk.DrawingArea):
    def __init__(self, config, audio_recorder):
        super().__init__()
        self.set_size_request(100, 24)
        self.config = config
        self.audio_recorder = audio_recorder
        self.set_draw_func(self.on_draw)
        self.bars = [0.0] * 10
        self.is_processing = False
        self.wave_offset = 0.0
        
        # Start a timeout to redraw the visualizer at 60fps
        GLib.timeout_add(16, self.update_bars)

    def update_bars(self):
        if self.is_processing:
            self.wave_offset += 0.15
            for i in range(len(self.bars)):
                # Create a smooth sine wave across the bars
                target = (math.sin(self.wave_offset + i * 0.5) + 1.0) * 0.5
                self.bars[i] += (target - self.bars[i]) * 0.3
            self.queue_draw()
            return True

        volume = self.audio_recorder.get_volume_level()
        
        # Lower threshold to pick up quiet mics
        if volume < 0.02:
            volume = 0.0
        else:
            # Apply a curve to significantly boost quiet sounds
            volume = min(1.0, volume ** 0.5)
            
        for i in range(len(self.bars)):
            # Simulating frequency bins: middle bars react most
            dist = abs(i - (len(self.bars) - 1) / 2.0)
            weight = max(0.3, 1.0 - (dist / (len(self.bars) / 2.0)))
            
            target = volume * weight * 1.8 # Scaled down multiplier since we boosted base volume
            if volume > 0:
                target *= random.uniform(0.85, 1.15)
                
            # Smoothly ease current bar towards target, much more responsive now
            self.bars[i] += (target - self.bars[i]) * 0.7
            
        self.queue_draw()
        return True

    def on_draw(self, area, cr, width, height):
        # Draw background (transparent)
        cr.set_operator(cairo.Operator.CLEAR)
        cr.paint()
        cr.set_operator(cairo.Operator.OVER)

        # Draw equalizer bars
        accent_color = self.config.get("accent_color", "#00ffcc")
        if self.config.get("use_caelestia_colors", False):
            caelestia = get_caelestia_colors()
            accent_color = caelestia.get("primary", accent_color)
            print(f"DEBUG CAELESTIA: primary='{accent_color}'")
        else:
            print(f"DEBUG CONFIG: accent_color='{accent_color}'")
        r, g, b, a = hex_to_rgba(accent_color)

        bar_width = width / len(self.bars)
        line_thickness = 5 # 100px width / 10 bars = 10px per slot. 5px thick means 5px gap.

        for i, val in enumerate(self.bars):
            bar_h = val * height * 0.7
            
            # Safe maximum height so rounded caps don't get clipped by drawing bounds
            max_h = height - line_thickness
            
            if bar_h > max_h:
                bar_h = max_h
            elif bar_h < line_thickness:
                bar_h = line_thickness
            
            x = i * bar_width + bar_width / 2
            y_start = height / 2 - bar_h / 2
            y_end = height / 2 + bar_h / 2

            cr.set_source_rgba(r, g, b, 0.8)
            cr.set_line_width(line_thickness)
            cr.set_line_cap(cairo.LineCap.ROUND)
            cr.move_to(x, y_start)
            cr.line_to(x, y_end)
            cr.stroke()



import os

def hex_to_rgba_css(hex_color, opacity=1.0):
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"rgba({r}, {g}, {b}, {opacity})"
    return hex_color

def get_caelestia_colors():
    colors = {}
    try:
        path = os.path.expanduser("~/.local/state/caelestia/theme/sddm-theme.conf")
        if os.path.exists(path):
            with open(path, 'r') as f:
                for line in f:
                    if line.startswith("surface="):
                        colors["bg"] = line.strip().split('=')[1]
                    elif line.startswith("text="):
                        colors["fg"] = line.strip().split('=')[1]
                    elif line.startswith("primary="):
                        colors["primary"] = line.strip().split('=')[1]
                    elif line.startswith("mainCardColorOpacity="):
                        colors["opacity"] = float(line.strip().split('=')[1])
    except: pass
    return colors

class DictationOverlay(Gtk.Window):
    def __init__(self, app, config, audio_recorder):
        super().__init__(application=app)
        self.config = config
        
        # Initialize Layer Shell
        Gtk4LayerShell.init_for_window(self)
        Gtk4LayerShell.set_layer(self, Gtk4LayerShell.Layer.OVERLAY)
        Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.NONE)
        
        # Anchor to bottom center
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.BOTTOM, True)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.LEFT, False)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.RIGHT, False)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.TOP, False)
        
        # Margins (0 so it doesn't detach)
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.BOTTOM, 0)
        
        # Namespace for Wayland compositor animations (like Hyprland)
        Gtk4LayerShell.set_namespace(self, "protocol7")
        
        self.set_default_size(120, 40)
        
        # Load CSS
        self.load_css()
        self.remove_css_class("background")
        self.add_css_class("transparent-window")

        outer_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        outer_hbox.set_valign(Gtk.Align.END)
        self.set_child(outer_hbox)

        left_concave = Gtk.Box()
        left_concave.set_size_request(15, 15)
        left_concave.add_css_class("concave-left")
        left_concave.set_valign(Gtk.Align.END)
        outer_hbox.append(left_concave)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.add_css_class("overlay-window")
        outer_hbox.append(main_box)
        
        right_concave = Gtk.Box()
        right_concave.set_size_request(15, 15)
        right_concave.add_css_class("concave-right")
        right_concave.set_valign(Gtk.Align.END)
        outer_hbox.append(right_concave)

        # Layout
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox.set_margin_top(5)
        vbox.set_margin_bottom(5)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        
        main_box.append(vbox)

        # Visualizer
        self.visualizer = Visualizer(config, audio_recorder)
        vbox.append(self.visualizer)

    def load_css(self):
        bg_rgba = "rgba(255, 255, 255, 1.0)"
        if self.config.get("use_caelestia_colors", False):
            caelestia = get_caelestia_colors()
            raw_bg = caelestia.get("bg", "#ffffff")
            bg_rgba = hex_to_rgba_css(raw_bg, 1.0)
            
        css = f"""
        window, window.background, window.transparent-window, decoration {{
            background-color: transparent;
            background: none;
            box-shadow: none;
            border: none;
        }}
        .overlay-window {{
            background-color: {bg_rgba};
            border-radius: 12px 12px 0 0;
            border: none;
            box-shadow: none;
        }}
        .concave-left {{
            background-image: radial-gradient(circle at 0% 0%, transparent 15px, {bg_rgba} 15px);
        }}
        .concave-right {{
            background-image: radial-gradient(circle at 100% 0%, transparent 15px, {bg_rgba} 15px);
        }}
        """
            
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

class UIManager:
    def __init__(self, config, audio_recorder):
        self.config = config
        self.audio_recorder = audio_recorder
        self.app = Gtk.Application(application_id="com.whisper.flow")
        
        settings = Gtk.Settings.get_default()
        if settings:
            settings.set_property("gtk-application-prefer-dark-theme", False)
        self.app.connect("activate", self.on_activate)
        self.overlay = None

    def on_activate(self, app):
        self.app.hold() # Keep the application running even if windows are hidden
        if not self.overlay:
            self.overlay = DictationOverlay(app, self.config, self.audio_recorder)

    def show(self):
        if self.overlay:
            if hasattr(self.overlay, 'visualizer'):
                self.overlay.visualizer.is_processing = False
            self.overlay.set_visible(True)

    def hide(self):
        if self.overlay:
            if hasattr(self.overlay, 'visualizer'):
                self.overlay.visualizer.is_processing = False
            self.overlay.set_visible(False)

    def set_processing_state(self):
        if self.overlay and hasattr(self.overlay, 'visualizer'):
            self.overlay.visualizer.is_processing = True
            
    def run(self):
        self.app.run(None)
