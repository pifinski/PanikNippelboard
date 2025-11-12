#!/usr/bin/env python3
"""
Nippelboard Funk - Hauptprogramm

Funküberwachung und Soundboard für Raspberry Pi
"""

import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PyQt5.QtWidgets import QApplication

# Imports aus src
from src.utils.config import config
from src.utils.database import init_database, close_database
from src.audio.recorder import AudioRecorder
from src.gpio.buttons import create_button_handler
from src.gui.nippelboard import NippelboardWindow


def setup_logging():
    """Konfiguriert Logging"""
    log_level = config.get('logging.level', 'INFO')
    log_file = config.get('logging.file', './nippelboard.log')
    max_size_mb = config.get('logging.max_size_mb', 10)
    backup_count = config.get('logging.backup_count', 5)

    # Root Logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level))

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler (mit Rotation)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_size_mb * 1024 * 1024,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, log_level))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.info("=" * 60)
    logger.info("Nippelboard Funk gestartet")
    logger.info("=" * 60)


def main():
    """Hauptprogramm"""
    # Setup Logging
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        # Initialisiere Datenbank
        logger.info("Initialisiere Datenbank...")
        init_database()

        # Erstelle Qt Application
        logger.info("Starte GUI...")
        app = QApplication(sys.argv)
        app.setApplicationName("Nippelboard Funk")

        # Erstelle Audio-Recorder
        logger.info("Initialisiere Audio-Recorder...")
        recorder = AudioRecorder()

        # Erstelle GPIO-Handler
        logger.info("Initialisiere GPIO-Handler...")
        button_handler = create_button_handler()

        # Starte Recorder
        logger.info("Starte Audio-Aufnahme...")
        recorder.start()

        # Erstelle Hauptfenster
        logger.info("Erstelle Hauptfenster...")
        window = NippelboardWindow(recorder, button_handler)
        window.show()

        logger.info("Nippelboard läuft!")

        # Event Loop
        exit_code = app.exec_()

        # Cleanup
        logger.info("Beende Nippelboard...")
        recorder.stop()
        button_handler.cleanup()
        close_database()

        logger.info("Nippelboard beendet")
        sys.exit(exit_code)

    except KeyboardInterrupt:
        logger.info("Beendet durch Benutzer (Ctrl+C)")
        sys.exit(0)

    except Exception as e:
        logger.exception(f"Kritischer Fehler: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
