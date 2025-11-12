"""
Konfigurations-Loader für Nippelboard Funk
Lädt YAML-Konfiguration und stellt sie bereit
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class Config:
    """Singleton-Konfigurationsklasse"""

    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._config:
            self.load()

    def load(self, config_path: str = 'config.yaml'):
        """Lädt Konfiguration aus YAML-Datei"""
        config_file = Path(config_path)

        if not config_file.exists():
            logger.warning(f"Config-Datei {config_path} nicht gefunden. Verwende Defaults.")
            self._load_defaults()
            return

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            logger.info(f"Konfiguration geladen von {config_path}")
            self._ensure_directories()
        except Exception as e:
            logger.error(f"Fehler beim Laden der Config: {e}")
            self._load_defaults()

    def _load_defaults(self):
        """Lädt Standard-Konfiguration"""
        self._config = {
            'audio': {
                'input_device': None,
                'output_device': None,
                'sample_rate': 44100,
                'channels': 1,
                'buffer_size': 2048,
                'ringbuffer_seconds': 45,
                'clip_post_seconds': 15,
                'recording_format': 'mp3',
                'recording_bitrate': '64k'
            },
            'gpio': {
                'clip_button_pin': 17,
                'panic_button_pin': 27,
                'pull_up_down': 'up',
                'debounce_ms': 300,
                'edge_detection': 'falling'
            },
            'crypto': {
                'encryption_password': 'CHANGE_ME_INSECURE',
                'pbkdf2_iterations': 100000,
                'salt_length': 32
            },
            'storage': {
                'data_dir': './data',
                'sounds_dir': './data/sounds',
                'recordings_dir': './data/recordings',
                'clips_dir': './data/recordings/clips',
                'panic_dir': './data/recordings/panic',
                'database': './data/nippelboard.db',
                'max_storage_gb': 50
            },
            'gui': {
                'window_width': 1024,
                'window_height': 600,
                'fullscreen': False,
                'button_width': 150,
                'button_height': 150,
                'grid_columns': 5,
                'icons_dir': './assets/icons',
                'theme': 'dark'
            },
            'downloads': {
                'allowed_domains': [],
                'timeout': 30,
                'max_file_size_mb': 10
            },
            'logging': {
                'level': 'INFO',
                'file': './nippelboard.log',
                'max_size_mb': 10,
                'backup_count': 5
            },
            'performance': {
                'audio_thread_priority': 90,
                'gui_update_rate': 100,
                'cleanup_interval': 300
            }
        }
        self._ensure_directories()

    def _ensure_directories(self):
        """Erstellt notwendige Verzeichnisse"""
        dirs = [
            self.get('storage.data_dir'),
            self.get('storage.sounds_dir'),
            self.get('storage.recordings_dir'),
            self.get('storage.clips_dir'),
            self.get('storage.panic_dir'),
            self.get('gui.icons_dir')
        ]

        for directory in dirs:
            Path(directory).mkdir(parents=True, exist_ok=True)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Holt Konfigurationswert mit Punkt-Notation

        Beispiel:
            config.get('audio.sample_rate')
            config.get('gpio.clip_button_pin', 17)
        """
        keys = key.split('.')
        value = self._config

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any):
        """Setzt Konfigurationswert mit Punkt-Notation"""
        keys = key.split('.')
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def save(self, config_path: str = 'config.yaml'):
        """Speichert aktuelle Konfiguration"""
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"Konfiguration gespeichert nach {config_path}")
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Config: {e}")

    @property
    def all(self) -> Dict[str, Any]:
        """Gibt gesamte Konfiguration zurück"""
        return self._config


# Globale Config-Instanz
config = Config()
