import tkinter as tk
from tkinter import ttk, messagebox
from threading import Thread
import os, sys, time, asyncio, json, platform
from pythonosc import udp_client
from bleak import BleakScanner
from garmin_core import GarminCore

CONFIG_FILE = "config.json"

# --- MATERIAL DESIGN THEMES ---
THEMES = {
    "dark": {
        "bg": "#121212",        # Material Surface
        "surface": "#1E1E1E",  # Material Secondary Surface
        "fg": "#FFFFFF",       # High Emphasis
        "fg_medium": "#B3B3B3",# Medium Emphasis
        "accent": "#03DAC6",   # Material Teal
        "secondary": "#CF6679",# Material Error/Pink
        "btn_bg": "#000000",
        "btn_fg": "#FFFFFF",
        "tree_bg": "#1E1E1E",
        "tree_head": "#2C2C2C"
    },
    "light": {
        "bg": "#FFFFFF",
        "surface": "#F5F5F5",
        "fg": "#000000",
        "fg_medium": "#666666",
        "accent": "#6200EE",   # Material Purple
        "secondary": "#B00020",# Material Red
        "btn_bg": "#E0E0E0",
        "btn_fg": "#000000",
        "tree_bg": "#FFFFFF",
        "tree_head": "#E0E0E0"
    }
}

class BioChuggerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("BIO-CHUGGER PRO")
        self.root.geometry("620x850")

        # LOGIC STATE
        self.current_bpm = 120
        self.time_signature = 4
        self.is_muted = False
        self.broadcasting = False
        self.points = [50] * 60
        self.config = self.load_config()
        self.watch_id = self.config.get("watch_id", "")
        self.current_theme_name = self.config.get("theme", "light")
        self.colors = THEMES[self.current_theme_name]
        
        self.osc_client = udp_client.SimpleUDPClient("127.0.0.1", 8000)
        self.core = None

        # --- STYLING ---
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # UI: CARD-LIKE BPM DISPLAY
        self.card_frame = tk.Frame(root, pady=40, padx=20)
        self.card_frame.pack(fill="x", padx=20, pady=20)
        
        self.bpm_text = tk.Label(self.card_frame, text="---", font=("Inter", 120, "bold"))
        self.bpm_text.pack()
        
        self.bpm_label = tk.Label(self.card_frame, text="BEATS PER MINUTE", font=("Inter", 12, "bold"))
        self.bpm_label.pack()

        # CONTROL PANEL
        self.ctrl_frame = tk.Frame(root)
        self.ctrl_frame.pack(pady=10)

        # Helper for common button style
        self.btn_font = ("Inter", 10, "bold")

        self.mute_btn = tk.Button(self.ctrl_frame, text="MUTE CLICK", command=self.toggle_mute, width=14)
        self.mute_btn.pack(side="left", padx=8)

        self.server_btn = tk.Button(self.ctrl_frame, text="START BROADCAST", command=self.toggle_server, width=18)
        self.server_btn.pack(side="left", padx=8)

        self.theme_btn = tk.Button(self.ctrl_frame, text="DARK MODE", command=self.toggle_theme, width=14)
        self.theme_btn.pack(side="left", padx=8)

        # DEVICE SECTION
        self.device_frame = tk.Frame(root, padx=30)
        self.device_frame.pack(fill="x", pady=20)
        
        self.device_header = tk.Frame(self.device_frame)
        self.device_header.pack(fill="x")
        
        self.device_label = tk.Label(self.device_header, text="DEVICE LINK", font=("Inter", 11, "bold"))
        self.device_label.pack(side="left")

        self.scan_btn = tk.Button(self.device_frame, text="SCAN FOR DEVICES", command=self.start_scan)
        self.scan_btn.pack(fill="x", pady=10)

        self.device_list = ttk.Treeview(self.device_frame, columns=("ID", "Name"), show="headings", height=5)
        self.device_list.heading("ID", text="DEVICE ID")
        self.device_list.heading("Name", text="SIGNAL NAME")
        self.device_list.column("ID", width=250)
        self.device_list.column("Name", width=250)
        self.device_list.pack(fill="x", pady=5)
        self.device_list.bind("<Double-1>", self.on_device_select)

        # WAVEFORM (CARD STYLE)
        self.canvas_card = tk.Frame(root, highlightthickness=0)
        self.canvas_card.pack(pady=10, padx=30, fill="x")
        self.canvas = tk.Canvas(self.canvas_card, height=120, highlightthickness=0)
        self.canvas.pack(fill="x")

        # STATUS BAR
        self.status_text = tk.Label(root, text="READY", font=("Inter", 9))
        self.status_text.pack(side="bottom", fill="x", pady=15)

        # APPLY THEME
        self.apply_theme()

        # 1. AUTO-START WATCH CONNECTION
        if self.watch_id:
            self.init_watch_connection()
        else:
            self.update_status("PLEASE LINK A DEVICE", self.colors["secondary"])
        
        # 2. START ENGINE
        Thread(target=self.metronome_engine, daemon=True).start()
        self.animate_wave()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except: pass
        return {}

    def save_config(self):
        config_to_save = {
            "watch_id": self.watch_id,
            "theme": self.current_theme_name
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(config_to_save, f)

    def apply_theme(self):
        c = self.colors
        self.root.configure(bg=c["bg"])
        
        # Style Configure
        self.style.configure("Treeview", 
                             background=c["tree_bg"], 
                             foreground=c["fg"], 
                             fieldbackground=c["tree_bg"], 
                             rowheight=35,
                             borderwidth=0,
                             font=("Inter", 10))
        self.style.map("Treeview", 
                       background=[('selected', c["accent"])],
                       foreground=[('selected', "#000000")])
        
        self.style.configure("Treeview.Heading", 
                             background=c["tree_head"], 
                             foreground=c["fg_medium"], 
                             borderwidth=0,
                             font=("Inter", 10, "bold"))

        # Main Components
        self.card_frame.config(bg=c["surface"])
        self.bpm_text.config(bg=c["surface"], fg=c["accent"] if self.current_bpm > 0 else c["fg_medium"])
        self.bpm_label.config(bg=c["surface"], fg=c["fg_medium"])
        
        self.ctrl_frame.config(bg=c["bg"])
        
        # High contrast button base
        btn_base = {
            "bg": c["btn_bg"],
            "fg": c["btn_fg"],
            "font": self.btn_font,
            "relief": "flat",
            "activebackground": c["accent"],
            "activeforeground": "#000000",
            "highlightthickness": 0,
            "bd": 0,
            "pady": 8
        }
        
        for btn in [self.mute_btn, self.server_btn, self.theme_btn, self.scan_btn]:
            btn.config(**btn_base)

        # Specific states
        if self.broadcasting:
            self.server_btn.config(bg=c["accent"], fg="#000000")
        
        self.device_frame.config(bg=c["bg"])
        self.device_header.config(bg=c["bg"])
        self.device_label.config(bg=c["bg"], fg=c["fg"])
        
        self.canvas_card.config(bg=c["surface"])
        self.canvas.config(bg=c["surface"])
        
        self.status_text.config(bg=c["bg"], fg=c["fg_medium"])
        self.theme_btn.config(text="LIGHT THEME" if self.current_theme_name == "dark" else "DARK THEME")

    def toggle_theme(self):
        self.current_theme_name = "light" if self.current_theme_name == "dark" else "dark"
        self.colors = THEMES[self.current_theme_name]
        self.apply_theme()
        self.save_config()

    def init_watch_connection(self):
        if self.core:
            self.core.stop()
        
        def run_core():
            self.core = GarminCore(
                watch_id=self.watch_id,
                callback=lambda bpm: self.root.after(0, self.update_bpm, bpm),
                status_callback=lambda msg, color: self.root.after(0, self.update_status_wrapper, msg, color)
            )
            asyncio.run(self.core.start())
        Thread(target=run_core, daemon=True).start()

    def start_scan(self):
        self.scan_btn.config(state="disabled", text="SCANNING...", bg=self.colors["tree_head"])
        self.device_list.delete(*self.device_list.get_children())
        
        async def scan():
            devices = await BleakScanner.discover(timeout=5.0)
            for d in devices:
                name = d.name if d.name else "Unknown Device"
                self.device_list.insert("", "end", values=(d.address, name))
            self.scan_btn.config(state="normal", text="SCAN FOR DEVICES", bg=self.colors["btn_bg"])

        def run_scan():
            asyncio.run(scan())
        
        Thread(target=run_scan, daemon=True).start()

    def on_device_select(self, event):
        item = self.device_list.selection()[0]
        self.watch_id = self.device_list.item(item, "values")[0]
        self.save_config()
        self.update_status(f"LINKED: {self.watch_id}", self.colors["accent"])
        self.init_watch_connection()

    def toggle_server(self):
        self.broadcasting = not self.broadcasting
        if self.broadcasting:
            self.server_btn.config(text="STOP BROADCAST", bg=self.colors["accent"], fg="#000000")
            self.update_status("● BROADCASTING TO REAPER", self.colors["accent"])
        else:
            self.server_btn.config(text="START BROADCAST", bg=self.colors["btn_bg"], fg=self.colors["btn_fg"])
            self.update_status("● STANDBY (LINKED)", self.colors["accent"])

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        self.mute_btn.config(text="UNMUTE" if self.is_muted else "MUTE CLICK")

    def update_bpm(self, bpm):
        self.current_bpm = bpm
        self.bpm_text.config(text=str(bpm), fg=self.colors["accent"])
        if self.broadcasting:
            self.osc_client.send_message("/tempo", float(bpm))

    def update_status_wrapper(self, message, color):
        if color == "#00ff00": color = self.colors["accent"]
        if color == "red": color = self.colors["secondary"]
        self.update_status(message, color)

    def update_status(self, message, color):
        self.status_text.config(text=message.upper(), fg=color)

    def metronome_engine(self):
        beat = 1
        while True:
            bpm = self.current_bpm if self.current_bpm > 0 else 120
            delay = 60.0 / bpm
            if not self.is_muted:
                if platform.system() == "Darwin":
                    sound = "Glass.aiff" if beat == 1 else "Tink.aiff"
                    os.system(f"afplay /System/Library/Sounds/{sound} &")
                elif platform.system() == "Windows":
                    import winsound
                    freq = 800 if beat == 1 else 400
                    winsound.Beep(freq, 100)
                else:
                    print("\a", end="", flush=True)
            
            self.points[-2], self.points[-1] = (20, 100) if beat == 1 else (50, 70)
            beat = (beat % self.time_signature) + 1
            time.sleep(delay)

    def animate_wave(self):
        self.canvas.delete("wave")
        self.points.append(60) 
        if len(self.points) > 60: self.points.pop(0)
        
        w = self.canvas.winfo_width()
        step = w / 60 if w > 60 else 10

        for i in range(len(self.points)-1):
            self.canvas.create_line(i*step, self.points[i], (i+1)*step, self.points[i+1], 
                                   fill=self.colors["accent"], width=3, tags="wave", capstyle="round")
        self.root.after(40, self.animate_wave)

if __name__ == "__main__":
    root = tk.Tk()
    try:
        root.attributes('-topmost', True)
    except: pass
    app = BioChuggerApp(root)
    root.mainloop()
