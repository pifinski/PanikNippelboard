# 🚀 Schnellstart: Sichere Verschlüsselung einrichten

**Ziel:** Panik-Aufnahmen so verschlüsseln, dass nur Sie sie entschlüsseln können - auch bei Beschlagnahmung!

---

## ⏱️ 5-Minuten-Setup

### 1️⃣ Schlüsselpaar generieren (auf Ihrem PC)

```bash
# AUF IHREM PC (NICHT auf Raspberry Pi!)
cd Nippelboard_Funk
python -m src.crypto.asymmetric generate --password
```

**Eingaben:**
- Passwort für Private Key: `[Ihr sicheres Passwort]`
- Passwort bestätigen: `[Ihr sicheres Passwort]`

**Ergebnis:**
```
✓ Schlüsselpaar generiert!
====================================
📁 Public Key:  ./public_key.pem
   → Kopieren Sie diesen auf den Raspberry Pi

🔐 Private Key: ./private_key.pem
   → BEWAHREN SIE DIESEN SICHER AUF!
   → USB-Stick, verschlüsselter Speicher, Tresor
   → NICHT auf Raspberry Pi lassen!
```

---

### 2️⃣ Public Key auf Raspberry Pi kopieren

```bash
# Von Ihrem PC aus:
scp public_key.pem pi@raspberrypi.local:/home/pi/Nippelboard_Funk/
```

---

### 3️⃣ Private Key sicher aufbewahren

**Wichtig:** Private Key **NIEMALS** auf Raspberry Pi lassen!

**Sichere Orte:**
- 💾 USB-Stick (verschlüsselt)
- 🏠 Externes Backup (zu Hause)
- ☁️ Verschlüsselter Cloud-Speicher

**Backup erstellen:**
```bash
# Erstelle mehrere Kopien
cp private_key.pem private_key_backup1.pem
cp private_key.pem private_key_backup2.pem

# Kopiere auf USB-Stick
cp private_key.pem /media/usb-stick/nippelboard_private_key.pem

# Lösche Original von PC (optional, nach Backup!)
# shred -vfz -n 10 private_key.pem
```

---

### 4️⃣ Config auf Raspberry Pi anpassen

```bash
# SSH zum Raspberry Pi
ssh pi@raspberrypi.local
cd /home/pi/Nippelboard_Funk

# Config bearbeiten
nano config.yaml
```

**Ändern Sie:**
```yaml
crypto:
  mode: 'asymmetric'  # ← WICHTIG!
  public_key_path: './public_key.pem'
```

Speichern mit `Ctrl+O`, `Enter`, `Ctrl+X`

---

### 5️⃣ Test durchführen

```bash
# Starte Nippelboard
python3 main.py

# Im GUI:
# 1. Klicke "🚨 Panik-Modus"
# 2. Warte 5 Sekunden
# 3. Klicke erneut "🚨 PANIK AKTIV - STOP"

# Prüfe Verschlüsselung
ls -lh data/recordings/panic/
# Sollte .enc Datei zeigen
```

---

## 🔓 Aufnahme entschlüsseln

**Auf Ihrem PC** (mit Private Key):

```bash
# 1. Hole verschlüsselte Datei vom Raspberry Pi
scp pi@raspberrypi.local:/home/pi/Nippelboard_Funk/data/recordings/panic/panic_*.enc .

# 2. Entschlüssele
python -m src.crypto.asymmetric decrypt \
    panic_20250112_143022.mp3.enc \
    panic_20250112_143022.mp3 \
    /pfad/zu/private_key.pem

# 3. Passwort eingeben
Passwort für Private Key: [Ihr Passwort]

# ✓ Fertig! Datei: panic_20250112_143022.mp3
```

---

## ✅ Checkliste

- [ ] Schlüsselpaar generiert (mit Passwort!)
- [ ] Public Key auf Raspberry Pi
- [ ] Private Key **NICHT** auf Raspberry Pi
- [ ] Private Key an 2+ Orten gesichert
- [ ] `config.yaml`: `mode: 'asymmetric'`
- [ ] Test-Verschlüsselung erfolgreich
- [ ] Test-Entschlüsselung erfolgreich

---

## ⚠️ Wichtige Warnungen

1. **Private Key verloren = Daten verloren!**
   → Erstellen Sie Backups!

2. **Private Key auf Raspberry Pi = UNSICHER!**
   → Bei Beschlagnahmung können Aufnahmen entschlüsselt werden

3. **Passwort vergessen = Daten verloren!**
   → Notieren Sie das Passwort sicher (nicht digital!)

4. **Keine Backups = Risiko!**
   → USB-Stick kann kaputt gehen, Cloud-Account gesperrt werden

---

## 🆘 Bei Problemen

### "Public Key nicht gefunden"
```bash
# Prüfe ob Datei existiert
ls -l /home/pi/Nippelboard_Funk/public_key.pem

# Falls nicht: Erneut kopieren
scp public_key.pem pi@raspberrypi.local:/home/pi/Nippelboard_Funk/
```

### "Private Key decrypt failed"
- Falsches Passwort eingegeben?
- Falscher Private Key verwendet?
- Datei manipuliert/beschädigt?

### Weitere Hilfe
→ Siehe ausführliche Anleitung: [SICHERHEIT.md](SICHERHEIT.md)

---

## 📚 Mehr Informationen

- **Ausführliche Sicherheitsanleitung:** [SICHERHEIT.md](SICHERHEIT.md)
- **Technische Details:** [SICHERHEIT.md - Technische Details](SICHERHEIT.md#-technische-details)
- **Rechtliche Hinweise:** [SICHERHEIT.md - Rechtliche Hinweise](SICHERHEIT.md#-rechtliche-hinweise)

---

**Zusammenfassung:**

```
┌────────────────────────────────────────┐
│ Raspberry Pi (kann beschlagnahmt sein) │
│ ✓ public_key.pem                       │
│ ✗ private_key.pem (NICHT hier!)        │
│ → Entschlüsselung UNMÖGLICH            │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│ Ihr sicherer Speicher                  │
│ 🔒 private_key.pem + Passwort          │
│ → Nur Sie können entschlüsseln!        │
└────────────────────────────────────────┘
```

**Sie sind jetzt geschützt! 🛡️**
