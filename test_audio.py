#!/usr/bin/env python3
"""
Test-Script für Audio-Module (ohne GUI)
Nützlich für Debugging und Testing auf Raspberry Pi
"""

import sys
import time
import logging
from pathlib import Path

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_audio_devices():
    """Teste Audio-Geräte"""
    print("\n" + "=" * 60)
    print("Test: Audio-Geräte")
    print("=" * 60)

    try:
        import sounddevice as sd

        print("\n📡 Verfügbare Audio-Geräte:")
        devices = sd.query_devices()

        for idx, device in enumerate(devices):
            input_ch = device['max_input_channels']
            output_ch = device['max_output_channels']
            print(f"\n[{idx}] {device['name']}")
            print(f"    Input: {input_ch} Kanäle, Output: {output_ch} Kanäle")
            print(f"    Sample Rate: {device['default_samplerate']} Hz")

        # Zeige Standard-Geräte
        default_input = sd.query_devices(kind='input')
        default_output = sd.query_devices(kind='output')

        print(f"\n✓ Standard Input: {default_input['name']}")
        print(f"✓ Standard Output: {default_output['name']}")

        return True

    except Exception as e:
        print(f"✗ Fehler: {e}")
        return False


def test_config():
    """Teste Konfiguration"""
    print("\n" + "=" * 60)
    print("Test: Konfiguration")
    print("=" * 60)

    try:
        from src.utils.config import config

        print(f"\nSample Rate: {config.get('audio.sample_rate')}")
        print(f"Ringbuffer: {config.get('audio.ringbuffer_seconds')}s")
        print(f"GPIO Clip-Pin: {config.get('gpio.clip_button_pin')}")
        print(f"GPIO Panik-Pin: {config.get('gpio.panic_button_pin')}")

        # Warnung bei Default-Passwort
        password = config.get('crypto.encryption_password')
        if password in ['CHANGE_ME_INSECURE', 'BITTE_ÄNDERN_SicheresPasswort123!']:
            print("\n⚠️  WARNUNG: Standard-Passwort verwendet!")
            print("   Bitte ändern Sie 'crypto.encryption_password' in config.yaml!")
        else:
            print("\n✓ Eigenes Passwort konfiguriert")

        return True

    except Exception as e:
        print(f"✗ Fehler: {e}")
        return False


def test_database():
    """Teste Datenbank"""
    print("\n" + "=" * 60)
    print("Test: Datenbank")
    print("=" * 60)

    try:
        from src.utils.database import init_database, NippelSound

        init_database()
        print("✓ Datenbank initialisiert")

        # Zähle Sounds
        sound_count = NippelSound.select().count()
        print(f"✓ {sound_count} Sounds in Datenbank")

        return True

    except Exception as e:
        print(f"✗ Fehler: {e}")
        return False


def test_recorder(duration=5):
    """Teste Recorder (kurze Aufnahme)"""
    print("\n" + "=" * 60)
    print(f"Test: Recorder ({duration}s Aufnahme)")
    print("=" * 60)

    try:
        from src.audio.recorder import AudioRecorder

        recorder = AudioRecorder()
        print("✓ Recorder erstellt")

        print(f"\nStarte Aufnahme für {duration}s...")
        recorder.start()
        print("✓ Aufnahme gestartet")

        # Warte
        for i in range(duration):
            time.sleep(1)
            status = recorder.get_buffer_status()
            print(f"  [{i+1}s] Buffer: {status['buffer_fill_percent']:.1f}%")

        print("\nSpeichere Test-Clip...")
        clip_path = recorder.save_clip("test_clip.mp3")

        if clip_path:
            print(f"✓ Clip gespeichert: {clip_path}")
        else:
            print("✗ Clip-Speicherung fehlgeschlagen")

        recorder.stop()
        print("✓ Aufnahme gestoppt")

        return clip_path is not None

    except Exception as e:
        print(f"✗ Fehler: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_player():
    """Teste Player"""
    print("\n" + "=" * 60)
    print("Test: Player")
    print("=" * 60)

    try:
        from src.audio.player import AudioPlayer

        player = AudioPlayer()
        print("✓ Player erstellt")

        # Suche Test-Sound
        test_sound = Path("data/recordings/clips/test_clip.mp3")

        if test_sound.exists():
            print(f"\nSpiele Test-Sound: {test_sound.name}")
            player.play(str(test_sound), volume=0.5, blocking=True)
            print("✓ Wiedergabe abgeschlossen")
            return True
        else:
            print("⚠️  Kein Test-Sound gefunden (führe erst test_recorder aus)")
            return False

    except Exception as e:
        print(f"✗ Fehler: {e}")
        return False


def test_gpio():
    """Teste GPIO (Mock-Modus wenn nicht auf RPi)"""
    print("\n" + "=" * 60)
    print("Test: GPIO")
    print("=" * 60)

    try:
        from src.gpio.buttons import create_button_handler

        handler = create_button_handler()
        print(f"✓ ButtonHandler erstellt (Enabled: {handler.enabled})")

        # Teste Mock-Funktionen falls verfügbar
        if hasattr(handler, 'simulate_clip_button'):
            print("\n⚠️  Mock-Modus (keine echten GPIO-Pins)")
            print("   Verwende Mock-Funktionen zum Testen")

            handler.on_clip_button = lambda: print("  → Clip-Button-Callback aufgerufen")
            handler.on_panic_button = lambda active: print(f"  → Panik-Button-Callback: {active}")

            handler.simulate_clip_button()
            handler.simulate_panic_button()
            handler.simulate_panic_button()

        handler.cleanup()
        print("✓ GPIO-Test abgeschlossen")

        return True

    except Exception as e:
        print(f"✗ Fehler: {e}")
        return False


def test_encryption():
    """Teste Verschlüsselung"""
    print("\n" + "=" * 60)
    print("Test: Verschlüsselung")
    print("=" * 60)

    try:
        from src.crypto.encryption import CryptoHandler
        import tempfile

        handler = CryptoHandler()
        print("✓ CryptoHandler erstellt")

        # Erstelle Test-Datei
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Dies ist ein Test für die Verschlüsselung!\n")
            f.write("Geheime Informationen...")
            test_file = f.name

        print(f"\n✓ Test-Datei erstellt: {test_file}")

        # Verschlüssele
        encrypted_file = handler.encrypt_file(test_file, test_file + '.enc')
        print(f"✓ Datei verschlüsselt: {encrypted_file}")

        # Entschlüssele
        decrypted_file = test_file + '.dec'
        success = handler.decrypt_file(encrypted_file, decrypted_file)

        if success:
            print(f"✓ Datei entschlüsselt: {decrypted_file}")

            # Vergleiche
            with open(test_file, 'r') as f:
                original = f.read()
            with open(decrypted_file, 'r') as f:
                decrypted = f.read()

            if original == decrypted:
                print("✓ Original == Entschlüsselt")
            else:
                print("✗ Dateien unterscheiden sich!")
                return False
        else:
            print("✗ Entschlüsselung fehlgeschlagen")
            return False

        # Cleanup
        Path(test_file).unlink(missing_ok=True)
        Path(encrypted_file).unlink(missing_ok=True)
        Path(decrypted_file).unlink(missing_ok=True)

        return True

    except Exception as e:
        print(f"✗ Fehler: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Hauptprogramm"""
    print("\n" + "=" * 60)
    print("Nippelboard Funk - Test Suite")
    print("=" * 60)

    tests = [
        ("Audio-Geräte", test_audio_devices),
        ("Konfiguration", test_config),
        ("Datenbank", test_database),
        ("Verschlüsselung", test_encryption),
        ("GPIO", test_gpio),
    ]

    # Optionale Tests
    if "--full" in sys.argv or "-f" in sys.argv:
        tests.append(("Recorder", lambda: test_recorder(5)))
        tests.append(("Player", test_player))

    results = {}

    for name, test_func in tests:
        try:
            results[name] = test_func()
        except KeyboardInterrupt:
            print("\n\n⚠️  Test abgebrochen")
            break
        except Exception as e:
            print(f"\n✗ Unerwarteter Fehler in {name}: {e}")
            results[name] = False

        time.sleep(0.5)

    # Zusammenfassung
    print("\n" + "=" * 60)
    print("Zusammenfassung")
    print("=" * 60)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:10} {name}")

    print(f"\n{passed}/{total} Tests erfolgreich")

    if passed == total:
        print("\n🎉 Alle Tests bestanden!")
        return 0
    else:
        print("\n⚠️  Einige Tests fehlgeschlagen")
        return 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nAbgebrochen")
        sys.exit(130)
