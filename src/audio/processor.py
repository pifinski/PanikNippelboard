"""
Audio-Prozessor für Soundbearbeitung
Schneiden, Normalisieren, etc.
"""

import logging
from pathlib import Path
from typing import Tuple, Optional

from pydub import AudioSegment
from pydub.effects import normalize

logger = logging.getLogger(__name__)


class AudioProcessor:
    """Prozessor für Audio-Bearbeitung"""

    @staticmethod
    def trim_audio(input_path: str, output_path: str,
                   start_ms: int = 0, end_ms: Optional[int] = None) -> bool:
        """
        Schneidet Audio-Datei

        Args:
            input_path: Eingabe-Datei
            output_path: Ausgabe-Datei
            start_ms: Start-Zeit in Millisekunden
            end_ms: End-Zeit in Millisekunden (None = bis Ende)

        Returns:
            True bei Erfolg
        """
        try:
            # Lade Audio
            audio = AudioSegment.from_file(input_path)

            # Schneide
            if end_ms is None:
                trimmed = audio[start_ms:]
            else:
                trimmed = audio[start_ms:end_ms]

            # Speichere
            file_format = Path(output_path).suffix[1:]  # Ohne Punkt
            trimmed.export(output_path, format=file_format)

            duration_s = len(trimmed) / 1000.0
            logger.info(f"Audio geschnitten: {output_path} ({duration_s:.1f}s)")
            return True

        except Exception as e:
            logger.error(f"Fehler beim Schneiden von {input_path}: {e}")
            return False

    @staticmethod
    def normalize_audio(input_path: str, output_path: str = None) -> bool:
        """
        Normalisiert Audio (maximiert Lautstärke ohne Clipping)

        Args:
            input_path: Eingabe-Datei
            output_path: Ausgabe-Datei (None = überschreibe Original)

        Returns:
            True bei Erfolg
        """
        if output_path is None:
            output_path = input_path

        try:
            audio = AudioSegment.from_file(input_path)
            normalized = normalize(audio)

            file_format = Path(output_path).suffix[1:]
            normalized.export(output_path, format=file_format)

            logger.info(f"Audio normalisiert: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Fehler beim Normalisieren von {input_path}: {e}")
            return False

    @staticmethod
    def fade_in_out(input_path: str, output_path: str,
                    fade_in_ms: int = 0, fade_out_ms: int = 0) -> bool:
        """
        Fügt Fade-In/Out hinzu

        Args:
            input_path: Eingabe-Datei
            output_path: Ausgabe-Datei
            fade_in_ms: Fade-In Dauer (ms)
            fade_out_ms: Fade-Out Dauer (ms)

        Returns:
            True bei Erfolg
        """
        try:
            audio = AudioSegment.from_file(input_path)

            if fade_in_ms > 0:
                audio = audio.fade_in(fade_in_ms)

            if fade_out_ms > 0:
                audio = audio.fade_out(fade_out_ms)

            file_format = Path(output_path).suffix[1:]
            audio.export(output_path, format=file_format)

            logger.info(f"Fade-In/Out hinzugefügt: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Fehler beim Fade: {e}")
            return False

    @staticmethod
    def get_audio_info(file_path: str) -> Optional[dict]:
        """
        Holt Informationen über Audio-Datei

        Returns:
            Dict mit duration_seconds, channels, sample_rate, format
        """
        try:
            audio = AudioSegment.from_file(file_path)

            return {
                'duration_seconds': len(audio) / 1000.0,
                'channels': audio.channels,
                'sample_rate': audio.frame_rate,
                'format': Path(file_path).suffix[1:],
                'file_size_bytes': Path(file_path).stat().st_size
            }

        except Exception as e:
            logger.error(f"Fehler beim Lesen von {file_path}: {e}")
            return None

    @staticmethod
    def convert_format(input_path: str, output_path: str,
                       bitrate: str = '128k') -> bool:
        """
        Konvertiert Audio-Format

        Args:
            input_path: Eingabe
            output_path: Ausgabe (Format über Endung)
            bitrate: Bitrate für komprimierte Formate

        Returns:
            True bei Erfolg
        """
        try:
            audio = AudioSegment.from_file(input_path)
            file_format = Path(output_path).suffix[1:]

            audio.export(
                output_path,
                format=file_format,
                bitrate=bitrate
            )

            logger.info(f"Format konvertiert: {input_path} -> {output_path}")
            return True

        except Exception as e:
            logger.error(f"Fehler bei Konvertierung: {e}")
            return False

    @staticmethod
    def change_speed(input_path: str, output_path: str,
                     speed_factor: float = 1.0) -> bool:
        """
        Ändert Wiedergabegeschwindigkeit (ohne Tonhöhen-Änderung wäre aufwendiger)

        Args:
            input_path: Eingabe
            output_path: Ausgabe
            speed_factor: Faktor (0.5 = halb so schnell, 2.0 = doppelt so schnell)

        Returns:
            True bei Erfolg
        """
        try:
            audio = AudioSegment.from_file(input_path)

            # Einfache Geschwindigkeitsänderung (ändert auch Tonhöhe)
            # Für bessere Qualität: ffmpeg mit atempo filter verwenden
            new_frame_rate = int(audio.frame_rate * speed_factor)
            audio = audio._spawn(audio.raw_data, overrides={
                'frame_rate': new_frame_rate
            })
            audio = audio.set_frame_rate(44100)  # Zurück zu Standard

            file_format = Path(output_path).suffix[1:]
            audio.export(output_path, format=file_format)

            logger.info(f"Geschwindigkeit geändert: {output_path} (Faktor: {speed_factor})")
            return True

        except Exception as e:
            logger.error(f"Fehler bei Geschwindigkeitsänderung: {e}")
            return False

    @staticmethod
    def combine_audio(audio_paths: list, output_path: str,
                      crossfade_ms: int = 0) -> bool:
        """
        Kombiniert mehrere Audio-Dateien

        Args:
            audio_paths: Liste von Eingabe-Dateien
            output_path: Ausgabe
            crossfade_ms: Crossfade zwischen Tracks (ms)

        Returns:
            True bei Erfolg
        """
        try:
            if not audio_paths:
                logger.error("Keine Audio-Dateien angegeben")
                return False

            # Lade erste Datei
            combined = AudioSegment.from_file(audio_paths[0])

            # Füge weitere hinzu
            for path in audio_paths[1:]:
                next_audio = AudioSegment.from_file(path)

                if crossfade_ms > 0:
                    combined = combined.append(next_audio, crossfade=crossfade_ms)
                else:
                    combined = combined + next_audio

            # Speichere
            file_format = Path(output_path).suffix[1:]
            combined.export(output_path, format=file_format)

            duration_s = len(combined) / 1000.0
            logger.info(f"Audio kombiniert: {output_path} ({duration_s:.1f}s)")
            return True

        except Exception as e:
            logger.error(f"Fehler beim Kombinieren: {e}")
            return False
