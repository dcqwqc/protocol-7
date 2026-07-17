import math
import random
import tkinter as tk
import customtkinter as ctk

class Visualizer(tk.Canvas):
    def __init__(self, master, config, audio_recorder, bg_color):
        super().__init__(master, width=100, height=24, bg=bg_color, highlightthickness=0)
        self.config = config
        self.audio_recorder = audio_recorder
        self.bars = [0.0] * 10
        self.is_processing = False
        self.wave_offset = 0.0
        
        # Color parsing
        self.accent_color = self.config.get("accent_color", "#00ffcc")
        
        self.update_bars()

    def update_bars(self):
        if self.is_processing:
            self.wave_offset += 0.15
            for i in range(len(self.bars)):
                target = (math.sin(self.wave_offset + i * 0.5) + 1.0) * 0.5
                self.bars[i] += (target - self.bars[i]) * 0.3
            self.draw_bars()
            self.after(16, self.update_bars)
            return

        volume = self.audio_recorder.get_volume_level()
        if volume < 0.02:
            volume = 0.0
        else:
            volume = min(1.0, volume ** 0.5)
            
        for i in range(len(self.bars)):
            dist = abs(i - (len(self.bars) - 1) / 2.0)
            weight = max(0.3, 1.0 - (dist / (len(self.bars) / 2.0)))
            
            target = volume * weight * 1.8
            if volume > 0:
                target *= random.uniform(0.85, 1.15)
                
            self.bars[i] += (target - self.bars[i]) * 0.7
            
        self.draw_bars()
        self.after(16, self.update_bars)

    def draw_bars(self):
        self.delete("all")
        width = int(self.cget("width"))
        height = int(self.cget("height"))
        
        bar_width = width / len(self.bars)
        line_thickness = 5
        
        for i, val in enumerate(self.bars):
            bar_h = val * height * 0.7
            max_h = height - line_thickness - 2
            
            if bar_h > max_h:
                bar_h = max_h
            elif bar_h < line_thickness:
                bar_h = line_thickness
                
            x = i * bar_width + bar_width / 2
            y_start = height / 2 - bar_h / 2
            y_end = height / 2 + bar_h / 2
            
            self.create_line(x, y_start, x, y_end, fill=self.accent_color, width=line_thickness, capstyle=tk.ROUND)

class DictationOverlay(tk.Toplevel):
    def __init__(self, master, config, audio_recorder):
        super().__init__(master)
        self.config = config
        
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        
        theme_mode = self.config.get("theme_mode", "system")
        if theme_mode == "light":
            self.bg_color = "#fafafa"
            self.border_color = "#cccccc"
        else:
            self.bg_color = "#1e1e1e"
            self.border_color = "#333333"
            
        # Set transparent color for Windows
        self.configure(bg="black")
        self.attributes("-transparentcolor", "black")
        
        # Frame holding content with beautiful rounded corners
        self.frame = ctk.CTkFrame(self, fg_color=self.bg_color, border_color=self.border_color, border_width=1, corner_radius=15)
        self.frame.pack(expand=True, fill="both", padx=10, pady=10)
        
        self.visualizer = Visualizer(self.frame, config, audio_recorder, self.bg_color)
        self.visualizer.pack(expand=True, padx=10, pady=5)
        
        self.update_idletasks()
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        
        # Position bottom center
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - w) // 2
        y = screen_height - h - 50 # 50px from bottom
        self.geometry(f"{w}x{h}+{x}+{y}")
        
class UIManager:
    def __init__(self, config, audio_recorder):
        self.config = config
        self.audio_recorder = audio_recorder
        
        self.root = tk.Tk()
        self.root.withdraw() # Hide main window
        self.overlay = None

    def invoke_main_thread(self, func, *args):
        self.root.after(0, lambda: func(*args))

    def show(self):
        if not self.overlay:
            self.overlay = DictationOverlay(self.root, self.config, self.audio_recorder)
        else:
            self.overlay.visualizer.is_processing = False
            self.overlay.deiconify()

    def hide(self):
        if self.overlay:
            self.overlay.visualizer.is_processing = False
            self.overlay.withdraw()

    def set_processing_state(self):
        if self.overlay:
            self.overlay.visualizer.is_processing = True
            
    def run(self):
        self.root.mainloop()
