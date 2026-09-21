import ctypes
try:
    ctypes.CDLL("libgtk4-layer-shell.so", mode=ctypes.RTLD_GLOBAL)
except Exception:
    pass

import gi
import json
import math
import os
import random
gi.require_version('Gtk', '4.0')
gi.require_version('Gtk4LayerShell', '1.0')
from gi.repository import Gtk, Gtk4LayerShell, GLib, Gdk, cairo

from overlay_shape import SLIDE_MS, draw_shadow, ease_spatial, panel_path

# Panel geometry, in logical pixels. The window around it is fixed and never
# resized: a layer-shell surface that changes size mid-animation costs a
# configure, an ack and a commit every frame, and the result reads as the panel
# inflating rather than sliding.
PANEL_W = 112
PANEL_H = 30
CORNER_R = 10
FILLET_R = 12
# Wide enough for the panel, both fillets, and the shift that lines it up with
# the shell's own centre -- the window itself never changes size.
WINDOW_W = PANEL_W + FILLET_R * 2 + 140
WINDOW_H = PANEL_H + 40


def hex_to_rgba(hex_code, alpha=1.0):
    hex_code = hex_code.lstrip('#')
    if len(hex_code) == 6:
        r = int(hex_code[0:2], 16) / 255.0
        g = int(hex_code[2:4], 16) / 255.0
        b = int(hex_code[4:6], 16) / 255.0
        return r, g, b, alpha
    return 0.0, 1.0, 0.8, alpha  # Default tealish


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
    except Exception:
        pass
    return colors


def get_caelestia_offset():
    """How far right of screen centre the shell centres its own surfaces.

    The bar occupies the left edge, so Caelestia's drawers are centred in what
    is left over rather than on the screen. A panel centred on the screen sits
    half a bar-width left of everything it is supposed to line up with, which is
    small enough to look like a mistake rather than a choice.
    """
    inner, padding = 40, 8  # Caelestia's bar.innerWidth and padding.small
    bar = inner + max(padding, get_caelestia_border()) * 2
    return bar * 0.5


def get_caelestia_border():
    """The shell's border thickness -- the strip the panel rises out of.

    Read from the shell's own config so the join lands on the real border
    rather than a guess. Ten is Caelestia's default when unset.
    """
    try:
        path = os.path.expanduser("~/.config/caelestia/shell.json")
        if os.path.exists(path):
            with open(path, 'r') as f:
                value = json.load(f).get("border", {}).get("thickness")
                if isinstance(value, (int, float)):
                    return max(0, int(value))
    except Exception:
        pass
    return 10


class OverlaySurface(Gtk.DrawingArea):
    """The whole overlay: the panel, its joins with the shell border, and the bars.

    Everything is drawn here rather than assembled from styled widgets. The old
    version tried to do it with CSS -- two boxes carrying a radial-gradient to
    fake the concave corners, and a `transition` on `transform` to slide. GTK4
    does not animate widget transforms from CSS, so the slide never ran at all,
    and the gradients only approximated the join at one exact size. Drawing it
    means the shape is correct at every point of the animation, including
    halfway.
    """

    def __init__(self, config, audio_recorder):
        super().__init__()
        self.config = config
        self.audio_recorder = audio_recorder
        self.set_content_width(WINDOW_W)
        self.set_content_height(WINDOW_H)
        self.set_draw_func(self.on_draw)

        self.bars = [0.0] * 9
        self.is_processing = False
        self.wave_offset = 0.0

        # Slide state. `progress` is the raw 0..1 the clock drives; the eased
        # value is derived, so retargeting mid-slide picks up from where the
        # panel actually is instead of snapping.
        self.progress = 0.0
        self.target = 0.0
        self._anim_from = 0.0
        self._anim_start = None
        self._tick = None

        GLib.timeout_add(16, self.update_bars)

    # ---- motion ---------------------------------------------------------

    def animate_to(self, target):
        # Deliberately no early return when the target is unchanged. The panel
        # has to end up where it was told to go even if a previous animation
        # was interrupted, retargeted, or never started -- skipping the call is
        # how it ends up frozen half out with nothing left to move it.
        self.target = target
        self._anim_from = self.progress
        self._anim_start = None
        if self._tick is None:
            self._tick = self.add_tick_callback(self._on_frame)

    def _on_frame(self, widget, clock):
        now = clock.get_frame_time() / 1000.0  # microseconds -> ms
        if self._anim_start is None:
            self._anim_start = now

        span = abs(self.target - self._anim_from)
        duration = max(1.0, SLIDE_MS * max(span, 0.25))
        t = min(1.0, (now - self._anim_start) / duration)

        eased = ease_spatial(t)
        self.progress = self._anim_from + (self.target - self._anim_from) * eased
        self.queue_draw()

        if t >= 1.0:
            self.progress = self.target
            self._tick = None
            self.queue_draw()
            return False
        return True

    # ---- bars -----------------------------------------------------------

    def update_bars(self):
        try:
            return self._update_bars()
        except Exception:
            # Never let this source die. PyGObject drops a timeout whose
            # callback raises, and the only symptom is that the bars stop
            # moving and the processing wave never runs again -- for the rest
            # of the session, with nothing on screen to say why.
            return True

    def _update_bars(self):
        if self.progress <= 0.001 and not self._tick:
            return True  # nothing visible; skip the work but keep the timer

        if self.is_processing:
            # Tuned by measuring the travel rather than by eye, because the
            # speed was never the limiting factor. Damping the follow factor to
            # 0.12 left the centre bar moving under five pixels out of
            # eighteen, and no wave speed rescues that -- the bars simply
            # cannot keep up with the target, so the whole row sits nearly
            # still. Follow closely enough to track, over a band that never
            # collapses to nothing or reaches the ceiling: about ten pixels of
            # travel between four and fourteen.
            self.wave_offset += 0.13
            for i in range(len(self.bars)):
                phase = math.sin(self.wave_offset + i * 0.45)
                target = 0.20 + 0.60 * (phase + 1.0) * 0.5
                self.bars[i] += (target - self.bars[i]) * 0.28
            self.queue_draw()
            return True

        volume = self.audio_recorder.get_volume_level()
        if volume < 0.02:
            volume = 0.0
        else:
            # The recorder reports rms * 10, so ordinary speech arrives around
            # 0.1 to 0.4. Dropping the gain entirely was an overcorrection: at
            # the gentler curve alone, talking normally moved each bar one or
            # two pixels out of eighteen, which is alive but indistinguishable
            # from dead. This keeps enough gain to read clearly while still
            # leaving headroom for actually raising your voice.
            volume = min(1.0, (volume ** 0.55) * 1.5)

        for i in range(len(self.bars)):
            dist = abs(i - (len(self.bars) - 1) / 2.0)
            weight = max(0.35, 1.0 - (dist / (len(self.bars) / 2.0)))
            target = volume * weight
            if volume > 0:
                target *= random.uniform(0.94, 1.06)
            # Rises briskly, falls slowly: the jitter reads as speech rather
            # than as flicker.
            k = 0.45 if target > self.bars[i] else 0.16
            self.bars[i] += (target - self.bars[i]) * k

        self.queue_draw()
        return True

    # ---- drawing --------------------------------------------------------

    def on_draw(self, area, cr, width, height):
        cr.set_operator(cairo.Operator.CLEAR)
        cr.paint()
        cr.set_operator(cairo.Operator.OVER)

        if self.progress <= 0.001:
            return

        use_caelestia = self.config.get("use_caelestia_colors", False)
        caelestia = get_caelestia_colors() if use_caelestia else {}

        surface_hex = caelestia.get("bg", "#ffffff")
        accent_hex = caelestia.get("primary", self.config.get("accent_color", "#00ffcc"))
        # Only merge with a border that is actually there. Off Caelestia the
        # panel is a free-standing pill instead, which is the honest shape.
        border = get_caelestia_border() if use_caelestia else 0
        dx = get_caelestia_offset() if use_caelestia else 0.0

        eased = max(0.0, min(1.0, self.progress))
        if not panel_path(cr, width, height, eased, PANEL_W, PANEL_H,
                          CORNER_R, FILLET_R, border, dx):
            return

        # Shadow first, under the panel, so it sits between the overlay and
        # whatever is behind it rather than on top of either.
        draw_shadow(cr, (0.0, 0.0, 0.0))

        sr, sg, sb, _ = hex_to_rgba(surface_hex)
        cr.set_source_rgba(sr, sg, sb, 1.0)
        cr.fill_preserve()
        # Contents are clipped to the panel so they emerge from behind the
        # border with it rather than floating in ahead of it.
        cr.clip()

        # Slide the bars with the panel instead of stretching them: they keep
        # their proportions the whole way up.
        # The panel sits on the screen edge, so its centre is measured from
        # there. This was still measuring from a border inset that the shape
        # stopped using, which drew every bar the border's thickness too high.
        baseline = height
        cr.translate(0.0, (1.0 - eased) * PANEL_H)
        self.draw_bars(cr, width, baseline, accent_hex, dx)

    def draw_bars(self, cr, width, baseline, accent_hex, dx=0.0):
        r, g, b, _ = hex_to_rgba(accent_hex)
        inner_w = PANEL_W - 24
        x_left = (width - inner_w) * 0.5 + dx
        mid_y = baseline - PANEL_H * 0.5
        bar_slot = inner_w / len(self.bars)
        thickness = 4.0
        max_h = PANEL_H - 12

        cr.set_source_rgba(r, g, b, 0.85)
        cr.set_line_width(thickness)
        cr.set_line_cap(cairo.LineCap.ROUND)
        for i, val in enumerate(self.bars):
            bar_h = min(max_h, max(thickness, val * max_h))
            x = x_left + i * bar_slot + bar_slot * 0.5
            cr.move_to(x, mid_y - bar_h * 0.5)
            cr.line_to(x, mid_y + bar_h * 0.5)
            cr.stroke()


class DictationOverlay(Gtk.Window):
    def __init__(self, app, config, audio_recorder):
        super().__init__(application=app)
        self.config = config

        Gtk4LayerShell.init_for_window(self)
        Gtk4LayerShell.set_layer(self, Gtk4LayerShell.Layer.OVERLAY)
        Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.NONE)

        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.BOTTOM, True)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.LEFT, False)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.RIGHT, False)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.TOP, False)
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.BOTTOM, 0)
        Gtk4LayerShell.set_namespace(self, "protocol7")

        # Fixed for the life of the window. The slide happens inside it.
        self.set_default_size(WINDOW_W, WINDOW_H)

        self.load_css()
        self.remove_css_class("background")
        self.add_css_class("transparent-window")

        self.visualizer = OverlaySurface(config, audio_recorder)
        self.set_child(self.visualizer)

        self.connect("realize", self._on_realize)

    def _on_realize(self, _widget):
        # Nothing here is interactive, so it should never take a click from
        # whatever is underneath it. An overlay pinned across the bottom of the
        # screen that swallows pointer events is worse than no overlay.
        try:
            surface = self.get_surface()
            if surface is not None:
                surface.set_input_region(cairo.Region())
        except Exception:
            pass

    def load_css(self):
        css = """
        window, window.background, window.transparent-window, decoration {
            background-color: transparent;
            background: none;
            box-shadow: none;
            border: none;
        }
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
        self.app.hold()
        if not self.overlay:
            self.overlay = DictationOverlay(app, self.config, self.audio_recorder)
            self.overlay.set_visible(True)

    def show(self):
        if self.overlay:
            self.overlay.visualizer.is_processing = False
            self.overlay.visualizer.animate_to(1.0)

    def hide(self):
        if self.overlay:
            self.overlay.visualizer.is_processing = False
            self.overlay.visualizer.animate_to(0.0)

    def set_processing_state(self):
        if self.overlay:
            self.overlay.visualizer.is_processing = True

    def run(self):
        self.app.run(None)
