"""
Datenbank-Schema für Nippelboard Funk
Verwendet Peewee ORM mit SQLite
"""

import logging
from datetime import datetime
from pathlib import Path
from peewee import *

from .config import config

logger = logging.getLogger(__name__)

# Datenbank-Instanz
db_path = config.get('storage.database', './data/nippelboard.db')
db = SqliteDatabase(db_path, pragmas={
    'journal_mode': 'wal',  # Write-Ahead Logging für bessere Performance
    'cache_size': -1024 * 64,  # 64MB Cache
    'foreign_keys': 1,
    'ignore_check_constraints': 0,
    'synchronous': 'NORMAL'
})


class BaseModel(Model):
    """Basis-Modell für alle Tabellen"""

    class Meta:
        database = db


class NippelSound(BaseModel):
    """Tabelle für Nippel-Sounds im Soundboard"""

    id = AutoField()
    name = CharField(max_length=100, unique=True)  # Anzeigename
    file_path = CharField(max_length=500)  # Pfad zur Audio-Datei
    icon_path = CharField(max_length=500, null=True)  # Pfad zum Icon/Bild
    position = IntegerField(default=0)  # Position im Grid (für Sortierung)
    duration = FloatField(null=True)  # Länge in Sekunden
    volume = FloatField(default=1.0)  # Lautstärke (0.0 - 1.0)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)
    last_played = DateTimeField(null=True)  # Wann zuletzt abgespielt
    play_count = IntegerField(default=0)  # Wie oft abgespielt

    class Meta:
        table_name = 'nippel_sounds'
        indexes = (
            (('position',), False),  # Index für schnelle Sortierung
        )

    def __str__(self):
        return f"NippelSound(name={self.name}, position={self.position})"


class Recording(BaseModel):
    """Tabelle für Funk-Aufnahmen (Clips und Panik)"""

    id = AutoField()
    filename = CharField(max_length=255, unique=True)
    file_path = CharField(max_length=500)
    recording_type = CharField(max_length=20)  # 'clip' oder 'panic'
    duration = FloatField(null=True)  # Länge in Sekunden
    file_size = IntegerField(null=True)  # Größe in Bytes
    is_encrypted = BooleanField(default=False)  # Verschlüsselt?
    created_at = DateTimeField(default=datetime.now)
    notes = TextField(null=True)  # Optionale Notizen

    class Meta:
        table_name = 'recordings'
        indexes = (
            (('created_at',), False),  # Index für chronologische Abfragen
            (('recording_type',), False),
        )

    def __str__(self):
        return f"Recording(filename={self.filename}, type={self.recording_type})"


class SystemState(BaseModel):
    """Tabelle für System-Status (z.B. ob Panik-Modus aktiv)"""

    id = AutoField()
    key = CharField(max_length=100, unique=True)
    value = CharField(max_length=500)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'system_state'

    def __str__(self):
        return f"SystemState(key={self.key}, value={self.value})"


class Settings(BaseModel):
    """Tabelle für persistente Einstellungen"""

    id = AutoField()
    category = CharField(max_length=50)  # z.B. 'gui', 'audio'
    key = CharField(max_length=100)
    value = TextField()  # JSON oder String
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'settings'
        indexes = (
            (('category', 'key'), True),  # Unique constraint
        )

    def __str__(self):
        return f"Settings(category={self.category}, key={self.key})"


def init_database():
    """Initialisiert die Datenbank und erstellt Tabellen"""
    try:
        db.connect()
        db.create_tables([
            NippelSound,
            Recording,
            SystemState,
            Settings
        ], safe=True)

        logger.info(f"Datenbank initialisiert: {db_path}")

        # Erstelle Default-Einträge
        _create_defaults()

    except Exception as e:
        logger.error(f"Fehler bei Datenbank-Initialisierung: {e}")
        raise


def _create_defaults():
    """Erstellt Standard-Einträge falls nicht vorhanden"""

    # System-Status: Panik-Modus
    SystemState.get_or_create(
        key='panic_mode_active',
        defaults={'value': 'false'}
    )

    # System-Status: Letzte Aufnahme
    SystemState.get_or_create(
        key='last_recording_path',
        defaults={'value': ''}
    )


def close_database():
    """Schließt Datenbankverbindung"""
    if not db.is_closed():
        db.close()
        logger.info("Datenbank geschlossen")


# Context Manager für Transaktionen
def db_transaction():
    """Context Manager für sichere Datenbank-Transaktionen"""
    return db.atomic()


# Utility-Funktionen

def get_all_sounds_sorted():
    """Holt alle Sounds sortiert nach Position"""
    return NippelSound.select().order_by(NippelSound.position)


def get_sound_by_name(name: str):
    """Holt Sound nach Name"""
    try:
        return NippelSound.get(NippelSound.name == name)
    except DoesNotExist:
        return None


def add_sound(name: str, file_path: str, icon_path: str = None, position: int = None):
    """Fügt neuen Sound hinzu"""
    if position is None:
        # Setze Position als nächste freie Nummer
        max_pos = NippelSound.select(fn.MAX(NippelSound.position)).scalar() or 0
        position = max_pos + 1

    return NippelSound.create(
        name=name,
        file_path=file_path,
        icon_path=icon_path,
        position=position
    )


def update_sound_position(sound_id: int, new_position: int):
    """Aktualisiert Sound-Position (für Drag & Drop)"""
    sound = NippelSound.get_by_id(sound_id)
    sound.position = new_position
    sound.updated_at = datetime.now()
    sound.save()


def add_recording(filename: str, file_path: str, recording_type: str,
                  duration: float = None, file_size: int = None,
                  is_encrypted: bool = False):
    """Fügt neue Aufnahme hinzu"""
    return Recording.create(
        filename=filename,
        file_path=file_path,
        recording_type=recording_type,
        duration=duration,
        file_size=file_size,
        is_encrypted=is_encrypted
    )


def get_recordings_by_type(recording_type: str):
    """Holt alle Aufnahmen eines Typs"""
    return Recording.select().where(
        Recording.recording_type == recording_type
    ).order_by(Recording.created_at.desc())


def get_system_state(key: str, default: str = None):
    """Holt System-Status"""
    try:
        state = SystemState.get(SystemState.key == key)
        return state.value
    except DoesNotExist:
        return default


def set_system_state(key: str, value: str):
    """Setzt System-Status"""
    state, created = SystemState.get_or_create(key=key)
    state.value = value
    state.updated_at = datetime.now()
    state.save()
    return state


def cleanup_old_recordings(max_size_gb: float):
    """
    Löscht alte Aufnahmen wenn Speicherlimit überschritten

    Args:
        max_size_gb: Maximale Größe in GB
    """
    # Berechne aktuelle Größe
    total_size = Recording.select(fn.SUM(Recording.file_size)).scalar() or 0
    max_size_bytes = max_size_gb * 1024 * 1024 * 1024

    if total_size <= max_size_bytes:
        return

    # Lösche älteste Clips (nicht Panik-Aufnahmen!)
    logger.warning(f"Speicherlimit überschritten ({total_size / 1e9:.2f} GB). Lösche alte Clips...")

    old_clips = Recording.select().where(
        Recording.recording_type == 'clip'
    ).order_by(Recording.created_at.asc())

    for clip in old_clips:
        # Lösche Datei
        try:
            Path(clip.file_path).unlink(missing_ok=True)
            clip.delete_instance()
            logger.info(f"Clip gelöscht: {clip.filename}")

            # Prüfe ob Limit erreicht
            total_size -= clip.file_size or 0
            if total_size <= max_size_bytes:
                break
        except Exception as e:
            logger.error(f"Fehler beim Löschen von {clip.filename}: {e}")
