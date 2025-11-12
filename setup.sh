#!/bin/bash
# Setup-Script für Nippelboard Funk auf Raspberry Pi

echo "======================================"
echo "Nippelboard Funk - Setup"
echo "======================================"
echo

# Prüfe ob auf Raspberry Pi
if [ ! -f /proc/device-tree/model ] || ! grep -q "Raspberry Pi" /proc/device-tree/model; then
    echo "⚠️  Warnung: Läuft nicht auf Raspberry Pi!"
    echo "GPIO-Funktionen werden nicht verfügbar sein."
    read -p "Trotzdem fortfahren? (j/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Jj]$ ]]; then
        exit 1
    fi
fi

# Update System
echo "📦 Aktualisiere System..."
sudo apt-get update

# Installiere System-Pakete
echo "📦 Installiere System-Pakete..."
sudo apt-get install -y \
    python3-pyqt5 \
    python3-pyqt5.qtmultimedia \
    portaudio19-dev \
    python3-dev \
    libasound2-dev \
    ffmpeg \
    python3-pip \
    python3-venv

# Erstelle Virtual Environment (optional)
read -p "Virtual Environment erstellen? (empfohlen) (j/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Jj]$ ]]; then
    echo "🐍 Erstelle Virtual Environment..."
    python3 -m venv venv
    source venv/bin/activate
fi

# Installiere Python-Pakete
echo "🐍 Installiere Python-Pakete..."
pip3 install -r requirements.txt

# Erstelle Konfiguration
if [ ! -f config.yaml ]; then
    echo "⚙️  Erstelle Konfiguration..."
    cp config.yaml.example config.yaml

    echo
    echo "⚠️  WICHTIG: Bitte ändern Sie das Verschlüsselungs-Passwort!"
    echo "   Bearbeiten Sie config.yaml und ändern Sie 'crypto.encryption_password'"
    read -p "Jetzt bearbeiten? (j/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Jj]$ ]]; then
        nano config.yaml
    fi
fi

# Erstelle Verzeichnisse
echo "📁 Erstelle Verzeichnisse..."
mkdir -p data/sounds data/recordings/clips data/recordings/panic assets/icons

# USB-Soundkarte testen
echo
echo "🔊 Teste Audio-Geräte..."
python3 << EOF
import sounddevice as sd
print("\n📡 Verfügbare Audio-Geräte:")
print(sd.query_devices())
EOF

# Autostart einrichten
echo
read -p "Autostart bei Boot einrichten? (j/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Jj]$ ]]; then
    echo "⚙️  Richte Autostart ein..."

    # Passe Service-Datei an
    SERVICE_FILE="nippelboard.service"
    INSTALL_DIR=$(pwd)

    sed -i "s|/home/pi/Nippelboard_Funk|$INSTALL_DIR|g" $SERVICE_FILE

    # Installiere Service
    sudo cp $SERVICE_FILE /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable nippelboard.service

    echo "✓ Autostart eingerichtet"
    echo "  Start: sudo systemctl start nippelboard"
    echo "  Stop:  sudo systemctl stop nippelboard"
    echo "  Log:   sudo journalctl -u nippelboard -f"
fi

# GPIO Berechtigungen
if [ -d /sys/class/gpio ]; then
    echo
    echo "🔧 Setze GPIO-Berechtigungen..."
    sudo usermod -a -G gpio $USER
    echo "✓ Benutzer zur gpio-Gruppe hinzugefügt"
    echo "  WICHTIG: Bitte neu anmelden oder neu starten!"
fi

echo
echo "======================================"
echo "✓ Setup abgeschlossen!"
echo "======================================"
echo
echo "Starten mit:"
echo "  python3 main.py"
echo
echo "Oder bei Virtual Environment:"
echo "  source venv/bin/activate"
echo "  python3 main.py"
echo
echo "Bei Autostart:"
echo "  sudo systemctl start nippelboard"
echo
echo "⚠️  Vergessen Sie nicht:"
echo "  1. Passwort in config.yaml ändern!"
echo "  2. USB-Soundkarte anschließen"
echo "  3. GPIO-Buttons anschließen (Pin 17 & 27)"
echo
