# BIO-CHUGGER PRO: Heart Rate Metronome & REAPER Bridge

BIO-CHUGGER PRO is a biological signal metronome that syncs your heart rate from a Garmin watch (or any device broadcasting standard Heart Rate BLE data) directly into your DAW.

## Features
- **Real-time Heart Rate Metronome:** Hear your pulse as a click track.
- **REAPER Sync:** Broadcast your heart rate to REAPER to set the project tempo live.
- **Cross-Platform:** Works on macOS and Windows.
- **Device Scanning:** Easily scan and save your watch's Bluetooth ID.
- **Auto-Reconnect:** Automatically tries to reconnect if the link is dropped.

## Installation (Local/Developer)

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd hr_metronome
   ```

2. **Set up a Virtual Environment (Recommended):**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install bleak python-osc
   ```

4. **Run the app:**
   ```bash
   python main.py
   ```

## Usage

1. **Scan for Devices:** Click the "SCAN FOR DEVICES" button.
2. **Select Device:** Double-click your Garmin watch (e.g., "Forerunner 955") in the list to save it as the target.
3. **Connect:** The app will attempt to link. Make sure your watch has "Virtual Run" or "Broadcast Heart Rate" active.
4. **Mute Click:** Toggle the metronome sound.
5. **Broadcast:** Click "START BROADCAST" to send OSC data to REAPER.

---

## REAPER Setup (Live Tempo Sync)

To allow BIO-CHUGGER to control REAPER's tempo, you must configure REAPER to listen for OSC messages.

### 1. Manual OSC Setup (Recommended)

1. Open REAPER **Preferences** (`Ctrl/Cmd + ,`).
2. Go to **Control/OSC/web**.
3. Click **Add**.
4. Set **Control surface mode** to `OSC (Open Sound Control)`.
5. Name it `BioChugger`.
6. Set **Mode** to `Local port`.
7. Set **Local listen port** to `8000`.
8. Under **Pattern config**, click **Open config directory**.
9. Create a new file named `BioChugger.ReaperOSC` and paste the following line:
   ```text
   TEMPO f/tempo
   ```
10. Select `BioChugger` in the Pattern Config dropdown in REAPER.
11. Click **OK**.

### 2. OSC Listener Script (Alternative)

If you prefer a script-based approach, you can use the following REAPER Lua script. Note that this requires REAPER's built-in OSC to be enabled as described above, or a custom listener.

Save this as `BioChugger_Listener.lua` in your REAPER Scripts folder:

```lua
-- REAPER Bio-Chugger Listener (Passive)
-- This script doesn't actually 'receive' the UDP (REAPER does that)
-- but it can be used to monitor the status or perform extra actions.

function main()
  -- The tempo is handled automatically by REAPER if the OSC pattern is set.
  -- You can add custom logic here if needed.
  reaper.defer(main)
end

-- main()
```

## Packaging for Release

The project includes a GitHub Actions workflow that automatically builds executables for macOS and Windows when a tag (e.g., `v1.0.0`) is pushed.

To build locally with PyInstaller:
```bash
# Windows
pyinstaller --noconfirm --onefile --windowed --name "BioChugger" main.py

# macOS
pyinstaller --noconfirm --windowed --name "BioChugger" main.py
```

## Troubleshooting
- **No devices found:** Ensure Bluetooth is enabled and the Garmin watch is in "Broadcast HR" or "Virtual Run" mode.
- **Not connecting to REAPER:** Verify the port (8000) and that the BioChugger.ReaperOSC pattern is correctly mapped.
