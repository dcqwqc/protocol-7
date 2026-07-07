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
        self.set_size_request(300, 60)
        self.config = config
        self.audio_recorder = audio_recorder
        self.set_draw_func(self.on_draw)
        self.bars = [0.0] * 15
        
        # Start a timeout to redraw the visualizer
        GLib.timeout_add(50, self.update_bars)

    def update_bars(self):
        volume = self.audio_recorder.get_volume_level()
        
        # Shift bars and add new volume, adding some noise for effect
        self.bars.pop(0)
        noise = random.uniform(0.0, 0.2) if volume > 0 else 0
        new_val = min(1.0, volume + noise)
        self.bars.append(new_val)
        
        self.queue_draw()
        return True

    def on_draw(self, area, cr, width, height):
        # Draw background (transparent)
        cr.set_operator(cairo.Operator.CLEAR)
        cr.paint()
        cr.set_operator(cairo.Operator.OVER)

        accent_color = self.config.get("accent_color", "#00ffcc")
        r, g, b, a = hex_to_rgba(accent_color)

        bar_width = width / len(self.bars)
        spacing = 4

        for i, val in enumerate(self.bars):
            bar_h = val * height * 0.8
            # Minimum height for visual effect even when quiet
            if bar_h < 2:
                bar_h = 2
            
            x = i * bar_width + spacing/2
            y = height / 2 - bar_h / 2

            cr.set_source_rgba(r, g, b, 0.8)
            cr.rectangle(x, y, bar_width - spacing, bar_h)
            cr.fill()

class DictationOverlay(Gtk.Window):
    def __init__(self, app, config, audio_recorder):
        super().__init__(application=app)
        self.config = config
        
        # Initialize Layer Shell
        Gtk4LayerShell.init_for_window(self)
        Gtk4LayerShell.set_layer(self, Gtk4LayerShell.Layer.OVERLAY)
        
        # Anchor to bottom center
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.BOTTOM, True)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.LEFT, False)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.RIGHT, False)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.TOP, False)
        
        # Margins
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.BOTTOM, 40)
        
        self.set_default_size(320, 80)
        
        # Load CSS
        self.load_css()
        self.add_css_class("overlay-window")

        # Layout
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        vbox.set_margin_start(15)
        vbox.set_margin_end(15)
        
        self.set_child(vbox)

        # Label
        self.label = Gtk.Label(label="Listening...")
        self.label.add_css_class("listening-label")
        vbox.append(self.label)

        # Visualizer
        self.visualizer = Visualizer(config, audio_recorder)
        vbox.append(self.visualizer)

    def load_css(self):
        css_provider = Gtk.CssProvider()
        css = """
        .overlay-window {
            background-color: rgba(30, 30, 30, 0.9);
            border-radius: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
            border: 1px solid rgba(255,255,255,0.1);
        }
        .listening-label {
            color: #ffffff;
            font-size: 16px;
            font-weight: bold;
        }
        """
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
        self.app.connect("activate", self.on_activate)
        self.overlay = None

    def on_activate(self, app):
        if not self.overlay:
            self.overlay = DictationOverlay(app, self.config, self.audio_recorder)
        self.overlay.present()

    def show(self):
        if self.overlay:
            self.overlay.present()
            # If visualizer has stopped, restart its logic here if needed
            self.overlay.label.set_text("Listening...")

    def hide(self):
        if self.overlay:
            self.overlay.close()
            self.overlay = None

    def set_processing_state(self):
        if self.overlay:
            self.overlay.label.set_text("Processing...")
            
    def run(self):
        self.app.run(None)
