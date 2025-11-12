"""
Audio-Recorder mit Ringbuffer für Dashcam-Funktion
Kontinuierliche Aufnahme mit der Möglichkeit, Clips zu speichern
"""

import logging
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

import numpy as np
import sounddevice as sd
import soundfile as sf
from pydub import AudioSegment

from ..utils.config import config
from ..utils.database import add_recording

logger = logging.getLogger(__name__)


class AudioRecorder:
    """
    Audio-Recorder mit Ringbuffer

    Features:
    - Kontinuierliche Aufnahme im Hintergrund
    - Ringbuffer hält letzte N Sekunden
    - Clips speichern (X Sekunden vorher + Y Sekunden nachher)
    - Panik-Modus: Vollständige Aufnahme
    """

    def __init__(self):
        # Konfiguration laden
        self.sample_rate = config.get('audio.sample_rate', 44100)
        self.channels = config.get('audio.channels', 1)
        self.input_device = config.get('audio.input_device')
        self.buffer_size = config.get('audio.buffer_size', 2048)

        # Ringbuffer-Größe
        self.ringbuffer_seconds = config.get('audio.ringbuffer_seconds', 45)
        self.ringbuffer_frames = int(self.sample_rate * self.ringbuffer_seconds)

        # Clip-Einstellungen
        self.clip_post_seconds = config.get('audio.clip_post_seconds', 15)
        self.clip_post_frames = int(self.sample_rate * self.clip_post_seconds)

        # Speicherformat
        self.recording_format = config.get('audio.recording_format', 'mp3')
        self.recording_bitrate = config.get('audio.recording_bitrate', '64k')

        # Ringbuffer (Deque für effizientes FIFO)
        self.ringbuffer = deque(maxlen=self.ringbuffer_frames)

        # Status
        self.is_running = False
        self.is_panic_mode = False
        self.panic_buffer = []
        self.panic_start_time = None

        # Threading
        self.stream = None
        self.lock = threading.Lock()

        # Callbacks
        self.on_clip_saved: Optional[Callable] = None
        self.on_panic_saved: Optional[Callable] = None

        logger.info(f"AudioRecorder initialisiert (SR={self.sample_rate}, Ringbuffer={self.ringbuffer_seconds}s)")

    def start(self):
        """Startet kontinuierliche Aufnahme"""
        if self.is_running:
            logger.warning("Recorder läuft bereits")
            return

        try:
            self.is_running = True
            self.stream = sd.InputStream(
                device=self.input_device,
                channels=self.channels,
                samplerate=self.sample_rate,
                blocksize=self.buffer_size,
                callback=self._audio_callback
            )
            self.stream.start()
            logger.info("Audio-Aufnahme gestartet")

        except Exception as e:
            logger.error(f"Fehler beim Starten der Aufnahme: {e}")
            self.is_running = False
            raise

    def stop(self):
        """Stoppt kontinuierliche Aufnahme"""
        if not self.is_running:
            return

        self.is_running = False

        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        logger.info("Audio-Aufnahme gestoppt")

    def _audio_callback(self, indata, frames, time_info, status):
        """
        Callback für Audio-Stream
        Wird kontinuierlich aufgerufen
        """
        if status:
            logger.warning(f"Audio-Stream-Status: {status}")

        # Konvertiere zu Mono falls nötig
        if self.channels == 1 and len(indata.shape) > 1:
            audio_data = np.mean(indata, axis=1)
        else:
            audio_data = indata.copy().flatten()

        with self.lock:
            # Füge zu Ringbuffer hinzu
            self.ringbuffer.extend(audio_data)

            # Falls Panik-Modus: Speichere alles
            if self.is_panic_mode:
                self.panic_buffer.extend(audio_data)

    def save_clip(self, filename: str = None) -> Optional[str]:
        """
        Speichert Clip: Ringbuffer (45s vorher) + nächste 15s

        Args:
            filename: Optional, sonst automatisch generiert

        Returns:
            Pfad zur gespeicherten Datei oder None bei Fehler
        """
        if not self.is_running:
            logger.error("Recorder läuft nicht, kann keinen Clip speichern")
            return None

        # Generiere Dateinamen
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"clip_{timestamp}.{self.recording_format}"

        clips_dir = Path(config.get('storage.clips_dir', './data/recordings/clips'))
        clips_dir.mkdir(parents=True, exist_ok=True)
        file_path = clips_dir / filename

        try:
            # Kopiere aktuellen Ringbuffer
            with self.lock:
                pre_data = np.array(self.ringbuffer, dtype=np.float32)

            logger.info(f"Speichere Clip: {self.ringbuffer_seconds}s vorher + {self.clip_post_seconds}s nachher...")

            # Warte und sammle Post-Daten
            post_data = self._capture_post_audio()

            # Kombiniere Pre + Post
            full_audio = np.concatenate([pre_data, post_data])

            # Speichere als temporäre WAV
            temp_wav = clips_dir / f"temp_{filename}.wav"
            sf.write(temp_wav, full_audio, self.sample_rate)

            # Konvertiere zu gewünschtem Format
            final_path = self._convert_audio(temp_wav, file_path)

            # Lösche temporäre Datei
            temp_wav.unlink(missing_ok=True)

            # Speichere in Datenbank
            file_size = final_path.stat().st_size
            duration = len(full_audio) / self.sample_rate

            add_recording(
                filename=filename,
                file_path=str(final_path),
                recording_type='clip',
                duration=duration,
                file_size=file_size,
                is_encrypted=False
            )

            logger.info(f"Clip gespeichert: {final_path} ({duration:.1f}s, {file_size/1024:.1f} KB)")

            # Callback
            if self.on_clip_saved:
                self.on_clip_saved(str(final_path))

            return str(final_path)

        except Exception as e:
            logger.error(f"Fehler beim Speichern des Clips: {e}")
            return None

    def _capture_post_audio(self) -> np.ndarray:
        """Nimmt Post-Audio auf (X Sekunden nach Button-Druck)"""
        post_buffer = []
        target_frames = self.clip_post_frames
        start_time = time.time()
        timeout = self.clip_post_seconds + 5  # Safety timeout

        while len(post_buffer) < target_frames:
            # Timeout-Check
            if time.time() - start_time > timeout:
                logger.warning("Post-Audio Timeout erreicht")
                break

            # Sammle neue Daten aus Ringbuffer
            with self.lock:
                if len(self.ringbuffer) > 0:
                    # Hole neueste Daten
                    chunk_size = min(self.buffer_size, target_frames - len(post_buffer))
                    new_data = list(self.ringbuffer)[-chunk_size:]
                    post_buffer.extend(new_data)

            time.sleep(0.01)  # Kleine Pause

        return np.array(post_buffer, dtype=np.float32)

    def start_panic_mode(self):
        """Startet Panik-Modus: Aufnahme von allem"""
        if self.is_panic_mode:
            logger.warning("Panik-Modus bereits aktiv")
            return

        with self.lock:
            self.is_panic_mode = True
            self.panic_buffer = list(self.ringbuffer)  # Starte mit Ringbuffer
            self.panic_start_time = datetime.now()

        logger.warning("PANIK-MODUS GESTARTET")

    def stop_panic_mode(self, filename: str = None) -> Optional[str]:
        """
        Stoppt Panik-Modus und speichert verschlüsselte Aufnahme

        Args:
            filename: Optional, sonst automatisch generiert

        Returns:
            Pfad zur gespeicherten verschlüsselten Datei
        """
        if not self.is_panic_mode:
            logger.warning("Panik-Modus ist nicht aktiv")
            return None

        # Stoppe Panik-Modus
        with self.lock:
            self.is_panic_mode = False
            panic_data = np.array(self.panic_buffer, dtype=np.float32)
            self.panic_buffer = []
            panic_duration = (datetime.now() - self.panic_start_time).total_seconds()

        logger.warning(f"PANIK-MODUS GESTOPPT (Dauer: {panic_duration:.1f}s)")

        # Generiere Dateinamen
        if filename is None:
            timestamp = self.panic_start_time.strftime("%Y%m%d_%H%M%S")
            filename = f"panic_{timestamp}.{self.recording_format}.enc"  # .enc für encrypted

        panic_dir = Path(config.get('storage.panic_dir', './data/recordings/panic'))
        panic_dir.mkdir(parents=True, exist_ok=True)
        file_path = panic_dir / filename

        try:
            # Speichere als temporäre WAV
            temp_wav = panic_dir / f"temp_{filename}.wav"
            sf.write(temp_wav, panic_data, self.sample_rate)

            # Konvertiere zu gewünschtem Format (noch unverschlüsselt)
            temp_audio = panic_dir / f"temp_{filename}.{self.recording_format}"
            self._convert_audio(temp_wav, temp_audio)

            # Verschlüssele (asymmetrisch oder symmetrisch)
            crypto_mode = config.get('crypto.mode', 'asymmetric')

            if crypto_mode == 'asymmetric':
                # Asymmetrische Verschlüsselung (EMPFOHLEN)
                from ..crypto.asymmetric import AsymmetricCrypto
                public_key_path = config.get('crypto.public_key_path', './public_key.pem')

                if not Path(public_key_path).exists():
                    logger.error(
                        f"Public Key nicht gefunden: {public_key_path}\n"
                        "Generieren Sie ein Schlüsselpaar mit:\n"
                        "  python -m src.crypto.asymmetric generate"
                    )
                    return None

                crypto = AsymmetricCrypto(public_key_path=public_key_path)
                encrypted_path = crypto.encrypt_file(str(temp_audio), str(file_path))

            else:
                # Symmetrische Verschlüsselung (UNSICHER bei Beschlagnahmung)
                logger.warning("⚠️  Verwende symmetrische Verschlüsselung (Passwort auf Gerät!)")
                from ..crypto.encryption import encrypt_file
                encrypted_path = encrypt_file(str(temp_audio), str(file_path))

            # Lösche temporäre Dateien
            temp_wav.unlink(missing_ok=True)
            temp_audio.unlink(missing_ok=True)

            # Speichere in Datenbank
            file_size = Path(encrypted_path).stat().st_size
            duration = len(panic_data) / self.sample_rate

            add_recording(
                filename=filename,
                file_path=encrypted_path,
                recording_type='panic',
                duration=duration,
                file_size=file_size,
                is_encrypted=True
            )

            logger.info(f"Panik-Aufnahme verschlüsselt gespeichert: {encrypted_path}")

            # Callback
            if self.on_panic_saved:
                self.on_panic_saved(encrypted_path)

            return encrypted_path

        except Exception as e:
            logger.error(f"Fehler beim Speichern der Panik-Aufnahme: {e}")
            return None

    def _convert_audio(self, input_path: Path, output_path: Path) -> Path:
        """
        Konvertiert Audio zu gewünschtem Format

        Args:
            input_path: Eingabe-WAV
            output_path: Ausgabe-Pfad

        Returns:
            Pfad zur konvertierten Datei
        """
        if self.recording_format == 'wav':
            # Keine Konvertierung nötig
            if input_path != output_path:
                input_path.rename(output_path)
            return output_path

        # Lade WAV
        audio = AudioSegment.from_wav(str(input_path))

        # Konvertiere
        if self.recording_format == 'mp3':
            audio.export(
                str(output_path),
                format='mp3',
                bitrate=self.recording_bitrate,
                parameters=["-q:a", "2"]  # VBR Qualität
            )
        elif self.recording_format == 'ogg':
            audio.export(
                str(output_path),
                format='ogg',
                bitrate=self.recording_bitrate
            )
        else:
            logger.warning(f"Unbekanntes Format {self.recording_format}, verwende MP3")
            audio.export(str(output_path), format='mp3', bitrate=self.recording_bitrate)

        return output_path

    def get_buffer_status(self) -> dict:
        """Gibt Status des Ringbuffers zurück"""
        with self.lock:
            buffer_fill = len(self.ringbuffer) / self.ringbuffer_frames * 100
            return {
                'is_running': self.is_running,
                'is_panic_mode': self.is_panic_mode,
                'buffer_fill_percent': buffer_fill,
                'buffer_seconds': len(self.ringbuffer) / self.sample_rate,
                'panic_duration': (datetime.now() - self.panic_start_time).total_seconds()
                if self.is_panic_mode and self.panic_start_time else 0
            }

    def __del__(self):
        """Cleanup beim Beenden"""
        self.stop()
