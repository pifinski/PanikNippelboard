"""
Verschlüsselungsmodul für Panik-Aufnahmen
Verwendet AES-256-GCM für sichere Verschlüsselung
"""

import logging
import os
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend

from ..utils.config import config

logger = logging.getLogger(__name__)


class CryptoHandler:
    """
    Handler für Dateiverschlüsselung

    Features:
    - AES-256-GCM Verschlüsselung
    - PBKDF2 Key-Derivation
    - Authentifizierte Verschlüsselung (verhindert Manipulation)
    """

    def __init__(self):
        # Konfiguration
        self.password = config.get('crypto.encryption_password', 'INSECURE_DEFAULT')
        self.iterations = config.get('crypto.pbkdf2_iterations', 100000)
        self.salt_length = config.get('crypto.salt_length', 32)

        if self.password == 'INSECURE_DEFAULT' or self.password == 'BITTE_ÄNDERN_SicheresPasswort123!':
            logger.warning(
                "WARNUNG: Standard-Passwort verwendet! "
                "Bitte ändern Sie 'crypto.encryption_password' in config.yaml!"
            )

        logger.info("CryptoHandler initialisiert")

    def derive_key(self, salt: bytes) -> bytes:
        """
        Leitet Schlüssel aus Passwort ab (PBKDF2)

        Args:
            salt: Salt für Key-Derivation

        Returns:
            32-Byte AES-256 Schlüssel
        """
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bit
            salt=salt,
            iterations=self.iterations,
            backend=default_backend()
        )

        key = kdf.derive(self.password.encode('utf-8'))
        return key

    def encrypt_file(self, input_path: str, output_path: str = None) -> str:
        """
        Verschlüsselt Datei mit AES-256-GCM

        Dateiformat:
        [Salt 32 bytes][Nonce 12 bytes][Encrypted Data + Tag 16 bytes]

        Args:
            input_path: Eingabe-Datei
            output_path: Ausgabe-Datei (None = input_path + '.enc')

        Returns:
            Pfad zur verschlüsselten Datei
        """
        if output_path is None:
            output_path = f"{input_path}.enc"

        try:
            # Lese Eingabe-Datei
            with open(input_path, 'rb') as f:
                plaintext = f.read()

            # Generiere Salt und Nonce
            salt = os.urandom(self.salt_length)
            nonce = os.urandom(12)  # 96 bit für GCM

            # Leite Schlüssel ab
            key = self.derive_key(salt)

            # Verschlüssele mit AES-GCM
            aesgcm = AESGCM(key)
            ciphertext = aesgcm.encrypt(nonce, plaintext, None)

            # Schreibe verschlüsselte Datei
            with open(output_path, 'wb') as f:
                f.write(salt)
                f.write(nonce)
                f.write(ciphertext)  # Enthält bereits den Auth-Tag

            file_size = Path(output_path).stat().st_size
            logger.info(f"Datei verschlüsselt: {output_path} ({file_size / 1024:.1f} KB)")

            return output_path

        except Exception as e:
            logger.error(f"Fehler bei Verschlüsselung von {input_path}: {e}")
            raise

    def decrypt_file(self, input_path: str, output_path: str,
                     password: str = None) -> bool:
        """
        Entschlüsselt Datei

        Args:
            input_path: Verschlüsselte Datei
            output_path: Ausgabe-Datei
            password: Optional anderes Passwort verwenden

        Returns:
            True bei Erfolg
        """
        try:
            # Lese verschlüsselte Datei
            with open(input_path, 'rb') as f:
                salt = f.read(self.salt_length)
                nonce = f.read(12)
                ciphertext = f.read()  # Rest der Datei

            # Verwende gegebenes oder Standard-Passwort
            if password is not None:
                old_password = self.password
                self.password = password

            # Leite Schlüssel ab
            key = self.derive_key(salt)

            # Entschlüssele
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)

            # Schreibe entschlüsselte Datei
            with open(output_path, 'wb') as f:
                f.write(plaintext)

            # Stelle altes Passwort wieder her
            if password is not None:
                self.password = old_password

            logger.info(f"Datei entschlüsselt: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Fehler bei Entschlüsselung von {input_path}: {e}")
            if "InvalidTag" in str(type(e).__name__):
                logger.error("Falsches Passwort oder Datei manipuliert!")
            return False

    def verify_password(self, encrypted_file: str, password: str) -> bool:
        """
        Verifiziert Passwort gegen verschlüsselte Datei

        Args:
            encrypted_file: Verschlüsselte Datei
            password: Zu testendes Passwort

        Returns:
            True wenn Passwort korrekt
        """
        try:
            # Lese nur Header
            with open(encrypted_file, 'rb') as f:
                salt = f.read(self.salt_length)
                nonce = f.read(12)
                ciphertext = f.read(1024)  # Nur Anfang lesen

            # Teste Entschlüsselung
            old_password = self.password
            self.password = password

            key = self.derive_key(salt)
            aesgcm = AESGCM(key)

            try:
                # Versuche zu entschlüsseln
                aesgcm.decrypt(nonce, ciphertext[:100], None)
                self.password = old_password
                return True
            except:
                self.password = old_password
                return False

        except Exception as e:
            logger.error(f"Fehler bei Passwort-Verifikation: {e}")
            return False


# Singleton-Instanz
_crypto_handler = None


def get_crypto_handler() -> CryptoHandler:
    """Gibt Singleton-Instanz zurück"""
    global _crypto_handler
    if _crypto_handler is None:
        _crypto_handler = CryptoHandler()
    return _crypto_handler


# Convenience-Funktionen
def encrypt_file(input_path: str, output_path: str = None) -> str:
    """Verschlüsselt Datei"""
    return get_crypto_handler().encrypt_file(input_path, output_path)


def decrypt_file(input_path: str, output_path: str, password: str = None) -> bool:
    """Entschlüsselt Datei"""
    return get_crypto_handler().decrypt_file(input_path, output_path, password)


def verify_password(encrypted_file: str, password: str) -> bool:
    """Verifiziert Passwort"""
    return get_crypto_handler().verify_password(encrypted_file, password)


# CLI-Tool zum Entschlüsseln
if __name__ == '__main__':
    import sys
    import getpass

    if len(sys.argv) < 3:
        print("Usage: python -m src.crypto.encryption <encrypted_file> <output_file>")
        sys.exit(1)

    encrypted_file = sys.argv[1]
    output_file = sys.argv[2]

    # Frage Passwort ab
    password = getpass.getpass("Passwort: ")

    # Entschlüssele
    handler = CryptoHandler()
    success = handler.decrypt_file(encrypted_file, output_file, password)

    if success:
        print(f"✓ Datei erfolgreich entschlüsselt: {output_file}")
    else:
        print("✗ Entschlüsselung fehlgeschlagen!")
        sys.exit(1)
