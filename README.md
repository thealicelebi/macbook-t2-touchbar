# MacBook T2 Linux Touch Bar Enhancement (Ubuntu 24.04 Noble)

A polished, fully customized Touch Bar experience tailored for Apple T2 MacBook Pros (specifically tested on **MacBookPro15,4 / A2159 - 13" 2019**) running **Ubuntu 24.04 LTS (Noble Numbat)** with GNOME on Wayland.

Built on top of the `touchbard` ecosystem, this configuration bridges the gap between the low-level T2 drivers and the modern Ubuntu desktop.

---

## ✨ Key Features

### 🎨 Live Color Ubuntu Dock
- **Authentic System Icons:** Dynamically reads your pinned GNOME favorites (`org.gnome.shell favorite-apps`) and renders high-resolution, full-color vector icons directly from your active Yaru/system theme using Cairo & GdkPixbuf.
- **Interactive App Launcher:** Tap any icon to launch the application with zero latency.
- **Smart Auto-Exit:** Automatically switches back to your primary control strip immediately upon app launch, or after a 5-second inactivity timeout.
- **Auto-Sync:** Real-time synchronization whenever you add or remove dock shortcuts on your Ubuntu desktop.

### 🌤️ Interactive 5-City Weather Center
- **Multi-City Overview:** Instant live temperature, weather conditions, and vibrant icons for **Istanbul, Bursa, Adıyaman, Edirne, and İzmir** (powered by Open-Meteo).
- **Hourly Detailed Forecast:** Tap any city card to expand an 8-hour detailed breakdown showing upcoming temperatures, animated state glyphs, and precipitation chances (`%`).
- **One-Tap Return:** Tap the back button or wait for the 8-second auto-return to revert to the main bar.

### 💡 Native Hardware Controls (T2 A2159)
- **Display Brightness:** Accurately bound to the `acpi_video0` backlight interface.
- **Keyboard Illumination:** Smooth slider mapped directly to `apple::kbd_backlight`.
- **Integrated Udev Rules:** Configures non-root write access to hardware brightness paths, eliminating permission hiccups.

### 📸 One-Tap Interactive Screenshot
- Dedicated camera button invoking the native GNOME interactive screen capture portal.

### 🎵 Media & Amethyst Visualizer
- MPRIS media playback controls (Play/Pause, Next, Previous) alongside custom "Amethyst" themed spectrum bars.

---

## 📋 Requirements

Before installation, ensure you have:
1. An Apple T2 MacBook running Linux with the [T2 Linux Kernel](https://t2linux.org/).
2. The core `touchbard` system service installed and running (`systemctl status touchbard.service`).
3. An active GNOME Wayland desktop session on Ubuntu 24.04 LTS.

---

## 🚀 Quick Installation

Clone this repository and run the automated installation script:

```bash
git clone [https://github.com/](https://github.com/)<YOUR_GITHUB_USERNAME>/macbook-t2-touchbar.git
cd macbook-t2-touchbar
chmod +x install.sh
./install.sh