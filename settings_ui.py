import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk

import sounddevice as sd
from config import save_config

class SettingsWindow(Gtk.ApplicationWindow):
    def __init__(self, app, config):
        super().__init__(application=app, title="Whisper Flow Settings")
        self.config = config
        self.set_default_size(500, 600)
        
        # Apply dark theme
        settings = Gtk.Settings.get_default()
        settings.set_property("gtk-application-prefer-dark-theme", True)

        scrolled = Gtk.ScrolledWindow()
        self.set_child(scrolled)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        vbox.set_margin_top(20)
        vbox.set_margin_bottom(20)
        vbox.set_margin_start(20)
        vbox.set_margin_end(20)
        scrolled.set_child(vbox)

        # -- Model Library & Management --
        self.add_section_title(vbox, "Model Library & Management")
        
        model_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.model_combo = Gtk.DropDown.new_from_strings(["tiny.en", "tiny", "base.en", "base", "small.en", "small", "medium", "large-v3"])
        self.set_dropdown_active(self.model_combo, self.config.get("model_size", "tiny.en"))
        model_box.append(Gtk.Label(label="Active Model:"))
        model_box.append(self.model_combo)
        vbox.append(model_box)
        
        info_label = Gtk.Label(label="(faster-whisper will automatically download models on first use)")
        info_label.add_css_class("dim-label")
        vbox.append(info_label)

        # -- Hotkey Configuration --
        self.add_section_title(vbox, "Hotkey Configuration")
        
        hotkey_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.hotkey_entry = Gtk.Entry()
        self.hotkey_entry.set_text(str(self.config.get("hotkey_keycode", 29)))
        hotkey_box.append(Gtk.Label(label="Trigger Keycode (e.g. 29 for L-Ctrl):"))
        hotkey_box.append(self.hotkey_entry)
        vbox.append(hotkey_box)

        # -- Accent Color --
        self.add_section_title(vbox, "Appearance")
        
        color_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.color_entry = Gtk.Entry()
        self.color_entry.set_text(self.config.get("accent_color", "#00ffcc"))
        color_box.append(Gtk.Label(label="Accent Color (Hex):"))
        color_box.append(self.color_entry)
        vbox.append(color_box)

        # -- Input Device --
        self.add_section_title(vbox, "Input Device")
        
        device_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        devices = []
        try:
            for i, dev in enumerate(sd.query_devices()):
                if dev['max_input_channels'] > 0:
                    devices.append(f"{i}: {dev['name']}")
        except Exception:
            devices = ["Default"]
            
        self.device_combo = Gtk.DropDown.new_from_strings(devices if devices else ["Default"])
        device_box.append(Gtk.Label(label="Microphone:"))
        device_box.append(self.device_combo)
        vbox.append(device_box)

        # -- Language & Translation --
        self.add_section_title(vbox, "Language & Translation")
        
        lang_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.auto_detect_check = Gtk.CheckButton(label="Auto-Detect Language")
        self.auto_detect_check.set_active(self.config.get("auto_detect_language", True))
        lang_box.append(self.auto_detect_check)
        vbox.append(lang_box)

        manual_lang_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.lang_entry = Gtk.Entry()
        self.lang_entry.set_placeholder_text("Language code (e.g., 'en', 'es')")
        self.lang_entry.set_text(self.config.get("language", "en"))
        manual_lang_box.append(Gtk.Label(label="Manual Language:"))
        manual_lang_box.append(self.lang_entry)
        vbox.append(manual_lang_box)

        trans_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.translate_check = Gtk.CheckButton(label="Translate to English")
        self.translate_check.set_active(self.config.get("translate", False))
        trans_box.append(self.translate_check)
        vbox.append(trans_box)

        # Save Button
        save_btn = Gtk.Button(label="Save & Exit")
        save_btn.set_margin_top(20)
        save_btn.connect("clicked", self.on_save_clicked)
        save_btn.add_css_class("suggested-action")
        vbox.append(save_btn)
        
        self.load_css()

    def add_section_title(self, box, title):
        label = Gtk.Label(label=title)
        label.set_halign(Gtk.Align.START)
        label.set_margin_top(15)
        label.set_margin_bottom(5)
        label.add_css_class("title-label")
        box.append(label)

    def set_dropdown_active(self, dropdown, text):
        model = dropdown.get_model()
        for i in range(model.get_n_items()):
            item = model.get_item(i)
            # This is a bit tricky with Gtk.StringList in GTK4
            if item.get_string() == text:
                dropdown.set_selected(i)
                break

    def get_dropdown_text(self, dropdown):
        selected_item = dropdown.get_selected_item()
        if selected_item:
            return selected_item.get_string()
        return ""

    def on_save_clicked(self, btn):
        # Save config
        self.config["model_size"] = self.get_dropdown_text(self.model_combo)
        
        try:
            self.config["hotkey_keycode"] = int(self.hotkey_entry.get_text())
        except ValueError:
            pass
            
        self.config["accent_color"] = self.color_entry.get_text()
        
        device_str = self.get_dropdown_text(self.device_combo)
        if device_str and ":" in device_str:
            try:
                self.config["input_device"] = int(device_str.split(":")[0])
            except ValueError:
                self.config["input_device"] = None
        else:
            self.config["input_device"] = None
            
        self.config["auto_detect_language"] = self.auto_detect_check.get_active()
        self.config["language"] = self.lang_entry.get_text()
        self.config["translate"] = self.translate_check.get_active()
        
        save_config(self.config)
        self.close()

    def load_css(self):
        css_provider = Gtk.CssProvider()
        css = """
        .title-label {
            font-size: 18px;
            font-weight: bold;
            color: #00ffcc;
        }
        .dim-label {
            color: #aaaaaa;
            font-size: 12px;
        }
        """
        css_provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

class SettingsApp(Gtk.Application):
    def __init__(self, config):
        super().__init__(application_id="com.whisper.flow.settings")
        self.config = config

    def do_activate(self):
        win = SettingsWindow(self, self.config)
        win.present()

def run_settings(config):
    app = SettingsApp(config)
    app.run(None)
