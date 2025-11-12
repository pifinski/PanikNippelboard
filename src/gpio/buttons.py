"""
GPIO-Handler für Buttons (Clip & Panik)
Verwendet RPi.GPIO für Raspberry Pi
"""

import logging
import time
from typing import Callable, Optional

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    GPIO_AVAILABLE = False
    logging.warning("RPi.GPIO nicht verfügbar. GPIO-Funktionen deaktiviert.")

from ..utils.config import config

logger = logging.getLogger(__name__)


class ButtonHandler:
    """
    Handler für GPIO-Buttons

    Features:
    - Clip-Button: Speichert 45s vorher + 15s nachher
    - Panik-Button: Toggle für kontinuierliche Aufnahme
    - Debouncing
    - Callbacks
    """

    def __init__(self):
        if not GPIO_AVAILABLE:
            logger.error("GPIO nicht verfügbar! Läuft auf Raspberry Pi?")
            self.enabled = False
            return

        self.enabled = True

        # Konfiguration
        self.clip_button_pin = config.get('gpio.clip_button_pin', 17)
        self.panic_button_pin = config.get('gpio.panic_button_pin', 27)
        self.pull_up_down = config.get('gpio.pull_up_down', 'up')
        self.debounce_ms = config.get('gpio.debounce_ms', 300)
        self.edge_detection = config.get('gpio.edge_detection', 'falling')

        # Callbacks
        self.on_clip_button: Optional[Callable] = None
        self.on_panic_button: Optional[Callable] = None

        # Status
        self.panic_mode_active = False
        self.last_clip_time = 0
        self.last_panic_time = 0

        # GPIO Setup
        self._setup_gpio()

        logger.info(
            f"ButtonHandler initialisiert (Clip={self.clip_button_pin}, "
            f"Panik={self.panic_button_pin})"
        )

    def _setup_gpio(self):
        """Initialisiert GPIO-Pins"""
        try:
            # Setze Modus (BCM Nummerierung)
            GPIO.setmode(GPIO.BCM)

            # Warnungen deaktivieren bei bereits verwendeten Pins
            GPIO.setwarnings(False)

            # Pull-Up/Down
            if self.pull_up_down == 'up':
                pud = GPIO.PUD_UP
            elif self.pull_up_down == 'down':
                pud = GPIO.PUD_DOWN
            else:
                pud = GPIO.PUD_OFF

            # Edge-Detection
            if self.edge_detection == 'rising':
                edge = GPIO.RISING
            elif self.edge_detection == 'falling':
                edge = GPIO.FALLING
            else:
                edge = GPIO.BOTH

            # Setup Clip-Button
            GPIO.setup(self.clip_button_pin, GPIO.IN, pull_up_down=pud)
            GPIO.add_event_detect(
                self.clip_button_pin,
                edge,
                callback=self._clip_button_callback,
                bouncetime=self.debounce_ms
            )
            logger.info(f"Clip-Button konfiguriert auf GPIO {self.clip_button_pin}")

            # Setup Panik-Button
            GPIO.setup(self.panic_button_pin, GPIO.IN, pull_up_down=pud)
            GPIO.add_event_detect(
                self.panic_button_pin,
                edge,
                callback=self._panic_button_callback,
                bouncetime=self.debounce_ms
            )
            logger.info(f"Panik-Button konfiguriert auf GPIO {self.panic_button_pin}")

        except Exception as e:
            logger.error(f"Fehler beim GPIO-Setup: {e}")
            self.enabled = False

    def _clip_button_callback(self, channel):
        """Callback für Clip-Button"""
        current_time = time.time()

        # Zusätzliches Software-Debouncing
        if current_time - self.last_clip_time < (self.debounce_ms / 1000.0):
            return

        self.last_clip_time = current_time

        logger.info("CLIP-BUTTON GEDRÜCKT")

        # Rufe Callback auf
        if self.on_clip_button:
            try:
                self.on_clip_button()
            except Exception as e:
                logger.error(f"Fehler im Clip-Button-Callback: {e}")

    def _panic_button_callback(self, channel):
        """Callback für Panik-Button (Toggle)"""
        current_time = time.time()

        # Software-Debouncing
        if current_time - self.last_panic_time < (self.debounce_ms / 1000.0):
            return

        self.last_panic_time = current_time

        # Toggle Panik-Modus
        self.panic_mode_active = not self.panic_mode_active

        if self.panic_mode_active:
            logger.warning("PANIK-BUTTON GEDRÜCKT - MODUS GESTARTET")
        else:
            logger.warning("PANIK-BUTTON GEDRÜCKT - MODUS GESTOPPT")

        # Rufe Callback auf
        if self.on_panic_button:
            try:
                self.on_panic_button(self.panic_mode_active)
            except Exception as e:
                logger.error(f"Fehler im Panik-Button-Callback: {e}")

    def cleanup(self):
        """Cleanup GPIO"""
        if self.enabled:
            try:
                GPIO.cleanup()
                logger.info("GPIO aufgeräumt")
            except Exception as e:
                logger.error(f"Fehler beim GPIO-Cleanup: {e}")

    def __del__(self):
        """Destruktor"""
        self.cleanup()


class MockButtonHandler:
    """
    Mock-Handler für Entwicklung ohne Raspberry Pi
    Simuliert GPIO-Buttons über Tastatur-Eingaben
    """

    def __init__(self):
        self.enabled = True
        self.panic_mode_active = False
        self.on_clip_button: Optional[Callable] = None
        self.on_panic_button: Optional[Callable] = None

        logger.warning("MockButtonHandler aktiv (keine echten GPIO-Pins)")

    def simulate_clip_button(self):
        """Simuliert Clip-Button-Druck"""
        logger.info("MOCK: Clip-Button gedrückt")
        if self.on_clip_button:
            self.on_clip_button()

    def simulate_panic_button(self):
        """Simuliert Panik-Button-Druck"""
        self.panic_mode_active = not self.panic_mode_active
        logger.warning(f"MOCK: Panik-Button gedrückt (Modus: {self.panic_mode_active})")
        if self.on_panic_button:
            self.on_panic_button(self.panic_mode_active)

    def cleanup(self):
        """Dummy cleanup"""
        pass


# Factory-Funktion
def create_button_handler() -> ButtonHandler:
    """
    Erstellt ButtonHandler (echt oder Mock)

    Returns:
        ButtonHandler oder MockButtonHandler je nach Verfügbarkeit
    """
    if GPIO_AVAILABLE:
        return ButtonHandler()
    else:
        return MockButtonHandler()
