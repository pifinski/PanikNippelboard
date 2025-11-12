# 🔐 Sicherheit bei Beschlagnahmung

## Problem: Symmetrische Verschlüsselung

Bei **symmetrischer Verschlüsselung** (Passwort-basiert):
- Passwort liegt in `config.yaml` auf dem Gerät
- Bei Beschlagnahmung können Behörden das Passwort auslesen
- **Alle Panik-Aufnahmen können entschlüsselt werden**

## ✅ Lösung: Asymmetrische Verschlüsselung (Public-Key)

### Wie funktioniert es?

1. **Public Key** (öffentlich) auf dem Raspberry Pi
   - Kann **nur verschlüsseln**
   - Kann **nicht entschlüsseln**

2. **Private Key** (geheim) nur bei Ihnen
   - USB-Stick, verschlüsselter PC, Tresor
   - **Einzig möglicher Weg zur Entschlüsselung**

3. Bei Beschlagnahmung:
   - Gerät hat nur Public Key → kann nicht entschlüsseln
   - **Nur Sie** mit Private Key können Aufnahmen öffnen

### Praktisches Beispiel

```
┌─────────────────────────────────────────────┐
│ Raspberry Pi (kann beschlagnahmt werden)    │
│                                             │
│ ✓ public_key.pem (verschlüsselt)           │
│ ✗ private_key.pem (NICHT vorhanden!)       │
│                                             │
│ → Panik-Aufnahmen: verschlüsselt           │
│ → Entschlüsselung: UNMÖGLICH ohne Private  │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Ihr sicherer Speicher (zu Hause)           │
│                                             │
│ 🔒 private_key.pem (NUR HIER!)             │
│                                             │
│ → Damit können Sie entschlüsseln           │
│ → Niemand sonst hat Zugriff                │
└─────────────────────────────────────────────┘
```

---

## 🚀 Einrichtung: Schritt für Schritt

### Schritt 1: Schlüsselpaar generieren

Auf Ihrem **persönlichen PC** (NICHT auf Raspberry Pi):

```bash
# Generiere Schlüsselpaar (RSA-4096)
python -m src.crypto.asymmetric generate --password

# Passwort für Private Key eingeben (EMPFOHLEN!)
# Dies schützt den Private Key zusätzlich
```

**Ergebnis:**
- `public_key.pem` → Für Raspberry Pi
- `private_key.pem` → **SICHER AUFBEWAHREN!**

### Schritt 2: Public Key auf Raspberry Pi kopieren

```bash
# Kopiere Public Key auf Raspberry Pi
scp public_key.pem pi@raspberrypi.local:/home/pi/Nippelboard_Funk/

# SSH zum Raspberry Pi
ssh pi@raspberrypi.local
cd /home/pi/Nippelboard_Funk

# Setze Pfad in config.yaml
nano config.yaml
```

In `config.yaml`:
```yaml
crypto:
  mode: 'asymmetric'
  public_key_path: './public_key.pem'
```

### Schritt 3: Private Key sicher aufbewahren

**WICHTIG:** Private Key **NIEMALS** auf Raspberry Pi speichern!

**Sichere Speicherorte:**
1. **USB-Stick** (verschlüsselt mit VeraCrypt/BitLocker)
2. **Verschlüsselter Cloud-Speicher** (NextCloud, Cryptomator)
3. **Externe Festplatte** (zu Hause, Tresor)
4. **Passwort-Manager** (1Password, KeePass)

**Backup:** Erstellen Sie mehrere Kopien an verschiedenen Orten!

---

## 🔓 Panik-Aufnahme entschlüsseln

Wenn Sie eine Panik-Aufnahme entschlüsseln möchten:

### Auf Ihrem PC (mit Private Key):

```bash
# Kopiere verschlüsselte Datei vom Raspberry Pi
scp pi@raspberrypi.local:/home/pi/Nippelboard_Funk/data/recordings/panic/panic_*.enc .

# Entschlüssele mit Private Key
python -m src.crypto.asymmetric decrypt \
    panic_20250112_143022.mp3.enc \
    panic_20250112_143022.mp3 \
    /pfad/zu/private_key.pem

# Passwort für Private Key eingeben
# → Fertig! Entschlüsselte Datei: panic_20250112_143022.mp3
```

---

## 🛡️ Zusätzliche Sicherheitsmaßnahmen

### 1. Private Key mit Passwort schützen

```bash
# Bei Generierung: --password verwenden
python -m src.crypto.asymmetric generate --password
```

**Vorteil:** Selbst wenn Private Key gestohlen wird, ist er ohne Passwort nutzlos.

### 2. Raspberry Pi verschlüsseln

Verschlüsseln Sie die gesamte SD-Karte:

```bash
# LUKS-Verschlüsselung für Raspberry Pi
# Bei Boot: Passwort-Eingabe erforderlich
```

**Vorteil:** Ohne Boot-Passwort ist gesamtes System unlesbar.

### 3. Auto-Delete bei Manipulation

Erweiterte Lösung: Löschen Sie Daten automatisch bei Manipulation:

```python
# Erkennung von Manipulation (z.B. falsches SSH-Login)
# → Automatisches Löschen von config.yaml
# → Public Key bleibt (Verschlüsselung weiterhin möglich)
```

### 4. Dead Man's Switch

```python
# Periodische "Lebenszeichen"-Eingabe erforderlich
# Ausbleiben → Automatisches Löschen kritischer Daten
```

---

## 📋 Checkliste vor Einsatz

- [ ] Schlüsselpaar generiert (`asymmetric generate --password`)
- [ ] Public Key auf Raspberry Pi kopiert
- [ ] Private Key **NICHT** auf Raspberry Pi
- [ ] Private Key an **mind. 2 sicheren Orten** gespeichert
- [ ] Private Key mit **starkem Passwort** geschützt
- [ ] `config.yaml`: `mode: 'asymmetric'` gesetzt
- [ ] Test: Panik-Aufnahme erstellen und entschlüsseln
- [ ] Private Key Passwort **sicher notiert** (nicht digital!)

---

## ⚖️ Rechtliche Hinweise

### Deutschland:

**Auskunftsverweigerungsrecht:**
- Sie haben das Recht, Passwörter/Keys zu verweigern
- Nemo-tenetur-Prinzip (Selbstbelastungsverbot)

**Aber:**
- Verschlüsselung selbst ist legal
- Verweigerung kann zu Nachteilen führen (z.B. U-Haft)
- Richterliche Anordnung zur Herausgabe möglich (umstritten)

**Bei Durchsuchung:**
- Gerät kann beschlagnahmt werden
- Verschlüsselte Daten können kopiert werden
- Ohne Private Key: Entschlüsselung praktisch unmöglich

### Wichtig:

- **Dokumentieren Sie** die Notwendigkeit der Verschlüsselung
- **Legitime Zwecke:** Schutz vertraulicher Gespräche, Persönlichkeitsrechte
- **Konsultieren Sie** einen Anwalt bei rechtlichen Fragen

---

## 🔬 Technische Details

### Verschlüsselungsverfahren:

1. **Datei-Verschlüsselung:** AES-256-GCM
   - Symmetrisch, sehr schnell
   - Authentifizierte Verschlüsselung (Manipulationsschutz)

2. **Key-Verschlüsselung:** RSA-4096
   - Asymmetrisch, nur Private Key kann entschlüsseln
   - OAEP-Padding (Optimal Asymmetric Encryption Padding)

3. **Hybrid-Ansatz:**
   - Datei wird mit zufälligem AES-Key verschlüsselt (schnell)
   - AES-Key wird mit RSA verschlüsselt (sicher)
   - Ergebnis: Schnell + Sicher

### Dateiformat:

```
[4 Bytes: Key-Länge]
[N Bytes: RSA-verschlüsselter AES-Key]
[12 Bytes: Nonce]
[M Bytes: AES-verschlüsselte Daten + Auth-Tag]
```

### Sicherheits-Analyse:

- **AES-256:** Unknackbar (2^256 Möglichkeiten)
- **RSA-4096:** Sicher bis mindestens 2030+
- **OAEP-Padding:** Verhindert Padding-Oracle-Angriffe
- **GCM-Modus:** Authentifizierung + Verschlüsselung in einem

**Fazit:** Ohne Private Key ist Entschlüsselung praktisch unmöglich, selbst mit Supercomputern.

---

## 🆘 Notfall-Szenarien

### Szenario 1: Private Key verloren

**Problem:** Sie können Ihre eigenen Aufnahmen nicht mehr entschlüsseln!

**Lösung:**
- Backup-Keys verwenden (falls erstellt)
- **Keine Wiederherstellung möglich** ohne Key!

**Prävention:**
- Erstellen Sie **mehrere Kopien** des Private Keys
- Lagern Sie diese an verschiedenen Orten

### Szenario 2: Raspberry Pi gestohlen

**Problem:** Gerät in fremden Händen

**Status:**
- ✓ Panik-Aufnahmen: Verschlüsselt (sicher)
- ✗ Normale Clips: Unverschlüsselt (lesbar)
- ✗ Nippel-Sounds: Unverschlüsselt (lesbar)

**Zusätzlicher Schutz:**
- Verschlüsseln Sie die gesamte SD-Karte (LUKS)
- Verwenden Sie starke SSH-Passwörter

### Szenario 3: Private Key kompromittiert

**Problem:** Jemand hat Ihren Private Key kopiert

**Sofortmaßnahmen:**
1. Neues Schlüsselpaar generieren
2. Neuen Public Key auf Raspberry Pi installieren
3. Alte Panik-Aufnahmen mit neuem Key neu verschlüsseln (falls möglich)

**Hinweis:** Bereits mit altem Key verschlüsselte Aufnahmen bleiben gefährdet!

---

## 📚 Weiterführende Informationen

### Literatur:
- [Applied Cryptography](https://www.schneier.com/books/applied-cryptography/) - Bruce Schneier
- [Handbook of Applied Cryptography](http://cacr.uwaterloo.ca/hac/)

### Tools:
- [VeraCrypt](https://www.veracrypt.fr/) - Container-Verschlüsselung
- [Cryptomator](https://cryptomator.org/) - Cloud-Verschlüsselung
- [KeePassXC](https://keepassxc.org/) - Passwort-Manager

### Rechtliche Beratung:
- CCC (Chaos Computer Club) - [ccc.de](https://www.ccc.de/)
- Digitale Gesellschaft e.V. - [digitalegesellschaft.de](https://digitalegesellschaft.de/)

---

## ✉️ Support

Bei Fragen zur Sicherheit:
- Öffnen Sie ein Issue auf GitHub
- Konsultieren Sie einen IT-Sicherheitsexperten
- Kontaktieren Sie einen Fachanwalt für IT-Recht

**Wichtig:** Diese Anleitung stellt keine Rechtsberatung dar!
