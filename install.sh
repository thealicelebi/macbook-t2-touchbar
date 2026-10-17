#!/usr/bin/env bash
set -e

echo "=== MacBook T2 Ubuntu Touch Bar Kurulumu Başlatılıyor ==="

echo "[1/4] Bağımlılıklar yükleniyor..."
sudo apt update
sudo apt install -y python3-gi python3-cairo gir1.2-gtk-3.0 gir1.2-rsvg-2.0 \
                    gnome-screenshot brightnessctl pulseaudio-utils

echo "[2/4] Parlaklık ve LED yetkileri ayarlanıyor..."
sudo usermod -aG video,input "$USER"
sudo tee /etc/udev/rules.d/99-backlight-permissions.rules > /dev/null << 'RULE'
SUBSYSTEM=="backlight", RUN+="/bin/chmod 666 /sys/class/backlight/%k/brightness"
SUBSYSTEM=="leds", RUN+="/bin/chmod 666 /sys/class/leds/%k/brightness"
RULE
sudo udevadm control --reload-rules && sudo udevadm trigger || true

echo "[3/4] Dosyalar kopyalanıyor..."
sudo cp bin/touchbar-agent /usr/local/bin/touchbar-agent
sudo chmod +x /usr/local/bin/touchbar-agent

mkdir -p "$HOME/.config/touchbar"
cp config/config.toml "$HOME/.config/touchbar/config.toml"
cp -r plugins "$HOME/.config/touchbar/"
chmod +x "$HOME"/.config/touchbar/plugins/*/*.py

echo "[4/4] Servisler yenileniyor..."
systemctl --user restart touchbar-agent.service || true

echo "=== Kurulum Tamamlandı! ==="
