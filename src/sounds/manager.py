"""
Sound-Manager für Nippelboard
Verwaltet Sounds, Downloads, Positionierung
"""

import logging
import shutil
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

import requests

from ..utils.config import config
from ..utils.database import (
    NippelSound, add_sound, get_all_sounds_sorted,
    get_sound_by_name, update_sound_position, db_transaction
)
from ..audio.processor import AudioProcessor
from .downloader import UniversalDownloader, check_yt_dlp_installed

logger = logging.getLogger(__name__)


class SoundManager:
    """
    Manager für Nippelboard-Sounds

    Features:
    - Sound hinzufügen (lokal, Download)
    - Sound löschen
    - Position ändern (Drag & Drop)
    - Sound bearbeiten (schneiden, normalisieren)
    """

    def __init__(self):
        self.sounds_dir = Path(config.get('storage.sounds_dir', './data/sounds'))
        self.sounds_dir.mkdir(parents=True, exist_ok=True)

        # Download-Einstellungen
        self.allowed_domains = config.get('downloads.allowed_domains', [])
        self.download_timeout = config.get('downloads.timeout', 30)
        self.max_file_size_mb = config.get('downloads.max_file_size_mb', 10)

        self.processor = AudioProcessor()

        # Universal Downloader (YouTube, SoundCloud, etc.)
        self.universal_downloader = UniversalDownloader()
        self.yt_dlp_available = check_yt_dlp_installed()
        if not self.yt_dlp_available:
            logger.warning("yt-dlp nicht installiert - YouTube/SoundCloud Downloads nicht verfügbar")

        logger.info(f"SoundManager initialisiert (Dir={self.sounds_dir})")

    def add_sound_from_file(self, name: str, source_path: str,
                           icon_path: str = None, position: int = None) -> Optional[NippelSound]:
        """
        Fügt Sound aus lokaler Datei hinzu

        Args:
            name: Anzeigename
            source_path: Pfad zur Audio-Datei
            icon_path: Optional Icon-Pfad
            position: Optional Position im Grid

        Returns:
            NippelSound oder None bei Fehler
        """
        try:
            source = Path(source_path)

            if not source.exists():
                logger.error(f"Datei nicht gefunden: {source_path}")
                return None

            # Prüfe ob Name bereits existiert
            if get_sound_by_name(name):
                logger.error(f"Sound mit Name '{name}' existiert bereits")
                return None

            # Kopiere zu sounds_dir
            dest_file = self.sounds_dir / f"{name}{source.suffix}"
            shutil.copy2(source, dest_file)

            # Hole Audio-Info
            info = self.processor.get_audio_info(str(dest_file))
            duration = info['duration_seconds'] if info else None

            # Icon kopieren falls vorhanden
            final_icon_path = None
            if icon_path and Path(icon_path).exists():
                icon_dest = self.sounds_dir / f"{name}_icon{Path(icon_path).suffix}"
                shutil.copy2(icon_path, icon_dest)
                final_icon_path = str(icon_dest)

            # Füge zu DB hinzu
            sound = add_sound(
                name=name,
                file_path=str(dest_file),
                icon_path=final_icon_path,
                position=position
            )

            # Setze Duration
            if duration:
                sound.duration = duration
                sound.save()

            logger.info(f"Sound hinzugefügt: {name} ({duration:.1f}s)")
            return sound

        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen von Sound: {e}")
            return None

    def add_sound_from_url(self, name: str, url: str,
                          icon_url: str = None, position: int = None,
                          auto_trim: bool = False, max_duration: int = 300) -> Optional[NippelSound]:
        """
        Lädt Sound aus dem Internet herunter

        Unterstützt:
        - Direkte Audio-URLs (.mp3, .ogg, etc.)
        - YouTube, SoundCloud, TikTok, etc. (via yt-dlp)

        Args:
            name: Anzeigename
            url: Download-URL
            icon_url: Optional Icon-URL
            position: Optional Position
            auto_trim: Automatisch auf max_duration kürzen
            max_duration: Maximale Dauer in Sekunden (default: 300 = 5 Min)

        Returns:
            NippelSound oder None bei Fehler
        """
        try:
            # Prüfe ob es eine YouTube/SoundCloud/etc. URL ist
            if self.yt_dlp_available and self.universal_downloader.is_supported_url(url):
                logger.info(f"Erkannt als Universal-URL (YouTube/SoundCloud/etc.): {url}")
                return self._download_universal(name, url, position, max_duration)

            # Ansonsten: Direkter Download
            return self._download_direct(name, url, icon_url, position)

        except Exception as e:
            logger.error(f"Fehler bei Sound-Download: {e}")
            return None

    def _download_universal(self, name: str, url: str, position: int = None,
                           max_duration: int = 300) -> Optional[NippelSound]:
        """
        Download via yt-dlp (YouTube, SoundCloud, etc.)

        Args:
            name: Anzeigename
            url: Video/Audio URL
            position: Optional Position
            max_duration: Max. Dauer in Sekunden

        Returns:
            NippelSound oder None
        """
        try:
            # Hole Metadaten
            logger.info("Hole Video-Informationen...")
            info = self.universal_downloader.get_info(url)

            if not info:
                logger.error("Konnte Video-Informationen nicht abrufen")
                return None

            # Nutze Video-Titel falls kein Name angegeben
            if not name or name.strip() == "":
                name = info['title']
                # Bereinige Name (keine Sonderzeichen)
                name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_'))[:50]

            logger.info(f"Titel: {info['title']}, Dauer: {info.get('duration', 0)}s")

            # Prüfe ob Name bereits existiert
            if get_sound_by_name(name):
                logger.error(f"Sound mit Name '{name}' existiert bereits")
                return None

            # Download
            output_path = self.sounds_dir / name
            logger.info(f"Starte Download von: {url}")

            success = self.universal_downloader.download(
                url=url,
                output_path=output_path,
                format='mp3',
                quality='128k',
                max_duration=max_duration
            )

            if not success:
                logger.error("Download fehlgeschlagen")
                return None

            # Finde heruntergeladene Datei
            downloaded_file = self.sounds_dir / f"{name}.mp3"

            if not downloaded_file.exists():
                logger.error(f"Datei nicht gefunden: {downloaded_file}")
                return None

            # Download Thumbnail als Icon
            icon_path = None
            if info.get('thumbnail'):
                icon_file = self.sounds_dir / f"{name}_icon.jpg"
                if self.universal_downloader.download_thumbnail(url, icon_file):
                    icon_path = str(icon_file)

            # Hole Audio-Info
            audio_info = self.processor.get_audio_info(str(downloaded_file))
            duration = audio_info['duration_seconds'] if audio_info else None

            # Füge zu DB hinzu
            sound = add_sound(
                name=name,
                file_path=str(downloaded_file),
                icon_path=icon_path,
                position=position
            )

            # Setze Duration
            if duration:
                sound.duration = duration
                sound.save()

            logger.info(f"Sound erfolgreich hinzugefügt: {name} ({duration:.1f}s)")
            return sound

        except Exception as e:
            logger.exception(f"Fehler beim Universal-Download: {e}")
            return None

    def _download_direct(self, name: str, url: str, icon_url: str = None,
                        position: int = None) -> Optional[NippelSound]:
        """
        Direkter Download von Audio-URL

        Args:
            name: Anzeigename
            url: Direkte Audio-URL
            icon_url: Optional Icon-URL
            position: Optional Position

        Returns:
            NippelSound oder None
        """
        try:
            # Prüfe Domain
            if self.allowed_domains:
                domain = urlparse(url).netloc
                if not any(allowed in domain for allowed in self.allowed_domains):
                    logger.error(f"Domain nicht erlaubt: {domain}")
                    return None

            # Download Audio
            logger.info(f"Lade Sound herunter (direkt): {url}")
            response = requests.get(
                url,
                timeout=self.download_timeout,
                stream=True
            )
            response.raise_for_status()

            # Prüfe Dateigröße
            content_length = int(response.headers.get('content-length', 0))
            max_size_bytes = self.max_file_size_mb * 1024 * 1024

            if content_length > max_size_bytes:
                logger.error(f"Datei zu groß: {content_length / 1e6:.1f} MB")
                return None

            # Bestimme Dateiendung
            content_type = response.headers.get('content-type', '')
            if 'audio/mpeg' in content_type or url.endswith('.mp3'):
                ext = '.mp3'
            elif 'audio/ogg' in content_type or url.endswith('.ogg'):
                ext = '.ogg'
            elif 'audio/wav' in content_type or url.endswith('.wav'):
                ext = '.wav'
            else:
                ext = '.mp3'  # Default

            # Speichere
            temp_file = self.sounds_dir / f"{name}{ext}"
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"Download abgeschlossen: {temp_file}")

            # Icon herunterladen falls angegeben
            icon_path = None
            if icon_url:
                icon_path = self._download_icon(name, icon_url)

            # Füge Sound hinzu
            return self.add_sound_from_file(
                name=name,
                source_path=str(temp_file),
                icon_path=icon_path,
                position=position
            )

        except requests.RequestException as e:
            logger.error(f"Fehler beim Download von {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Fehler bei direktem Download: {e}")
            return None

    def _download_icon(self, name: str, icon_url: str) -> Optional[str]:
        """Lädt Icon herunter"""
        try:
            response = requests.get(icon_url, timeout=10)
            response.raise_for_status()

            # Bestimme Dateiendung
            content_type = response.headers.get('content-type', '')
            if 'image/png' in content_type:
                ext = '.png'
            elif 'image/jpeg' in content_type or 'image/jpg' in content_type:
                ext = '.jpg'
            elif 'image/gif' in content_type:
                ext = '.gif'
            else:
                ext = '.png'

            icon_file = self.sounds_dir / f"{name}_icon{ext}"
            with open(icon_file, 'wb') as f:
                f.write(response.content)

            logger.info(f"Icon heruntergeladen: {icon_file}")
            return str(icon_file)

        except Exception as e:
            logger.warning(f"Fehler beim Icon-Download: {e}")
            return None

    def delete_sound(self, sound_id: int) -> bool:
        """
        Löscht Sound

        Args:
            sound_id: ID des Sounds

        Returns:
            True bei Erfolg
        """
        try:
            sound = NippelSound.get_by_id(sound_id)

            # Lösche Dateien
            Path(sound.file_path).unlink(missing_ok=True)

            if sound.icon_path:
                Path(sound.icon_path).unlink(missing_ok=True)

            # Lösche aus DB
            sound.delete_instance()

            logger.info(f"Sound gelöscht: {sound.name}")
            return True

        except Exception as e:
            logger.error(f"Fehler beim Löschen von Sound {sound_id}: {e}")
            return False

    def update_positions(self, sound_positions: dict):
        """
        Aktualisiert Positionen mehrerer Sounds

        Args:
            sound_positions: Dict {sound_id: new_position}
        """
        try:
            with db_transaction():
                for sound_id, position in sound_positions.items():
                    update_sound_position(sound_id, position)

            logger.info(f"Positionen aktualisiert für {len(sound_positions)} Sounds")

        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren der Positionen: {e}")

    def trim_sound(self, sound_id: int, start_ms: int, end_ms: int = None) -> bool:
        """
        Schneidet Sound

        Args:
            sound_id: ID des Sounds
            start_ms: Start in Millisekunden
            end_ms: Ende in Millisekunden (None = bis Ende)

        Returns:
            True bei Erfolg
        """
        try:
            sound = NippelSound.get_by_id(sound_id)

            # Erstelle Backup
            backup_path = f"{sound.file_path}.backup"
            shutil.copy2(sound.file_path, backup_path)

            # Schneide
            success = self.processor.trim_audio(
                sound.file_path,
                sound.file_path,
                start_ms,
                end_ms
            )

            if success:
                # Aktualisiere Duration
                info = self.processor.get_audio_info(sound.file_path)
                if info:
                    sound.duration = info['duration_seconds']
                    sound.save()

                # Lösche Backup
                Path(backup_path).unlink(missing_ok=True)

                logger.info(f"Sound geschnitten: {sound.name}")
                return True
            else:
                # Stelle Backup wieder her
                shutil.move(backup_path, sound.file_path)
                return False

        except Exception as e:
            logger.error(f"Fehler beim Schneiden von Sound {sound_id}: {e}")
            return False

    def normalize_sound(self, sound_id: int) -> bool:
        """Normalisiert Sound"""
        try:
            sound = NippelSound.get_by_id(sound_id)
            return self.processor.normalize_audio(sound.file_path)
        except Exception as e:
            logger.error(f"Fehler beim Normalisieren: {e}")
            return False

    def get_all_sounds(self) -> List[NippelSound]:
        """Holt alle Sounds sortiert nach Position"""
        return list(get_all_sounds_sorted())

    def get_sound(self, sound_id: int) -> Optional[NippelSound]:
        """Holt Sound nach ID"""
        try:
            return NippelSound.get_by_id(sound_id)
        except:
            return None

    def search_sounds(self, query: str) -> List[NippelSound]:
        """Sucht Sounds nach Name"""
        return list(
            NippelSound.select().where(
                NippelSound.name.contains(query)
            ).order_by(NippelSound.position)
        )

    def import_sounds_from_directory(self, directory: str) -> int:
        """
        Importiert alle Sounds aus Verzeichnis

        Args:
            directory: Quell-Verzeichnis

        Returns:
            Anzahl importierter Sounds
        """
        dir_path = Path(directory)

        if not dir_path.is_dir():
            logger.error(f"Verzeichnis nicht gefunden: {directory}")
            return 0

        # Unterstützte Formate
        audio_extensions = {'.mp3', '.ogg', '.wav', '.flac', '.m4a'}

        count = 0
        for file in dir_path.iterdir():
            if file.suffix.lower() in audio_extensions:
                name = file.stem  # Dateiname ohne Endung

                # Suche nach Icon mit gleichem Namen
                icon_path = None
                for icon_ext in ['.png', '.jpg', '.jpeg', '.gif']:
                    potential_icon = dir_path / f"{name}{icon_ext}"
                    if potential_icon.exists():
                        icon_path = str(potential_icon)
                        break

                # Füge hinzu
                result = self.add_sound_from_file(
                    name=name,
                    source_path=str(file),
                    icon_path=icon_path
                )

                if result:
                    count += 1

        logger.info(f"{count} Sounds aus {directory} importiert")
        return count


# Singleton-Instanz
_sound_manager = None


def get_sound_manager() -> SoundManager:
    """Gibt Singleton-Instanz zurück"""
    global _sound_manager
    if _sound_manager is None:
        _sound_manager = SoundManager()
    return _sound_manager
