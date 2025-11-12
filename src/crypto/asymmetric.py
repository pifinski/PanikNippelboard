"""
Asymmetrische Verschlüsselung für Panik-Aufnahmen
Verwendet RSA + AES Hybrid-Verschlüsselung

Public Key auf Gerät -> Verschlüsseln
Private Key extern -> Entschlüsseln (nur Sie!)
"""

import logging
import os
from pathlib import Path
from typing import Optional, Tuple

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class AsymmetricCrypto:
    """
    Hybrid-Verschlüsselung: RSA + AES

    - Datei wird mit AES-256 verschlüsselt (schnell)
    - AES-Key wird mit RSA verschlüsselt (sicher)
    - Nur Private Key kann entschlüsseln
    """

    def __init__(self, public_key_path: str = None, private_key_path: str = None):
        """
        Args:
            public_key_path: Pfad zum Public Key (PEM)
            private_key_path: Pfad zum Private Key (PEM, optional)
        """
        self.public_key = None
        self.private_key = None

        # Lade Public Key (für Verschlüsselung)
        if public_key_path and Path(public_key_path).exists():
            self.load_public_key(public_key_path)

        # Lade Private Key (für Entschlüsselung)
        if private_key_path and Path(private_key_path).exists():
            self.load_private_key(private_key_path)

    @staticmethod
    def generate_keypair(output_dir: str = '.',
                         key_size: int = 4096,
                         password: str = None) -> Tuple[str, str]:
        """
        Generiert RSA-Schlüsselpaar

        Args:
            output_dir: Ausgabeverzeichnis
            key_size: RSA-Schlüssellänge (2048, 4096)
            password: Optional: Passwort für Private Key

        Returns:
            (public_key_path, private_key_path)
        """
        logger.info(f"Generiere RSA-{key_size} Schlüsselpaar...")

        # Generiere Private Key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )

        # Generiere Public Key
        public_key = private_key.public_key()

        # Speichere Private Key (optional mit Passwort)
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(password.encode())
            if password else serialization.NoEncryption()
        )

        private_key_path = Path(output_dir) / 'private_key.pem'
        with open(private_key_path, 'wb') as f:
            f.write(private_pem)

        # Schütze Private Key (nur Owner darf lesen)
        if os.name != 'nt':  # Unix/Linux
            os.chmod(private_key_path, 0o600)

        logger.warning(f"⚠️  PRIVATE KEY gespeichert: {private_key_path}")
        logger.warning("   BEWAHREN SIE DIESEN SICHER AUF (USB-Stick, verschlüsselter Speicher)!")
        logger.warning("   NICHT AUF DEM RASPBERRY PI LASSEN!")

        # Speichere Public Key
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        public_key_path = Path(output_dir) / 'public_key.pem'
        with open(public_key_path, 'wb') as f:
            f.write(public_pem)

        logger.info(f"✓ PUBLIC KEY gespeichert: {public_key_path}")
        logger.info("  (Dieser bleibt auf dem Raspberry Pi)")

        return str(public_key_path), str(private_key_path)

    def load_public_key(self, key_path: str):
        """Lädt Public Key"""
        try:
            with open(key_path, 'rb') as f:
                self.public_key = serialization.load_pem_public_key(
                    f.read(),
                    backend=default_backend()
                )
            logger.info(f"Public Key geladen: {key_path}")
        except Exception as e:
            logger.error(f"Fehler beim Laden des Public Keys: {e}")
            raise

    def load_private_key(self, key_path: str, password: str = None):
        """Lädt Private Key"""
        try:
            with open(key_path, 'rb') as f:
                self.private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=password.encode() if password else None,
                    backend=default_backend()
                )
            logger.info(f"Private Key geladen: {key_path}")
        except Exception as e:
            logger.error(f"Fehler beim Laden des Private Keys: {e}")
            raise

    def encrypt_file(self, input_path: str, output_path: str = None) -> str:
        """
        Verschlüsselt Datei mit Public Key

        Dateiformat:
        [Encrypted AES Key (RSA)][Nonce 12 bytes][Encrypted Data + Tag]

        Args:
            input_path: Eingabe-Datei
            output_path: Ausgabe-Datei

        Returns:
            Pfad zur verschlüsselten Datei
        """
        if not self.public_key:
            raise ValueError("Public Key nicht geladen! Verwende load_public_key()")

        if output_path is None:
            output_path = f"{input_path}.enc"

        try:
            # Lese Datei
            with open(input_path, 'rb') as f:
                plaintext = f.read()

            # Generiere zufälligen AES-Key (256 bit)
            aes_key = AESGCM.generate_key(bit_length=256)
            nonce = os.urandom(12)

            # Verschlüssele Datei mit AES-GCM
            aesgcm = AESGCM(aes_key)
            ciphertext = aesgcm.encrypt(nonce, plaintext, None)

            # Verschlüssele AES-Key mit RSA
            encrypted_aes_key = self.public_key.encrypt(
                aes_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )

            # Schreibe verschlüsselte Datei
            # Format: [RSA-verschlüsselter AES-Key][Nonce][AES-verschlüsselte Daten]
            with open(output_path, 'wb') as f:
                # Schreibe Länge des verschlüsselten Keys (4 bytes)
                key_length = len(encrypted_aes_key)
                f.write(key_length.to_bytes(4, byteorder='big'))

                # Schreibe verschlüsselten AES-Key
                f.write(encrypted_aes_key)

                # Schreibe Nonce
                f.write(nonce)

                # Schreibe verschlüsselte Daten
                f.write(ciphertext)

            file_size = Path(output_path).stat().st_size
            logger.info(f"Datei verschlüsselt: {output_path} ({file_size / 1024:.1f} KB)")

            return output_path

        except Exception as e:
            logger.error(f"Fehler bei Verschlüsselung: {e}")
            raise

    def decrypt_file(self, input_path: str, output_path: str) -> bool:
        """
        Entschlüsselt Datei mit Private Key

        Args:
            input_path: Verschlüsselte Datei
            output_path: Ausgabe-Datei

        Returns:
            True bei Erfolg
        """
        if not self.private_key:
            raise ValueError("Private Key nicht geladen! Verwende load_private_key()")

        try:
            # Lese verschlüsselte Datei
            with open(input_path, 'rb') as f:
                # Lese Länge des verschlüsselten Keys
                key_length = int.from_bytes(f.read(4), byteorder='big')

                # Lese verschlüsselten AES-Key
                encrypted_aes_key = f.read(key_length)

                # Lese Nonce
                nonce = f.read(12)

                # Lese verschlüsselte Daten
                ciphertext = f.read()

            # Entschlüssele AES-Key mit RSA
            aes_key = self.private_key.decrypt(
                encrypted_aes_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )

            # Entschlüssele Datei mit AES
            aesgcm = AESGCM(aes_key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)

            # Schreibe entschlüsselte Datei
            with open(output_path, 'wb') as f:
                f.write(plaintext)

            logger.info(f"Datei entschlüsselt: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Fehler bei Entschlüsselung: {e}")
            if "decrypt" in str(e).lower():
                logger.error("Falscher Private Key oder Datei manipuliert!")
            return False


# CLI-Tool
if __name__ == '__main__':
    import sys
    import getpass

    if len(sys.argv) < 2:
        print("""
Nippelboard Funk - Asymmetrische Verschlüsselung

Verwendung:
  1. Schlüsselpaar generieren:
     python -m src.crypto.asymmetric generate [--password]

  2. Datei entschlüsseln:
     python -m src.crypto.asymmetric decrypt <encrypted_file> <output_file> <private_key.pem>

WICHTIG:
  - Public Key bleibt auf Raspberry Pi (verschlüsselt Panik-Aufnahmen)
  - Private Key extern aufbewahren (USB-Stick, verschlüsselter PC)
  - Bei Beschlagnahmung: Nur Sie können mit Private Key entschlüsseln!
""")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'generate':
        # Generiere Schlüsselpaar
        use_password = '--password' in sys.argv
        password = None

        if use_password:
            password = getpass.getpass("Passwort für Private Key (optional, empfohlen): ")
            if password:
                password_confirm = getpass.getpass("Passwort bestätigen: ")
                if password != password_confirm:
                    print("✗ Passwörter stimmen nicht überein!")
                    sys.exit(1)

        output_dir = sys.argv[2] if len(sys.argv) > 2 else '.'

        public_path, private_path = AsymmetricCrypto.generate_keypair(
            output_dir=output_dir,
            key_size=4096,
            password=password
        )

        print("\n" + "=" * 60)
        print("✓ Schlüsselpaar generiert!")
        print("=" * 60)
        print(f"\n📁 Public Key:  {public_path}")
        print(f"   → Kopieren Sie diesen auf den Raspberry Pi")
        print(f"   → Pfad in config.yaml eintragen")
        print(f"\n🔐 Private Key: {private_path}")
        print(f"   → BEWAHREN SIE DIESEN SICHER AUF!")
        print(f"   → USB-Stick, verschlüsselter Speicher, Tresor")
        print(f"   → NICHT auf Raspberry Pi lassen!")
        print(f"   → Bei Verlust: Panik-Aufnahmen nicht mehr entschlüsselbar!")

    elif command == 'decrypt':
        if len(sys.argv) < 5:
            print("Usage: decrypt <encrypted_file> <output_file> <private_key.pem>")
            sys.exit(1)

        encrypted_file = sys.argv[2]
        output_file = sys.argv[3]
        private_key_path = sys.argv[4]

        # Frage Passwort falls nötig
        password = getpass.getpass("Passwort für Private Key (Enter falls keins): ")
        if not password:
            password = None

        # Entschlüssele
        crypto = AsymmetricCrypto()
        crypto.load_private_key(private_key_path, password)

        success = crypto.decrypt_file(encrypted_file, output_file)

        if success:
            print(f"\n✓ Datei erfolgreich entschlüsselt: {output_file}")
        else:
            print(f"\n✗ Entschlüsselung fehlgeschlagen!")
            sys.exit(1)

    else:
        print(f"Unbekannter Befehl: {command}")
        print("Verwende: generate oder decrypt")
        sys.exit(1)
