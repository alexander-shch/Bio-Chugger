import tkinter as tk
from tkinter import ttk, messagebox
from threading import Thread
import os, sys, time, asyncio, json, platform
from pythonosc import udp_client
from bleak import BleakScanner
from garmin_core import GarminCore

CONFIG_FILE = "config.json"

class BioChuggerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("BIO-CHUGGER PRO")
        self.root.geometry("600x750")
        self.root.configure(bg="#050505")

        # LOGIC STATE
        self.current_bpm = 120
        self.time_signature = 4
        self.is_muted = False
        self.broadcasting = False # Toggle for REAPER
        self.points = [100] * 60
        self.config = self.load_config()
        self.watch_id = self.config.get("watch_id", "")
        self.osc_client = udp_client.SimpleUDPClient("127.0.0.1", 8000)
        self.core = None

        # UI: BPM & BUTTONS
        self.bpm_text = tk.Label(root, text="---", fg="#444", bg="#050505", font=("Helvetica", 90, "bold"))
        self.bpm_text.pack(pady=10)

        self.ctrl_frame = tk.Frame(root, bg="#050505")
        self.ctrl_frame.pack(pady=10)

        self.mute_btn = tk.Button(self.ctrl_frame, text="MUTE CLICK", command=self.toggle_mute, width=12)
        self.mute_btn.pack(side="left", padx=10)

        self.server_btn = tk.Button(self.ctrl_frame, text="START BROADCAST", command=self.toggle_server, width=15, highlightbackground="#555")
        self.server_btn.pack(side="left", padx=10)

        self.scan_btn = tk.Button(root, text="SCAN FOR DEVICES", command=self.start_scan, width=20)
        self.scan_btn.pack(pady=5)

        self.device_list = ttk.Treeview(root, columns=("ID", "Name"), show="headings", height=5)
        self.device_list.heading("ID", text="Device ID")
        self.device_list.heading("Name", text="Device Name")
        self.device_list.column("ID", width=250)
        self.device_list.column("Name", width=250)
        self.device_list.pack(pady=10, padx=10)
        self.device_list.bind("<Double-1>", self.on_device_select)

        self.canvas = tk.Canvas(root, width=580, height=120, bg="#000", highlightthickness=0)
        self.canvas.pack(pady=10)

        self.status_text = tk.Label(root, text="BOOTING...", fg="#555", bg="#050505", font=("Courier", 12))
        self.status_text.pack(side="bottom", pady=20)

        # 1. AUTO-START WATCH CONNECTION if ID exists
        if self.watch_id:
            self.init_watch_connection()
        else:
            self.update_status("PLEASE SCAN AND SELECT A DEVICE", "orange")
        
        # 2. START ENGINE
        Thread(target=self.metronome_engine, daemon=True).start()
        self.animate_wave()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        return {}

    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump({"watch_id": self.watch_id}, f)

    def init_watch_connection(self):
        if self.core:
            self.core.stop()
        
        def run_core():
            self.core = GarminCore(
                watch_id=self.watch_id,
                callback=lambda bpm: self.root.after(0, self.update_bpm, bpm),
                status_callback=lambda msg, color: self.root.after(0, self.update_status, msg, color)
            )
            asyncio.run(self.core.start())
        Thread(target=run_core, daemon=True).start()

    def start_scan(self):
        self.scan_btn.config(state="disabled", text="SCANNING...")
        self.device_list.delete(*self.device_list.get_children())
        
        async def scan():
            devices = await BleakScanner.discover(timeout=5.0)
            for d in devices:
                name = d.name if d.name else "Unknown"
                self.device_list.insert("", "end", values=(d.address, name))
            self.scan_btn.config(state="normal", text="SCAN FOR DEVICES")

        def run_scan():
            asyncio.run(scan())
        
        Thread(target=run_scan, daemon=True).start()

    def on_device_select(self, event):
        item = self.device_list.selection()[0]
        self.watch_id = self.device_list.item(item, "values")[0]
        self.save_config()
        messagebox.showinfo("Success", f"Connected to device: {self.watch_id}")
        self.init_watch_connection()

    def toggle_server(self):
        """Toggles the broadcast to REAPER on/off."""
        self.broadcasting = not self.broadcasting
        if self.broadcasting:
            self.server_btn.config(text="STOP BROADCAST", highlightbackground="#00ff00")
            self.update_status("● BROADCASTING TO REAPER", "#00ff00")
        else:
            self.server_btn.config(text="START BROADCAST", highlightbackground="#555")
            self.update_status("● WATCH LINKED (STDBY)", "#00ff00")

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        self.mute_btn.config(text="UNMUTE" if self.is_muted else "MUTE CLICK")

    def update_bpm(self, bpm):
        self.current_bpm = bpm
        self.bpm_text.config(text=str(bpm), fg="#00ff00")
        # Only send to REAPER if the toggle is ON
        if self.broadcasting:
            self.osc_client.send_message("/tempo", float(bpm))

    def update_status(self, message, color):
        self.status_text.config(text=message, fg=color)

    def metronome_engine(self):
        beat = 1
        while True:
            # Prevent division by zero if current_bpm is somehow 0 or invalid
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
                    # Fallback for Linux or others if needed
                    print("\a", end="", flush=True) # Terminal bell
            
            self.points[-2], self.points[-1] = (20, 160) if beat == 1 else (50, 130)
            beat = (beat % self.time_signature) + 1
            time.sleep(delay)

    def animate_wave(self):
        self.canvas.delete("wave")
        self.points.append(100)
        if len(self.points) > 60: self.points.pop(0)
        for i in range(len(self.points)-1):
            self.canvas.create_line(i*10, self.points[i], (i+1)*10, self.points[i+1], fill="#00ff00", width=2, tags="wave")
        self.root.after(40, self.animate_wave)

if __name__ == "__main__":
    root = tk.Tk()
    # On macOS, topmost might require special handling or just work
    try:
        root.attributes('-topmost', True)
    except:
        pass
    app = BioChuggerApp(root)
    root.mainloop()
