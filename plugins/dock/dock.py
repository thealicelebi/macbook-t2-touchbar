#!/usr/bin/env python3
import sys
import os
import json
import re
import select
import time
import socket
import subprocess
from pathlib import Path

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, Gdk, GdkPixbuf
import cairo

DESKTOP_DIRS = [
    Path.home() / ".local/share/applications",
    Path("/usr/local/share/applications"),
    Path("/usr/share/applications"),
    Path("/var/lib/snapd/desktop/applications"),
    Path("/var/lib/flatpak/exports/share/applications"),
]

def return_to_control():
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect("/run/touchbard/touchbard.sock")
        s.sendall(b'{"t":"layer","name":"control"}\n')
        s.close()
    except Exception:
        subprocess.Popen(["touchbar-agent", "--layer", "control"])

def get_dock_apps():
    try:
        out = subprocess.check_output(
            ["gsettings", "get", "org.gnome.shell", "favorite-apps"],
            text=True, timeout=1
        )
        app_ids = re.findall(r"'([^']+)'", out)
    except Exception:
        app_ids = []

    apps = []
    for app_id in app_ids:
        path = None
        for d in DESKTOP_DIRS:
            candidate = d / app_id
            if candidate.exists():
                path = candidate
                break
        if not path:
            continue

        name, icon, exec_cmd = app_id.replace(".desktop", ""), None, None
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("Name=") and not name:
                        name = line.split("=", 1)[1]
                    elif line.startswith("Icon=") and not icon:
                        icon = line.split("=", 1)[1]
                    elif line.startswith("Exec=") and not exec_cmd:
                        exec_cmd = line.split("=", 1)[1]
        except Exception:
            continue

        if icon:
            apps.append({
                "id": app_id,
                "path": str(path),
                "name": name,
                "icon": icon,
                "exec": re.sub(r"%[a-zA-Z]", "", exec_cmd or "").strip()
            })
    return apps

class DockRenderer:
    def __init__(self):
        self.w = 1850
        self.h = 60
        self.icon_size = 40
        self.slot_w = 66
        self.theme = Gtk.IconTheme.get_default()
        self.apps = []
        self.opened_at = None
        self.pressed_idx = None
        self.reload_apps()

    def reload_apps(self):
        self.apps = get_dock_apps()

    def load_pixbuf(self, icon_name):
        try:
            if icon_name.startswith("/") and os.path.exists(icon_name):
                return GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_name, self.icon_size, self.icon_size, True)
            icon_info = self.theme.lookup_icon(icon_name, self.icon_size, Gtk.IconLookupFlags.FORCE_SIZE)
            if icon_info:
                return icon_info.load_icon()
        except Exception:
            pass
        try:
            return self.theme.load_icon("application-x-executable", self.icon_size, 0)
        except Exception:
            return None

    def render(self):
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.w, self.h)
        cr = cairo.Context(surface)
        cr.set_source_rgb(0.0, 0.0, 0.0)
        cr.paint()

        x_offset = 12
        for i, app in enumerate(self.apps):
            slot_x = x_offset + (i * self.slot_w)
            if slot_x + self.slot_w > self.w:
                break

            # DOKUNMA EFEKTİ (Neon Amethyst Glow)
            if self.pressed_idx == i:
                cr.set_source_rgba(0.75, 0.52, 0.99, 0.40)
                cr.rectangle(slot_x + 4, 6, self.slot_w - 8, self.h - 12)
                cr.fill()
                cr.set_source_rgba(0.85, 0.65, 1.0, 0.9)
                cr.set_line_width(2.0)
                cr.rectangle(slot_x + 4, 6, self.slot_w - 8, self.h - 12)
                cr.stroke()

            pb = self.load_pixbuf(app["icon"])
            if pb:
                ix = slot_x + (self.slot_w - pb.get_width()) // 2
                iy = (self.h - pb.get_height()) // 2
                Gdk.cairo_set_source_pixbuf(cr, pb, ix, iy)
                cr.paint()

        surface.flush()
        data = bytes(surface.get_data())
        header = (json.dumps({"t": "frame", "w": self.w, "h": self.h, "len": len(data)}) + "\n").encode()
        sys.stdout.buffer.write(header + data)
        sys.stdout.buffer.flush()

    def handle_tap(self, tap_x):
        x_offset = 12
        idx = int((tap_x - x_offset) // self.slot_w)
        if 0 <= idx < len(self.apps):
            self.pressed_idx = idx
            self.render()
            app = self.apps[idx]
            try:
                subprocess.Popen(["gtk-launch", app["id"]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                try:
                    subprocess.Popen(["gio", "launch", app["path"]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass
            time.sleep(0.09)  # Efektin net görünmesi için mikro bekleme
        self.pressed_idx = None
        self.opened_at = None
        return_to_control()

def main():
    dock = DockRenderer()
    dock.render()
    last_frame = time.time()
    last_dock_check = 0
    cached_dock_raw = ""

    while True:
        r, _, _ = select.select([sys.stdin], [], [], 0.2)
        if r:
            line = sys.stdin.readline()
            if not line:
                break
            try:
                msg = json.loads(line)
            except Exception:
                continue
            t = msg.get("t")
            if t == "size":
                dock.w = int(msg.get("w", 1850))
                dock.h = int(msg.get("h", 60))
                dock.render()
                dock.opened_at = time.time()
                last_frame = time.time()
            elif t == "cmd" and msg.get("cmd") == "tap":
                dock.handle_tap(float(msg.get("x", 0)))
                last_frame = time.time()

        now = time.time()
        if dock.opened_at and (now - dock.opened_at >= 5.0):
            dock.opened_at = None
            return_to_control()

        if now - last_dock_check >= 1.0:
            last_dock_check = now
            try:
                raw = subprocess.check_output(
                    ["gsettings", "get", "org.gnome.shell", "favorite-apps"],
                    text=True, timeout=1
                ).strip()
            except Exception:
                raw = ""
            if raw and raw != cached_dock_raw:
                cached_dock_raw = raw
                dock.reload_apps()
                dock.render()
                last_frame = now

        if dock.w > 0 and (now - last_frame >= 0.7):
            dock.render()
            last_frame = now

if __name__ == "__main__":
    main()
