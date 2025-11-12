"""
Custom Widgets für Nippelboard GUI
"""

import logging
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import (
    QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QWidget,
    QFrame, QProgressBar
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QIcon, QFont

logger = logging.getLogger(__name__)


class SoundButton(QPushButton):
    """
    Button für einen Nippel-Sound

    Features:
    - Zeigt Icon/Bild
    - Zeigt Name
    - Highlight beim Spielen
    """

    # Signal wenn Button geklickt
    sound_clicked = pyqtSignal(int)  # sound_id

    def __init__(self, sound_id: int, name: str, icon_path: str = None,
                 parent=None):
        super().__init__(parent)

        self.sound_id = sound_id
        self.sound_name = name
        self.icon_path = icon_path
        self.is_playing = False

        self._setup_ui()

    def _setup_ui(self):
        """Setup UI"""
        # Größe
        self.setMinimumSize(150, 150)
        self.setMaximumSize(200, 200)

        # Icon falls vorhanden
        if self.icon_path and Path(self.icon_path).exists():
            icon = QIcon(self.icon_path)
            self.setIcon(icon)
            self.setIconSize(QSize(100, 100))

        # Text
        self.setText(self.sound_name)

        # Style
        self.setStyleSheet("""
            QPushButton {
                background-color: #2c3e50;
                color: white;
                border: 2px solid #34495e;
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #34495e;
                border-color: #3498db;
            }
            QPushButton:pressed {
                background-color: #1abc9c;
            }
        """)

        # Click-Handler
        self.clicked.connect(lambda: self.sound_clicked.emit(self.sound_id))

    def set_playing(self, playing: bool):
        """Setzt Playing-Status (visuelles Feedback)"""
        self.is_playing = playing

        if playing:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60;
                    color: white;
                    border: 3px solid #2ecc71;
                    border-radius: 10px;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 5px;
                }
            """)
        else:
            # Zurück zu Normal
            self._setup_ui()


class StatusPanel(QFrame):
    """
    Status-Panel für Recorder-Info

    Zeigt:
    - Ringbuffer-Status
    - Panik-Modus
    - Letzte Aufnahme
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._setup_ui()

    def _setup_ui(self):
        """Setup UI"""
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet("""
            QFrame {
                background-color: #34495e;
                border-radius: 5px;
                padding: 10px;
            }
        """)

        layout = QVBoxLayout()

        # Titel
        title = QLabel("📡 Funk-Monitor")
        title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Ringbuffer-Status
        self.buffer_label = QLabel("Ringbuffer: 0%")
        self.buffer_label.setStyleSheet("color: #ecf0f1;")
        layout.addWidget(self.buffer_label)

        self.buffer_progress = QProgressBar()
        self.buffer_progress.setMaximum(100)
        self.buffer_progress.setValue(0)
        self.buffer_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #2c3e50;
                border-radius: 3px;
                background-color: #2c3e50;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #3498db;
            }
        """)
        layout.addWidget(self.buffer_progress)

        # Panik-Status
        self.panic_label = QLabel("Panik-Modus: Inaktiv")
        self.panic_label.setStyleSheet("color: #2ecc71; font-weight: bold;")
        layout.addWidget(self.panic_label)

        # Letzte Aufnahme
        self.last_clip_label = QLabel("Letzter Clip: -")
        self.last_clip_label.setStyleSheet("color: #ecf0f1; font-size: 10px;")
        self.last_clip_label.setWordWrap(True)
        layout.addWidget(self.last_clip_label)

        self.setLayout(layout)

    def update_status(self, status: dict):
        """
        Aktualisiert Status

        Args:
            status: Dict mit buffer_fill_percent, is_panic_mode, etc.
        """
        # Buffer
        buffer_percent = int(status.get('buffer_fill_percent', 0))
        self.buffer_progress.setValue(buffer_percent)
        self.buffer_label.setText(f"Ringbuffer: {buffer_percent}%")

        # Panik
        is_panic = status.get('is_panic_mode', False)
        if is_panic:
            panic_duration = status.get('panic_duration', 0)
            self.panic_label.setText(f"⚠️ PANIK-MODUS: {panic_duration:.0f}s")
            self.panic_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        else:
            self.panic_label.setText("Panik-Modus: Inaktiv")
            self.panic_label.setStyleSheet("color: #2ecc71; font-weight: bold;")

    def update_last_clip(self, filename: str):
        """Aktualisiert letzte Clip-Info"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.last_clip_label.setText(f"Letzter Clip: {filename}\n{timestamp}")


class ControlPanel(QFrame):
    """
    Kontroll-Panel mit Buttons

    Buttons:
    - Clip speichern (falls GPIO nicht verfügbar)
    - Panik-Modus toggle
    - Sound hinzufügen
    - Einstellungen
    """

    # Signals
    clip_requested = pyqtSignal()
    panic_toggled = pyqtSignal(bool)
    add_sound_requested = pyqtSignal()
    settings_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.panic_active = False
        self._setup_ui()

    def _setup_ui(self):
        """Setup UI"""
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet("""
            QFrame {
                background-color: #2c3e50;
                border-radius: 5px;
                padding: 10px;
            }
        """)

        layout = QVBoxLayout()

        # Clip-Button
        self.clip_btn = QPushButton("💾 Clip Speichern")
        self.clip_btn.setMinimumHeight(50)
        self.clip_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1abc9c;
            }
        """)
        self.clip_btn.clicked.connect(self.clip_requested.emit)
        layout.addWidget(self.clip_btn)

        # Panik-Button
        self.panic_btn = QPushButton("🚨 Panik-Modus")
        self.panic_btn.setMinimumHeight(50)
        self.panic_btn.setCheckable(True)
        self.panic_btn.setStyleSheet("""
            QPushButton {
                background-color: #e67e22;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d35400;
            }
            QPushButton:checked {
                background-color: #c0392b;
            }
        """)
        self.panic_btn.clicked.connect(self._on_panic_clicked)
        layout.addWidget(self.panic_btn)

        # Add Sound Button
        self.add_sound_btn = QPushButton("➕ Sound hinzufügen")
        self.add_sound_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        self.add_sound_btn.clicked.connect(self.add_sound_requested.emit)
        layout.addWidget(self.add_sound_btn)

        # Settings Button
        self.settings_btn = QPushButton("⚙️ Einstellungen")
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #7f8c8d;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #95a5a6;
            }
        """)
        self.settings_btn.clicked.connect(self.settings_requested.emit)
        layout.addWidget(self.settings_btn)

        layout.addStretch()

        self.setLayout(layout)

    def _on_panic_clicked(self):
        """Panik-Button geklickt"""
        self.panic_active = self.panic_btn.isChecked()
        self.panic_toggled.emit(self.panic_active)

        if self.panic_active:
            self.panic_btn.setText("🚨 PANIK AKTIV - STOP")
        else:
            self.panic_btn.setText("🚨 Panik-Modus")

    def set_panic_active(self, active: bool):
        """Setzt Panik-Status von außen"""
        self.panic_active = active
        self.panic_btn.setChecked(active)

        if active:
            self.panic_btn.setText("🚨 PANIK AKTIV - STOP")
        else:
            self.panic_btn.setText("🚨 Panik-Modus")
