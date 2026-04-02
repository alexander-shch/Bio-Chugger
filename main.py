import tkinter as tk
from tkinter import ttk, messagebox
from threading import Thread
import os, sys, time, asyncio, json, platform
from pythonosc import udp_client
from bleak import BleakScanner
from garmin_core import GarminCore

CONFIG_FILE = "config.json"

# --- THEMES ---
THEMES = {
    "dark": {
        "bg": "#0A0A0A",
        "fg": "#FFFFFF",
        "accent": "#00FF41", # Matrix Green
        "secondary": "#FF9900", # Amber
        "dim": "#888888",
        "btn_bg": "#151515",
        "tree_bg": "#111",
        "tree_head": "#222"
    },
    "light": {
        "bg": "#F0F0F0",
        "fg": "#111111",
        "accent": "#0055BB", # Deep Blue
        "secondary": "#CC3300", # Red-ish
        "dim": "#555555",
        "btn_bg": "#E0E0E0",
        "tree_bg": "#FFFFFF",
        "tree_head": "#D0D0D0"
    }
}

class BioChuggerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("BIO-CHUGGER PRO")
        self.root.geometry("600x800")

        # LOGIC STATE
        self.current_bpm = 120
        self.time_signature = 4
        self.is_muted = False
        self.broadcasting = False
        self.points = [100] * 60
        self.config = self.load_config()
        self.watch_id = self.config.get("watch_id", "")
        self.current_theme_name = self.config.get("theme", "dark")
        self.colors = THEMES[self.current_theme_name]
        
        self.osc_client = udp_client.SimpleUDPClient("127.0.0.1", 8000)
        self.core = None

        # --- STYLING ---
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # UI: BPM DISPLAY
        self.bpm_frame = tk.Frame(root)
        self.bpm_frame.pack(pady=30)
        
        self.bpm_text = tk.Label(self.bpm_frame, text="---", font=("Helvetica", 100, "bold"))
        self.bpm_text.pack()
        
        self.bpm_label = tk.Label(self.bpm_frame, text="BPM", font=("Courier", 14, "bold"))
        self.bpm_label.pack()

        # CONTROL PANEL
        self.ctrl_frame = tk.Frame(root)
        self.ctrl_frame.pack(pady=10)

        self.mute_btn = tk.Button(self.ctrl_frame, text="MUTE CLICK", command=self.toggle_mute, width=12)
        self.mute_btn.pack(side="left", padx=10)

        self.server_btn = tk.Button(self.ctrl_frame, text="START BROADCAST", command=self.toggle_server, width=15)
        self.server_btn.pack(side="left", padx=10)

        self.theme_btn = tk.Button(self.ctrl_frame, text="THEME", command=self.toggle_theme, width=12)
        self.theme_btn.pack(side="left", padx=10)

        # DEVICE SECTION
        self.device_frame = tk.Frame(root, padx=20)
        self.device_frame.pack(fill="x", pady=20)
        
        self.device_label = tk.Label(self.device_frame, text="DEVICE LINK", font=("Courier", 12, "bold"))
        self.device_label.pack(anchor="w")

        self.scan_btn = tk.Button(self.device_frame, text="SCAN FOR DEVICES", command=self.start_scan, width=20)
        self.scan_btn.pack(pady=10)

        self.device_list = ttk.Treeview(self.device_frame, columns=("ID", "Name"), show="headings", height=5)
        self.device_list.heading("ID", text="ADDRESS / ID")
        self.device_list.heading("Name", text="SIGNAL NAME")
        self.device_list.column("ID", width=250)
        self.device_list.column("Name", width=250)
        self.device_list.pack(fill="x", pady=5)
        self.device_list.bind("<Double-1>", self.on_device_select)

        # OSCILLOSCOPE / WAVEFORM
        self.canvas_frame = tk.Frame(root, highlightthickness=1)
        self.canvas_frame.pack(pady=10, padx=20, fill="x")
        self.canvas = tk.Canvas(self.canvas_frame, height=100, highlightthickness=0)
        self.canvas.pack(fill="x", padx=2, pady=2)

        # STATUS BAR
        self.status_text = tk.Label(root, text="INITIALIZING...", font=("Courier", 10))
        self.status_text.pack(side="bottom", fill="x", pady=10)

        # APPLY THEME
        self.apply_theme()

        # 1. AUTO-START WATCH CONNECTION
        if self.watch_id:
            self.init_watch_connection()
        else:
            self.update_status("NO DEVICE LINKED", self.colors["secondary"])
        
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
                             rowheight=30,
                             borderwidth=0,
                             font=("Courier", 11))
        self.style.map("Treeview", 
                       background=[('selected', c["accent"])],
                       foreground=[('selected', "#000" if self.current_theme_name == "dark" else "#FFF")])
        
        self.style.configure("Treeview.Heading", 
                             background=c["tree_head"], 
                             foreground=c["accent"], 
                             borderwidth=0,
                             font=("Courier", 12, "bold"))

        # Widgets
        self.bpm_frame.config(bg=c["bg"])
        self.bpm_text.config(bg=c["bg"], fg=c["accent"] if self.current_bpm > 0 else c["dim"])
        self.bpm_label.config(bg=c["bg"], fg=c["accent"])
        
        self.ctrl_frame.config(bg=c["bg"])
        btn_style = {
            "bg": c["btn_bg"],
            "fg": c["fg"],
            "font": ("Courier", 10, "bold"),
            "relief": "flat",
            "borderwidth": 1,
            "highlightbackground": c["dim"],
            "activebackground": c["accent"],
            "activeforeground": "#000",
            "padx": 10,
            "pady": 5
        }
        
        for btn in [self.mute_btn, self.server_btn, self.theme_btn, self.scan_btn]:
            btn.config(**btn_style)

        if self.broadcasting:
            self.server_btn.config(bg=c["accent"], fg="#000")

        self.device_frame.config(bg=c["bg"])
        self.device_label.config(bg=c["bg"], fg=c["dim"])
        
        self.canvas_frame.config(bg=c["tree_bg"], highlightbackground=c["dim"])
        self.canvas.config(bg="#000" if self.current_theme_name == "dark" else "#FFF")
        
        self.status_text.config(bg=c["bg"], fg=c["dim"])
        self.theme_btn.config(text=f"THEME: {self.current_theme_name.upper()}")

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
        self.scan_btn.config(state="disabled", text="SCANNING...", fg=self.colors["secondary"])
        self.device_list.delete(*self.device_list.get_children())
        
        async def scan():
            devices = await BleakScanner.discover(timeout=5.0)
            for d in devices:
                name = d.name if d.name else "Unknown Signal"
                self.device_list.insert("", "end", values=(d.address, name))
            self.scan_btn.config(state="normal", text="SCAN FOR DEVICES", fg=self.colors["fg"])

        def run_scan():
            asyncio.run(scan())
        
        Thread(target=run_scan, daemon=True).start()

    def on_device_select(self, event):
        item = self.device_list.selection()[0]
        self.watch_id = self.device_list.item(item, "values")[0]
        self.save_config()
        self.update_status(f"LINKED TO {self.watch_id}", self.colors["accent"])
        self.init_watch_connection()

    def toggle_server(self):
        self.broadcasting = not self.broadcasting
        if self.broadcasting:
            self.server_btn.config(text="STOP BROADCAST", bg=self.colors["accent"], fg="#000")
            self.update_status("● BROADCASTING TO REAPER", self.colors["accent"])
        else:
            self.server_btn.config(text="START BROADCAST", bg=self.colors["btn_bg"], fg=self.colors["fg"])
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
        # Translate named colors if necessary, or just use accent if it's a success
        if color == "#00ff00": color = self.colors["accent"]
        if color == "red": color = self.colors["secondary"]
        self.update_status(message, color)

    def update_status(self, message, color):
        self.status_text.config(text=message, fg=color)

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
            
            self.points[-2], self.points[-1] = (10, 90) if beat == 1 else (40, 60)
            beat = (beat % self.time_signature) + 1
            time.sleep(delay)

    def animate_wave(self):
        self.canvas.delete("wave")
        self.points.append(50) # Middle line
        if len(self.points) > 60: self.points.pop(0)
        
        w = self.canvas.winfo_width()
        step = w / 60 if w > 60 else 10

        for i in range(len(self.points)-1):
            self.canvas.create_line(i*step, self.points[i], (i+1)*step, self.points[i+1], fill=self.colors["accent"], width=2, tags="wave")
        self.root.after(40, self.animate_wave)

if __name__ == "__main__":
    root = tk.Tk()
    try:
        root.attributes('-topmost', True)
    except: pass
    app = BioChuggerApp(root)
    root.mainloop()
