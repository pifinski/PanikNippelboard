"""
Audio-Player für Nippelboard
Spielt Sounds über Funkgerät (USB-Soundkarte) ab
"""

import logging
import threading
from pathlib import Path
from typing import Optional

import sounddevice as sd
import soundfile as sf
import numpy as np

from ..utils.config import config

logger = logging.getLogger(__name__)


class AudioPlayer:
    """
    Audio-Player für Soundboard

    Features:
    - Spielt Audio-Dateien über Output-Device
    - Unterstützt verschiedene Formate (MP3, WAV, OGG, etc.)
    - Lautstärke-Kontrolle
    - Stop-Funktion
    """

    def __init__(self):
        # Konfiguration
        self.output_device = config.get('audio.output_device')
        self.sample_rate = config.get('audio.sample_rate', 44100)

        # Status
        self.is_playing = False
        self.current_sound = None
        self.stream = None
        self.lock = threading.Lock()

        # Playback-Thread
        self.playback_thread = None

        logger.info(f"AudioPlayer initialisiert (Device={self.output_device})")

    def play(self, file_path: str, volume: float = 1.0, blocking: bool = False):
        """
        Spielt Audio-Datei ab

        Args:
            file_path: Pfad zur Audio-Datei
            volume: Lautstärke (0.0 - 1.0)
            blocking: Falls True, wartet bis Wiedergabe fertig
        """
        if not Path(file_path).exists():
            logger.error(f"Audio-Datei nicht gefunden: {file_path}")
            return

        # Stoppe aktuelle Wiedergabe falls läuft
        if self.is_playing:
            self.stop()

        self.current_sound = file_path

        if blocking:
            self._play_sound(file_path, volume)
        else:
            # Starte in separatem Thread
            self.playback_thread = threading.Thread(
                target=self._play_sound,
                args=(file_path, volume),
                daemon=True
            )
            self.playback_thread.start()

    def _play_sound(self, file_path: str, volume: float):
        """Interne Funktion zum Abspielen"""
        try:
            # Lade Audio-Datei
            data, file_sample_rate = sf.read(file_path, dtype='float32')

            # Resampling falls nötig (vereinfacht, besser wäre scipy.signal.resample)
            if file_sample_rate != self.sample_rate:
                logger.warning(
                    f"Sample-Rate Unterschied: {file_sample_rate} -> {self.sample_rate}. "
                    f"Verwende ffmpeg oder scipy für besseres Resampling."
                )
                # Für jetzt: Einfaches Resampling
                ratio = self.sample_rate / file_sample_rate
                new_length = int(len(data) * ratio)
                data = np.interp(
                    np.linspace(0, len(data), new_length),
                    np.arange(len(data)),
                    data
                )

            # Konvertiere zu Mono falls nötig
            if len(data.shape) > 1:
                data = np.mean(data, axis=1)

            # Lautstärke anpassen
            data = data * volume

            # Verhindere Clipping
            data = np.clip(data, -1.0, 1.0)

            with self.lock:
                self.is_playing = True

            # Spiele ab
            sd.play(data, self.sample_rate, device=self.output_device)
            sd.wait()  # Warte bis fertig

            logger.info(f"Wiedergabe abgeschlossen: {Path(file_path).name}")

        except Exception as e:
            logger.error(f"Fehler beim Abspielen von {file_path}: {e}")

        finally:
            with self.lock:
                self.is_playing = False
                self.current_sound = None

    def stop(self):
        """Stoppt aktuelle Wiedergabe"""
        if not self.is_playing:
            return

        try:
            sd.stop()
            logger.info("Wiedergabe gestoppt")
        except Exception as e:
            logger.error(f"Fehler beim Stoppen: {e}")

        with self.lock:
            self.is_playing = False
            self.current_sound = None

    def get_status(self) -> dict:
        """Gibt aktuellen Status zurück"""
        with self.lock:
            return {
                'is_playing': self.is_playing,
                'current_sound': self.current_sound
            }

    def list_devices(self):
        """Listet verfügbare Audio-Geräte"""
        devices = sd.query_devices()
        logger.info("Verfügbare Audio-Geräte:")
        for idx, device in enumerate(devices):
            logger.info(f"  [{idx}] {device['name']} (Out: {device['max_output_channels']})")
        return devices


# Utility-Funktion für einfachen Zugriff
_player_instance = None


def get_player() -> AudioPlayer:
    """Gibt Singleton-Instanz des Players zurück"""
    global _player_instance
    if _player_instance is None:
        _player_instance = AudioPlayer()
    return _player_instance
