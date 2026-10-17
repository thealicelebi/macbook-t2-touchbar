#!/usr/bin/env python3
import sys
import os
import json
import select
import time
import socket
import datetime
import threading
import urllib.request
import cairo

CITIES = [
    {"id": "ist", "name": "İstanbul", "lat": 41.0082, "lon": 28.9784, "temp": "--", "icon": "\U000F0599", "desc": "Yükleniyor", "color": (0.95, 0.75, 0.2), "hourly": []},
    {"id": "brs", "name": "Bursa",    "lat": 40.1885, "lon": 29.0610, "temp": "--", "icon": "\U000F0595", "desc": "Yükleniyor", "color": (0.7, 0.8, 0.95), "hourly": []},
    {"id": "ady", "name": "Adıyaman", "lat": 37.7648, "lon": 38.2786, "temp": "--", "icon": "\U000F0599", "desc": "Yükleniyor", "color": (0.95, 0.75, 0.2), "hourly": []},
    {"id": "edr", "name": "Edirne",   "lat": 41.6772, "lon": 26.5557, "temp": "--", "icon": "\U000F0597", "desc": "Yükleniyor", "color": (0.4, 0.65, 0.95), "hourly": []},
    {"id": "izm", "name": "İzmir",    "lat": 38.4192, "lon": 27.1287, "temp": "--", "icon": "\U000F0599", "desc": "Yükleniyor", "color": (0.95, 0.75, 0.2), "hourly": []},
]

WMO = {
    0: ("Açık", "\U000F0599", (0.95, 0.75, 0.2)),
    1: ("Az Bulutlu", "\U000F0595", (0.7, 0.8, 0.95)),
    2: ("Parçalı", "\U000F0595", (0.7, 0.8, 0.95)),
    3: ("Kapalı", "\U000F0590", (0.6, 0.65, 0.7)),
    45: ("Sisli", "\U000F0591", (0.55, 0.6, 0.65)),
    51: ("Çisenti", "\U000F0597", (0.4, 0.65, 0.95)),
    53: ("Çisenti", "\U000F0597", (0.4, 0.65, 0.95)),
    55: ("Yoğun Çisenti", "\U000F0597", (0.4, 0.65, 0.95)),
    61: ("Hafif Yağmur", "\U000F0597", (0.4, 0.65, 0.95)),
    63: ("Yağmurlu", "\U000F0597", (0.35, 0.6, 0.95)),
    65: ("Kuvvetli Yağış", "\U000F0596", (0.3, 0.5, 0.95)),
    71: ("Hafif Kar", "\U000F0598", (0.85, 0.9, 0.95)),
    73: ("Karlı", "\U000F0598", (0.85, 0.9, 0.95)),
    75: ("Yoğun Kar", "\U000F0F36", (0.9, 0.95, 1.0)),
    80: ("Sağanak", "\U000F0597", (0.4, 0.65, 0.95)),
    81: ("Kuvvetli Sağanak", "\U000F0596", (0.3, 0.5, 0.95)),
    82: ("Şiddetli Yağış", "\U000F0596", (0.25, 0.45, 0.9)),
    85: ("Kar Sağanağı", "\U000F0598", (0.85, 0.9, 0.95)),
    95: ("Gök Gürültülü", "\U000F067E", (0.85, 0.5, 0.9)),
    96: ("Dolu / Fırtına", "\U000F0592", (0.9, 0.45, 0.8)),
}

def return_to_control():
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect("/run/touchbard/touchbard.sock")
        s.sendall(b'{"t":"layer","name":"control"}\n')
        s.close()
    except Exception:
        pass

def fetch_single_city(city):
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={city['lat']}&longitude={city['lon']}"
        "&current=temperature_2m,weather_code,is_day"
        "&hourly=temperature_2m,weather_code,precipitation_probability"
        "&timezone=auto&forecast_days=2"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "touchbar-agent"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode())
            cur = data.get("current", {})
            t = cur.get("temperature_2m")
            code = cur.get("weather_code", 0)
            desc, icon, color = WMO.get(code, ("Açık", "\U000F0599", (0.95, 0.75, 0.2)))
            city["temp"] = f"{round(t)}°" if t is not None else "--"
            city["desc"] = desc
            city["icon"] = icon
            city["color"] = color

            # Saatlik tahminleri işle
            hourly = data.get("hourly", {})
            times = hourly.get("time", [])
            temps = hourly.get("temperature_2m", [])
            codes = hourly.get("weather_code", [])
            probs = hourly.get("precipitation_probability", [])

            now_str = datetime.datetime.now().strftime("%Y-%m-%dT%H:00")
            parsed_hours = []
            start = False
            for i, ts in enumerate(times):
                if ts >= now_str:
                    start = True
                if start and len(parsed_hours) < 8:
                    h_code = codes[i] if i < len(codes) else 0
                    h_desc, h_icon, h_col = WMO.get(h_code, ("Açık", "\U000F0599", (0.95, 0.75, 0.2)))
                    h_temp = f"{round(temps[i])}°" if i < len(temps) and temps[i] is not None else "--"
                    h_prob = probs[i] if i < len(probs) and probs[i] is not None else 0
                    parsed_hours.append({
                        "hour": ts.split("T")[1][:5],
                        "temp": h_temp,
                        "desc": h_desc,
                        "icon": h_icon,
                        "color": h_col,
                        "prob": f"%{h_prob}" if h_prob >= 15 else ""
                    })
            city["hourly"] = parsed_hours
    except Exception:
        pass

class WeatherBar:
    def __init__(self):
        self.w = 1850
        self.h = 60
        self.view = "cities"      # "cities" veya "detail"
        self.selected_city = 0   # Seçilen il indeksi
        self.opened_at = None
        self.needs_render = True
        self.start_fetch()

    def start_fetch(self):
        def worker():
            for c in CITIES:
                fetch_single_city(c)
                self.needs_render = True
        threading.Thread(target=worker, daemon=True).start()

    def render_cities(self, cr):
        # 5 Şehir Kartı
        card_w = (self.w - 20) // 5
        card_h = 50
        y_pos = 5

        for i, city in enumerate(CITIES):
            x_pos = 10 + (i * card_w)

            # Kart Arka Planı
            cr.set_source_rgb(0.09, 0.11, 0.16)
            cr.rectangle(x_pos + 4, y_pos, card_w - 8, card_h)
            cr.fill()

            # İnce Kart Çerçevesi
            cr.set_source_rgb(0.18, 0.22, 0.32)
            cr.set_line_width(1.2)
            cr.rectangle(x_pos + 4, y_pos, card_w - 8, card_h)
            cr.stroke()

            # Şehir İsmi
            cr.select_font_face("JetBrainsMono Nerd Font", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(14)
            cr.set_source_rgb(0.96, 0.95, 0.98)
            cr.move_to(x_pos + 14, y_pos + 22)
            cr.show_text(city["name"])

            # Durum Açıklaması
            cr.set_font_size(11)
            cr.set_source_rgb(0.65, 0.65, 0.75)
            cr.move_to(x_pos + 14, y_pos + 40)
            cr.show_text(city["desc"][:10])

            # Canlı İkon
            cr.set_font_size(19)
            r, g, b = city["color"]
            cr.set_source_rgb(r, g, b)
            cr.move_to(x_pos + card_w - 85, y_pos + 33)
            cr.show_text(city["icon"])

            # Derece
            cr.set_font_size(17)
            cr.set_source_rgb(0.65, 0.55, 0.98)
            cr.move_to(x_pos + card_w - 55, y_pos + 33)
            cr.show_text(city["temp"])

    def render_detail(self, cr):
        city = CITIES[self.selected_city]

        # 1. Sol: Geri Butonu
        cr.set_source_rgb(0.14, 0.17, 0.25)
        cr.rectangle(8, 7, 105, 46)
        cr.fill()
        cr.set_source_rgb(0.24, 0.29, 0.42)
        cr.set_line_width(1.2)
        cr.rectangle(8, 7, 105, 46)
        cr.stroke()

        cr.select_font_face("JetBrainsMono Nerd Font", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(13)
        cr.set_source_rgb(0.85, 0.88, 0.98)
        cr.move_to(16, 35)
        cr.show_text("‹ Şehirler")

        # 2. Şehir Başlığı & Anlık Bilgi
        cr.set_font_size(15)
        cr.set_source_rgb(0.65, 0.55, 0.98)
        cr.move_to(126, 26)
        cr.show_text(city["name"])

        cr.set_font_size(12)
        cr.set_source_rgb(0.75, 0.75, 0.85)
        cr.move_to(126, 44)
        cr.show_text(f"{city['temp']}  {city['desc']}")

        # 3. Sağ: 8 Saatlik Tahmin Şeridi
        hours = city.get("hourly", [])
        if not hours:
            cr.set_font_size(13)
            cr.set_source_rgb(0.6, 0.6, 0.7)
            cr.move_to(320, 35)
            cr.show_text("Saatlik tahmin yükleniyor...")
            return

        start_x = 280
        slot_w = (self.w - start_x - 10) // len(hours)

        for i, h in enumerate(hours):
            hx = start_x + (i * slot_w)

            # İnce ayırıcı dikey çizgi
            if i > 0:
                cr.set_source_rgb(0.14, 0.17, 0.25)
                cr.set_line_width(1.0)
                cr.move_to(hx, 10)
                cr.line_to(hx, 50)
                cr.stroke()

            # Saat
            cr.set_font_size(11)
            cr.set_source_rgb(0.65, 0.68, 0.75)
            cr.move_to(hx + 10, 20)
            cr.show_text(h["hour"])

            # İkon
            cr.set_font_size(15)
            r, g, b = h["color"]
            cr.set_source_rgb(r, g, b)
            cr.move_to(hx + 10, 38)
            cr.show_text(h["icon"])

            # Sıcaklık
            cr.set_font_size(13)
            cr.set_source_rgb(0.95, 0.95, 0.98)
            cr.move_to(hx + 32, 38)
            cr.show_text(h["temp"])

            # Yağış ihtimali
            if h["prob"]:
                cr.set_font_size(10)
                cr.set_source_rgb(0.4, 0.75, 1.0)
                cr.move_to(hx + 32, 51)
                cr.show_text(h["prob"])

    def render(self):
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.w, self.h)
        cr = cairo.Context(surface)
        cr.set_source_rgb(0.035, 0.043, 0.062)
        cr.paint()

        if self.view == "cities":
            self.render_cities(cr)
        else:
            self.render_detail(cr)

        surface.flush()
        data = bytes(surface.get_data())
        header = (json.dumps({"t": "frame", "w": self.w, "h": self.h, "len": len(data)}) + "\n").encode()
        sys.stdout.buffer.write(header + data)
        sys.stdout.buffer.flush()
        self.needs_render = False

    def handle_tap(self, tap_x):
        self.opened_at = time.time()  # Tıklama olunca 8 saniyelik sayaç sıfırlanır

        if self.view == "cities":
            card_w = (self.w - 20) // 5
            idx = int((tap_x - 10) // card_w)
            if 0 <= idx < 5:
                self.selected_city = idx
                self.view = "detail"
                self.needs_render = True
        else:
            # Detay ekranındayken sol butona (x <= 120) basılırsa şehir listesine dön
            if tap_x <= 120:
                self.view = "cities"
                self.needs_render = True

def main():
    wb = WeatherBar()
    last_frame = 0

    while True:
        r, _, _ = select.select([sys.stdin], [], [], 0.15)
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
                wb.w = int(msg.get("w", 1850))
                wb.h = int(msg.get("h", 60))
                wb.opened_at = time.time()
                wb.needs_render = True
            elif t == "cmd" and msg.get("cmd") == "tap":
                wb.handle_tap(float(msg.get("x", 0)))

        now = time.time()

        # 8 saniye boyunca işlem yapılmazsa ana kontrol ekranına dön
        if wb.opened_at and (now - wb.opened_at >= 8.0):
            wb.opened_at = None
            wb.view = "cities"
            return_to_control()

        # Ekranı çiz veya canlı tut
        if wb.w > 0 and (wb.needs_render or (now - last_frame >= 0.7)):
            wb.render()
            last_frame = now

if __name__ == "__main__":
    main()
