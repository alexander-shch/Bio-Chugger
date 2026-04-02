# BIO-CHUGGER PRO: Heart Rate Metronome & REAPER Bridge

BIO-CHUGGER PRO is a biological signal metronome that syncs your heart rate from a Garmin watch (or any device broadcasting standard Heart Rate BLE data) directly into your DAW.

[![Releases](https://img.shields.io/github/v/release/alexander-shch/Bio-Chugger?style=for-the-badge)](https://github.com/alexander-shch/Bio-Chugger/releases)

## 📥 Download
Download the latest pre-built executables for **macOS** and **Windows** from the [Releases Page](https://github.com/alexander-shch/Bio-Chugger/releases).

## Features
- **Real-time Heart Rate Metronome:** Hear your pulse as a click track.
- **Material Design UI:** Modern, high-contrast interface with Light and Dark mode support.
- **REAPER Sync:** Broadcast your heart rate to REAPER to set the project tempo live via OSC.
- **Cross-Platform:** Works on macOS and Windows.
- **Device Scanning:** Easily scan and save your watch's Bluetooth ID.
- **Auto-Reconnect:** Automatically tries to reconnect if the link is dropped.

## Usage

1. **Scan for Devices:** Click the "SCAN FOR DEVICES" button.
2. **Select Device:** Double-click your Garmin watch (e.g., "Forerunner 955") in the list to save it as the target.
3. **Connect:** The app will attempt to link. Make sure your watch has "Virtual Run" or "Broadcast Heart Rate" active.
4. **Mute Click:** Toggle the metronome sound.
5. **Theme:** Toggle between Light and Dark mode using the theme button.
6. **Broadcast:** Click "START BROADCAST" to send OSC data to REAPER.

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

If you prefer a script-based approach, you can use the included `reaper_listener.lua` script in your REAPER Scripts folder.

## Installation (For Developers)

1. **Clone the repository:**
   ```bash
   git clone git@github.com:alexander-shch/Bio-Chugger.git
   cd Bio-Chugger
   ```

2. **Set up a Virtual Environment (Recommended):**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install bleak python-osc
   ```

4. **Run the app:**
   ```bash
   python3 main.py
   ```

## Packaging for Release

The project includes a GitHub Actions workflow that automatically builds executables for macOS and Windows.

To build locally with PyInstaller:
```bash
# Windows
pyinstaller --noconfirm --onefile --windowed --name "Bio-Chugger-Win" main.py

# macOS
pyinstaller --noconfirm --windowed --name "Bio-Chugger-Mac" main.py
```

## Troubleshooting
- **No devices found:** Ensure Bluetooth is enabled and the Garmin watch is in "Broadcast HR" or "Virtual Run" mode.
- **Not connecting to REAPER:** Verify the port (8000) and that the `BioChugger.ReaperOSC` pattern is correctly mapped.
- **Permissions:** On macOS, the first time you run the app, you may need to allow Bluetooth permissions in System Settings.
