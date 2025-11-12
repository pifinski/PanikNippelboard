# Nippelboard Funk - Raspberry Pi Funküberwachung & Soundboard

Dieses System kombiniert Funküberwachung mit einem flexiblen Soundboard für Raspberry Pi 4.

## Features

### 1. Funk-Monitoring (Dashcam-Funktion)
- Kontinuierliche Aufnahme des Funkverkehrs über USB-Soundkarte
- Ringbuffer hält die letzten 45 Sekunden im Speicher
- Automatisches Überschreiben alter Daten

### 2. Clip-Speicherung (GPIO-Button)
- Bei Knopfdruck: Letzte 45s + nächste 15s speichern (60s Clip)
- Automatische Benennung mit Zeitstempel
- Komprimiertes Format (MP3/OGG)

### 3. Panik-Button (GPIO-Button)
- Startet vollständige Aufnahme bei Aktivierung
- Stoppt bei erneutem Drücken
- Verschlüsselte Speicherung (AES-256-GCM)
- Nur mit Passwort entschlüsselbar

### 4. Nippelboard (Soundboard)
- Grafische Oberfläche mit konfigurierbaren Buttons
- Eigene Sounds/Bilder pro Button
- Wiedergabe über Funkgerät (Kopfhörerausgang)
- Download von Sounds über Internet
- Audio-Editor zum Kürzen von Dateien
- Drag & Drop Anordnung

## Hardware-Anforderungen

- Raspberry Pi 4
- USB-Soundkarte (Stereo In/Out)
- 2x GPIO-Buttons (Clip-Button, Panik-Button)
- Funkgerät (Audio In/Out)
- Optional: Touchscreen für GUI

## Verkabelung

```
Funkgerät (Lautsprecher) -> USB-Soundkarte (Mikrofon-Eingang)
USB-Soundkarte (Kopfhörer) -> Funkgerät (Mikrofon-Eingang)

GPIO-Pins:
- GPIO 17: Clip-Button (+ GND)
- GPIO 27: Panik-Button (+ GND)
```

## Installation

```bash
# System-Pakete installieren
sudo apt-get update
sudo apt-get install -y python3-pyqt5 python3-pyqt5.qtmultimedia \
                        portaudio19-dev python3-dev libasound2-dev \
                        ffmpeg

# Python-Dependencies installieren
pip3 install -r requirements.txt

# Konfiguration kopieren und anpassen
cp config.yaml.example config.yaml
nano config.yaml
```

## Konfiguration

Bearbeiten Sie `config.yaml`:
- Audio-Geräte (USB-Soundkarte)
- GPIO-Pins
- Speicherpfade
- **Verschlüsselungs-Modus** (asymmetrisch empfohlen!)
- Nippelboard-Layout

### 🔐 Wichtig: Verschlüsselung bei Beschlagnahmung

**EMPFOHLEN:** Asymmetrische Verschlüsselung verwenden!

```bash
# 1. Schlüsselpaar generieren (auf Ihrem PC, NICHT auf Raspberry Pi!)
python -m src.crypto.asymmetric generate --password

# 2. Public Key auf Raspberry Pi kopieren
scp public_key.pem pi@raspberrypi:/home/pi/Nippelboard_Funk/

# 3. Private Key SICHER aufbewahren (USB-Stick, Tresor)
# NIEMALS auf Raspberry Pi lassen!

# 4. In config.yaml einstellen:
crypto:
  mode: 'asymmetric'
  public_key_path: './public_key.pem'
```

**Ergebnis:**
- Bei Beschlagnahmung: Nur Sie können mit Private Key entschlüsseln
- Raspberry Pi hat nur Public Key → kann nicht entschlüsseln

**Ausführliche Anleitung:** Siehe [SICHERHEIT.md](SICHERHEIT.md)

## Verwendung

```bash
# Starten
python3 main.py

# Autostart bei Boot (systemd)
sudo cp nippelboard.service /etc/systemd/system/
sudo systemctl enable nippelboard
sudo systemctl start nippelboard
```

## Verzeichnisstruktur

```
data/
├── sounds/           # Nippel-Sounddateien
├── recordings/       # Gespeicherte Clips
│   ├── clips/       # Normale Clips (45s vorher + 15s nachher)
│   └── panic/       # Verschlüsselte Panik-Aufnahmen
└── nippelboard.db   # SQLite Datenbank
```

## Sicherheit

- Panik-Aufnahmen werden mit AES-256-GCM verschlüsselt
- Passwort wird NICHT in Klartext gespeichert
- Entschlüsselung nur mit korrektem Passwort möglich
- Tool zur Entschlüsselung: `python3 -m src.crypto.decrypt <datei>`

## Performance-Optimierung

- MP3 mit variabler Bitrate (VBR) ~64kbps für Funk-Qualität
- Ringbuffer in RAM (mmap) für schnellen Zugriff
- Lazy-Loading von Sounds in GUI
- Effiziente SQLite-Indizes

## Lizenz

Privates Projekt für Medimeisterschaften
