"""
Universal Sound Downloader
Unterstützt YouTube, SoundCloud, und viele weitere Plattformen via yt-dlp
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict
import re

logger = logging.getLogger(__name__)


class UniversalDownloader:
    """
    Universal Sound Downloader

    Unterstützte Plattformen:
    - YouTube
    - SoundCloud
    - Vimeo
    - Twitter
    - TikTok
    - und viele mehr (via yt-dlp)
    """

    def __init__(self):
        self.supported_sites = [
            'youtube.com', 'youtu.be',
            'soundcloud.com',
            'vimeo.com',
            'twitter.com', 'x.com',
            'tiktok.com',
            'twitch.tv',
            'facebook.com',
            'instagram.com'
        ]

    def is_supported_url(self, url: str) -> bool:
        """
        Prüft ob URL unterstützt wird

        Args:
            url: URL zum Prüfen

        Returns:
            True wenn unterstützt
        """
        url_lower = url.lower()
        return any(site in url_lower for site in self.supported_sites)

    def get_info(self, url: str) -> Optional[Dict]:
        """
        Holt Metadaten zu Video/Audio

        Args:
            url: URL zum Video/Audio

        Returns:
            Dict mit title, duration, thumbnail, etc. oder None
        """
        try:
            # yt-dlp --dump-json für Metadaten
            result = subprocess.run(
                ['yt-dlp', '--dump-json', '--no-playlist', url],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                logger.error(f"yt-dlp info error: {result.stderr}")
                return None

            # Parse JSON
            import json
            info = json.loads(result.stdout)

            return {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail'),
                'uploader': info.get('uploader'),
                'description': info.get('description', '')[:200]  # Gekürzt
            }

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout beim Abrufen der Infos für {url}")
            return None
        except Exception as e:
            logger.error(f"Fehler beim Info-Abruf: {e}")
            return None

    def download(
        self,
        url: str,
        output_path: Path,
        format: str = 'mp3',
        quality: str = '128k',
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        max_duration: int = 300  # Max 5 Minuten
    ) -> bool:
        """
        Lädt Sound von URL herunter

        Args:
            url: URL zum Video/Audio
            output_path: Ausgabepfad (ohne Endung)
            format: Ausgabeformat (mp3, ogg, wav)
            quality: Bitrate für MP3 (z.B. '128k')
            start_time: Start-Zeit in Sekunden (zum Kürzen)
            end_time: End-Zeit in Sekunden (zum Kürzen)
            max_duration: Maximale Dauer in Sekunden

        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            # Erstelle temporäres Verzeichnis
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # yt-dlp Argumente
                cmd = [
                    'yt-dlp',
                    '--no-playlist',  # Nur einzelnes Video
                    '--extract-audio',  # Nur Audio
                    '--audio-format', format,
                    '--audio-quality', quality,
                    '--output', str(temp_path / '%(title)s.%(ext)s'),
                    '--no-warnings',
                    '--no-progress'
                ]

                # Max-Dauer-Filter (yt-dlp integriert)
                if max_duration:
                    cmd.extend(['--match-filter', f'duration < {max_duration}'])

                # URL
                cmd.append(url)

                logger.info(f"Starte Download: {url}")
                logger.debug(f"yt-dlp command: {' '.join(cmd)}")

                # Download
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=180  # 3 Minuten Timeout
                )

                if result.returncode != 0:
                    logger.error(f"yt-dlp error: {result.stderr}")
                    return False

                # Finde heruntergeladene Datei
                downloaded_files = list(temp_path.glob(f'*.{format}'))

                if not downloaded_files:
                    logger.error("Keine Datei heruntergeladen")
                    return False

                downloaded_file = downloaded_files[0]

                # Optional: Schneiden mit ffmpeg
                if start_time is not None or end_time is not None:
                    cut_file = temp_path / f"cut.{format}"
                    if not self._cut_audio(downloaded_file, cut_file, start_time, end_time):
                        logger.warning("Schneiden fehlgeschlagen, verwende Original")
                    else:
                        downloaded_file = cut_file

                # Verschiebe zu Zielpfad
                final_path = output_path.parent / f"{output_path.stem}.{format}"
                downloaded_file.rename(final_path)

                logger.info(f"Download erfolgreich: {final_path}")
                return True

        except subprocess.TimeoutExpired:
            logger.error(f"Download-Timeout für {url}")
            return False
        except Exception as e:
            logger.exception(f"Download-Fehler: {e}")
            return False

    def _cut_audio(
        self,
        input_path: Path,
        output_path: Path,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> bool:
        """
        Schneidet Audio mit ffmpeg

        Args:
            input_path: Eingabedatei
            output_path: Ausgabedatei
            start_time: Start in Sekunden
            end_time: Ende in Sekunden

        Returns:
            True bei Erfolg
        """
        try:
            cmd = ['ffmpeg', '-i', str(input_path)]

            if start_time is not None:
                cmd.extend(['-ss', str(start_time)])

            if end_time is not None:
                if start_time is not None:
                    duration = end_time - start_time
                else:
                    duration = end_time
                cmd.extend(['-t', str(duration)])

            cmd.extend([
                '-acodec', 'copy',  # Kein Re-Encoding
                '-y',  # Überschreiben
                str(output_path)
            ])

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=60
            )

            return result.returncode == 0

        except Exception as e:
            logger.error(f"Schneiden fehlgeschlagen: {e}")
            return False

    def download_thumbnail(self, url: str, output_path: Path) -> bool:
        """
        Lädt Thumbnail/Icon herunter

        Args:
            url: URL zum Video
            output_path: Pfad für Thumbnail

        Returns:
            True bei Erfolg
        """
        try:
            cmd = [
                'yt-dlp',
                '--write-thumbnail',
                '--skip-download',
                '--convert-thumbnails', 'jpg',
                '--output', str(output_path.with_suffix('')),
                url
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30
            )

            # Finde heruntergeladenes Thumbnail
            thumb_files = list(output_path.parent.glob(f"{output_path.stem}.*"))

            if thumb_files:
                # Rename zu gewünschtem Pfad
                thumb_files[0].rename(output_path)
                return True

            return False

        except Exception as e:
            logger.error(f"Thumbnail-Download fehlgeschlagen: {e}")
            return False


def check_yt_dlp_installed() -> bool:
    """
    Prüft ob yt-dlp installiert ist

    Returns:
        True wenn verfügbar
    """
    try:
        result = subprocess.run(
            ['yt-dlp', '--version'],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def install_yt_dlp() -> bool:
    """
    Installiert yt-dlp via pip

    Returns:
        True bei Erfolg
    """
    try:
        logger.info("Installiere yt-dlp...")
        result = subprocess.run(
            ['pip', 'install', 'yt-dlp'],
            capture_output=True,
            timeout=120
        )
        return result.returncode == 0
    except Exception as e:
        logger.error(f"yt-dlp Installation fehlgeschlagen: {e}")
        return False
