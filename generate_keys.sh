#!/bin/bash
# Interaktives Script zur Schlüssel-Generierung

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Nippelboard Funk - Sichere Verschlüsselung einrichten    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo

echo "Dieses Script generiert ein RSA-Schlüsselpaar für sichere"
echo "Panik-Aufnahmen, die nur Sie entschlüsseln können."
echo

# Warnung
echo "⚠️  WICHTIG:"
echo "   - Führen Sie dieses Script auf IHREM PC aus (NICHT auf Raspberry Pi!)"
echo "   - Der Private Key muss sicher aufbewahrt werden"
echo "   - Bei Verlust sind Panik-Aufnahmen NICHT mehr entschlüsselbar"
echo

read -p "Fortfahren? (j/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[JjYy]$ ]]; then
    echo "Abgebrochen."
    exit 0
fi

echo

# Ausgabeverzeichnis
read -p "Ausgabeverzeichnis (Standard: .): " OUTPUT_DIR
OUTPUT_DIR=${OUTPUT_DIR:-.}

if [ ! -d "$OUTPUT_DIR" ]; then
    echo "✗ Verzeichnis existiert nicht: $OUTPUT_DIR"
    exit 1
fi

echo

# Prüfe ob Keys bereits existieren
if [ -f "$OUTPUT_DIR/private_key.pem" ] || [ -f "$OUTPUT_DIR/public_key.pem" ]; then
    echo "⚠️  Warnung: Keys existieren bereits in $OUTPUT_DIR!"
    ls -l "$OUTPUT_DIR"/*.pem 2>/dev/null
    echo
    read -p "Überschreiben? (j/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[JjYy]$ ]]; then
        echo "Abgebrochen."
        exit 0
    fi
fi

# Generiere Keys
echo "🔐 Generiere RSA-4096 Schlüsselpaar..."
echo
python3 -m src.crypto.asymmetric generate --password "$OUTPUT_DIR"

if [ $? -ne 0 ]; then
    echo
    echo "✗ Fehler bei der Generierung!"
    exit 1
fi

echo
echo "════════════════════════════════════════════════════════════"
echo "✓ Schlüsselpaar erfolgreich generiert!"
echo "════════════════════════════════════════════════════════════"
echo

# Zeige Dateien
echo "📁 Generierte Dateien:"
ls -lh "$OUTPUT_DIR/public_key.pem" "$OUTPUT_DIR/private_key.pem"
echo

# Nächste Schritte
echo "═══════════════════════════════════════════════════════════════"
echo "NÄCHSTE SCHRITTE:"
echo "═══════════════════════════════════════════════════════════════"
echo

echo "1️⃣  Public Key auf Raspberry Pi kopieren:"
echo "   scp $OUTPUT_DIR/public_key.pem pi@raspberrypi.local:/home/pi/Nippelboard_Funk/"
echo

echo "2️⃣  Private Key SICHER aufbewahren:"
echo "   → USB-Stick (verschlüsselt)"
echo "   → Externe Festplatte"
echo "   → Verschlüsselter Cloud-Speicher"
echo "   → NIEMALS auf Raspberry Pi!"
echo

echo "3️⃣  Backup erstellen:"
echo "   cp $OUTPUT_DIR/private_key.pem /pfad/zum/backup/private_key_backup.pem"
echo

echo "4️⃣  Config auf Raspberry Pi anpassen:"
echo "   ssh pi@raspberrypi.local"
echo "   cd /home/pi/Nippelboard_Funk"
echo "   nano config.yaml"
echo "   # Setze: crypto.mode: 'asymmetric'"
echo

echo "5️⃣  Private Key vom aktuellen Rechner löschen (nach Backup!):"
echo "   shred -vfz -n 10 $OUTPUT_DIR/private_key.pem"
echo

# Passwort-Hinweis
echo "═══════════════════════════════════════════════════════════════"
echo "⚠️  WICHTIG:"
echo "═══════════════════════════════════════════════════════════════"
echo "Notieren Sie das Passwort für den Private Key an einem"
echo "sicheren Ort (z.B. Passwort-Manager, Tresor)."
echo "Ohne Passwort können Sie Ihre Aufnahmen NICHT entschlüsseln!"
echo

read -p "Passwort sicher notiert? (j/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[JjYy]$ ]]; then
    echo
    echo "⚠️  Bitte notieren Sie das Passwort, bevor Sie fortfahren!"
fi

echo
echo "Weitere Informationen: QUICKSTART_SICHERHEIT.md"
echo
