"""
Nippelboard Hauptfenster (PyQt5)
"""

import logging
from typing import Dict

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QScrollArea, QMessageBox, QFileDialog,
    QInputDialog, QLabel
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from .widgets import SoundButton, StatusPanel, ControlPanel
from ..audio.player import get_player
from ..sounds.manager import get_sound_manager
from ..utils.database import NippelSound
from ..utils.config import config

logger = logging.getLogger(__name__)


class NippelboardWindow(QMainWindow):
    """
    Hauptfenster für Nippelboard

    Features:
    - Grid mit Sound-Buttons
    - Status-Panel
    - Kontroll-Panel
    - Auto-Update
    """

    def __init__(self, recorder, button_handler):
        super().__init__()

        self.recorder = recorder
        self.button_handler = button_handler
        self.player = get_player()
        self.sound_manager = get_sound_manager()

        # Sound-Buttons Cache
        self.sound_buttons: Dict[int, SoundButton] = {}

        # Aktuell spielender Sound
        self.current_playing_id = None

        self._setup_ui()
        self._load_sounds()
        self._setup_timers()
        self._connect_handlers()

        logger.info("NippelboardWindow initialisiert")

    def _setup_ui(self):
        """Setup UI"""
        # Fenstereigenschaften
        self.setWindowTitle("Nippelboard Funk 🎛️")

        window_width = config.get('gui.window_width', 1024)
        window_height = config.get('gui.window_height', 600)
        self.resize(window_width, window_height)

        # Fullscreen falls konfiguriert
        if config.get('gui.fullscreen', False):
            self.showFullScreen()

        # Hauptlayout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout()

        # Linke Seite: Status & Controls
        left_panel = QVBoxLayout()

        self.status_panel = StatusPanel()
        left_panel.addWidget(self.status_panel)

        self.control_panel = ControlPanel()
        left_panel.addWidget(self.control_panel)

        main_layout.addLayout(left_panel, 1)  # 1 Teil der Breite

        # Rechte Seite: Nippelboard (Scrollable)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #1a1a1a;
                border: none;
            }
        """)

        scroll_widget = QWidget()
        self.sound_grid = QGridLayout()
        self.sound_grid.setSpacing(10)
        scroll_widget.setLayout(self.sound_grid)

        scroll_area.setWidget(scroll_widget)

        main_layout.addWidget(scroll_area, 3)  # 3 Teile der Breite

        central_widget.setLayout(main_layout)

        # Dunkles Theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a1a;
            }
            QWidget {
                color: #ecf0f1;
            }
        """)

    def _load_sounds(self):
        """Lädt Sounds und erstellt Buttons"""
        # Lösche alte Buttons
        for button in self.sound_buttons.values():
            button.deleteLater()
        self.sound_buttons.clear()

        # Hole Sounds aus DB
        sounds = self.sound_manager.get_all_sounds()

        if not sounds:
            # Zeige Info
            no_sounds_label = QLabel("Keine Sounds vorhanden.\nFüge Sounds über '➕ Sound hinzufügen' hinzu.")
            no_sounds_label.setAlignment(Qt.AlignCenter)
            no_sounds_label.setStyleSheet("color: #95a5a6; font-size: 14px;")
            self.sound_grid.addWidget(no_sounds_label, 0, 0)
            return

        # Grid-Layout-Einstellungen
        columns = config.get('gui.grid_columns', 5)

        # Erstelle Buttons
        for idx, sound in enumerate(sounds):
            row = idx // columns
            col = idx % columns

            button = SoundButton(
                sound_id=sound.id,
                name=sound.name,
                icon_path=sound.icon_path
            )

            button.sound_clicked.connect(self._on_sound_clicked)

            self.sound_buttons[sound.id] = button
            self.sound_grid.addWidget(button, row, col)

        logger.info(f"{len(sounds)} Sound-Buttons geladen")

    def _setup_timers(self):
        """Setup Update-Timer"""
        # Status-Update Timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status)
        update_rate = config.get('performance.gui_update_rate', 100)
        self.status_timer.start(update_rate)

    def _connect_handlers(self):
        """Verbindet Event-Handler"""
        # Control-Panel Signals
        self.control_panel.clip_requested.connect(self._on_clip_requested)
        self.control_panel.panic_toggled.connect(self._on_panic_toggled)
        self.control_panel.add_sound_requested.connect(self._on_add_sound_requested)
        self.control_panel.settings_requested.connect(self._on_settings_requested)

        # GPIO-Button-Handler
        if self.button_handler:
            self.button_handler.on_clip_button = self._on_clip_button_pressed
            self.button_handler.on_panic_button = self._on_panic_button_pressed

        # Recorder Callbacks
        if self.recorder:
            self.recorder.on_clip_saved = self._on_clip_saved
            self.recorder.on_panic_saved = self._on_panic_saved

    def _update_status(self):
        """Aktualisiert Status-Anzeige"""
        if self.recorder:
            status = self.recorder.get_buffer_status()
            self.status_panel.update_status(status)

    def _on_sound_clicked(self, sound_id: int):
        """Sound-Button geklickt"""
        try:
            # Stoppe aktuellen Sound falls läuft
            if self.current_playing_id:
                old_button = self.sound_buttons.get(self.current_playing_id)
                if old_button:
                    old_button.set_playing(False)

            # Hole Sound
            sound = self.sound_manager.get_sound(sound_id)
            if not sound:
                logger.error(f"Sound {sound_id} nicht gefunden")
                return

            # Visuelles Feedback
            button = self.sound_buttons.get(sound_id)
            if button:
                button.set_playing(True)

            self.current_playing_id = sound_id

            # Spiele Sound
            logger.info(f"Spiele Sound: {sound.name}")
            self.player.play(sound.file_path, volume=sound.volume, blocking=False)

            # Aktualisiere DB
            from datetime import datetime
            sound.last_played = datetime.now()
            sound.play_count += 1
            sound.save()

            # Timer zum Zurücksetzen des Button-Status
            QTimer.singleShot(int(sound.duration * 1000) if sound.duration else 3000,
                            lambda: self._on_sound_finished(sound_id))

        except Exception as e:
            logger.error(f"Fehler beim Abspielen von Sound {sound_id}: {e}")
            QMessageBox.critical(self, "Fehler", f"Sound konnte nicht abgespielt werden:\n{e}")

    def _on_sound_finished(self, sound_id: int):
        """Sound fertig abgespielt"""
        button = self.sound_buttons.get(sound_id)
        if button:
            button.set_playing(False)

        if self.current_playing_id == sound_id:
            self.current_playing_id = None

    def _on_clip_requested(self):
        """Clip-Speicherung angefordert (via GUI)"""
        self._on_clip_button_pressed()

    def _on_clip_button_pressed(self):
        """Clip-Button gedrückt (GPIO oder GUI)"""
        try:
            logger.info("Speichere Clip...")
            QMessageBox.information(
                self,
                "Clip wird gespeichert",
                "Clip wird gespeichert: 45s vorher + 15s nachher.\nBitte warten..."
            )

            # Speichere Clip (läuft im Hintergrund)
            if self.recorder:
                self.recorder.save_clip()

        except Exception as e:
            logger.error(f"Fehler beim Speichern des Clips: {e}")
            QMessageBox.critical(self, "Fehler", f"Clip konnte nicht gespeichert werden:\n{e}")

    def _on_clip_saved(self, file_path: str):
        """Callback wenn Clip gespeichert wurde"""
        from pathlib import Path
        filename = Path(file_path).name

        logger.info(f"Clip gespeichert: {filename}")
        self.status_panel.update_last_clip(filename)

        QMessageBox.information(
            self,
            "Clip gespeichert",
            f"Clip erfolgreich gespeichert:\n{filename}"
        )

    def _on_panic_toggled(self, active: bool):
        """Panik-Button getoggled (GUI)"""
        self._on_panic_button_pressed(active)

    def _on_panic_button_pressed(self, active: bool):
        """Panik-Button gedrückt"""
        try:
            if active:
                # Starte Panik-Modus
                logger.warning("Starte Panik-Modus")
                if self.recorder:
                    self.recorder.start_panic_mode()

                QMessageBox.warning(
                    self,
                    "⚠️ Panik-Modus",
                    "Panik-Modus gestartet!\nKomplette Aufnahme läuft.\nDrücke erneut zum Stoppen."
                )

            else:
                # Stoppe Panik-Modus
                logger.warning("Stoppe Panik-Modus")
                if self.recorder:
                    file_path = self.recorder.stop_panic_mode()

                    if file_path:
                        QMessageBox.information(
                            self,
                            "Panik-Modus gestoppt",
                            f"Aufnahme verschlüsselt gespeichert:\n{Path(file_path).name}"
                        )
                    else:
                        QMessageBox.critical(
                            self,
                            "Fehler",
                            "Fehler beim Speichern der Panik-Aufnahme!"
                        )

            # Update Control-Panel
            self.control_panel.set_panic_active(active)

        except Exception as e:
            logger.error(f"Fehler im Panik-Modus: {e}")
            QMessageBox.critical(self, "Fehler", f"Panik-Modus-Fehler:\n{e}")

    def _on_panic_saved(self, file_path: str):
        """Callback wenn Panik-Aufnahme gespeichert"""
        logger.info(f"Panik-Aufnahme gespeichert: {file_path}")

    def _on_add_sound_requested(self):
        """Sound hinzufügen angefordert"""
        from pathlib import Path

        # Dialog: Datei oder URL?
        choice, ok = QInputDialog.getItem(
            self,
            "Sound hinzufügen",
            "Sound-Quelle:",
            ["Datei auswählen", "Von URL herunterladen"],
            0,
            False
        )

        if not ok:
            return

        if choice == "Datei auswählen":
            self._add_sound_from_file()
        else:
            self._add_sound_from_url()

    def _add_sound_from_file(self):
        """Sound aus Datei hinzufügen"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Sound-Datei auswählen",
            "",
            "Audio Files (*.mp3 *.ogg *.wav *.flac *.m4a);;All Files (*)"
        )

        if not file_path:
            return

        # Name eingeben
        name, ok = QInputDialog.getText(
            self,
            "Sound-Name",
            "Name für den Sound:"
        )

        if not ok or not name:
            return

        # Optional: Icon
        icon_path, _ = QFileDialog.getOpenFileName(
            self,
            "Icon auswählen (optional)",
            "",
            "Image Files (*.png *.jpg *.jpeg *.gif);;All Files (*)"
        )

        # Füge hinzu
        try:
            sound = self.sound_manager.add_sound_from_file(
                name=name,
                source_path=file_path,
                icon_path=icon_path if icon_path else None
            )

            if sound:
                QMessageBox.information(self, "Erfolg", f"Sound '{name}' hinzugefügt!")
                self._load_sounds()  # Reload
            else:
                QMessageBox.critical(self, "Fehler", "Sound konnte nicht hinzugefügt werden!")

        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen: {e}")
            QMessageBox.critical(self, "Fehler", str(e))

    def _add_sound_from_url(self):
        """Sound von URL herunterladen"""
        url, ok = QInputDialog.getText(
            self,
            "Sound-URL",
            "URL zur Sound-Datei:"
        )

        if not ok or not url:
            return

        name, ok = QInputDialog.getText(
            self,
            "Sound-Name",
            "Name für den Sound:"
        )

        if not ok or not name:
            return

        # Download
        try:
            QMessageBox.information(
                self,
                "Download",
                "Sound wird heruntergeladen...\nBitte warten."
            )

            sound = self.sound_manager.add_sound_from_url(
                name=name,
                url=url
            )

            if sound:
                QMessageBox.information(self, "Erfolg", f"Sound '{name}' heruntergeladen!")
                self._load_sounds()
            else:
                QMessageBox.critical(self, "Fehler", "Download fehlgeschlagen!")

        except Exception as e:
            logger.error(f"Fehler beim Download: {e}")
            QMessageBox.critical(self, "Fehler", str(e))

    def _on_settings_requested(self):
        """Einstellungen öffnen"""
        QMessageBox.information(
            self,
            "Einstellungen",
            "Einstellungen-Dialog noch nicht implementiert.\n"
            "Bearbeite config.yaml manuell."
        )

    def closeEvent(self, event):
        """Fenster wird geschlossen"""
        reply = QMessageBox.question(
            self,
            "Beenden",
            "Nippelboard beenden?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Cleanup
            self.status_timer.stop()

            if self.recorder:
                self.recorder.stop()

            if self.button_handler:
                self.button_handler.cleanup()

            event.accept()
        else:
            event.ignore()
