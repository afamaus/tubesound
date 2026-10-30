"""Einstellungen, portabel in tubesounds.json neben dem Programm gespeichert."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Optional

from .core import BITRATES, FORMATS, SAMPLE_RATES, AudioOptions, default_output_dir

FILENAME = "tubesounds.json"


@dataclass
class Settings:
    output_dir: str = ""  # leer = Downloads-Ordner
    format: str = "mp3"
    bitrate: int = 192
    sample_rate: int = 0
    mono: bool = False
    embed_metadata: bool = True
    disclaimer_accepted: str = ""  # Version des akzeptierten Haftungsausschlusses

    def audio(self) -> AudioOptions:
        return AudioOptions(self.bitrate, self.sample_rate, self.mono, self.embed_metadata)

    def target_dir(self) -> Path:
        return Path(self.output_dir) if self.output_dir else default_output_dir()

    def validate(self) -> "Settings":
        """Setzt ungültige Werte (z. B. von Hand bearbeitete Datei) auf den Standard zurück."""
        default = Settings()
        if self.format not in FORMATS:
            self.format = default.format
        if self.bitrate not in BITRATES:
            self.bitrate = default.bitrate
        if self.sample_rate not in SAMPLE_RATES:
            self.sample_rate = default.sample_rate
        return self


def program_dir() -> Path:
    """Ordner, in dem das Programm liegt (bei macOS-Apps der Ordner neben der .app)."""
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        for parent in exe.parents:
            if parent.suffix == ".app":
                return parent.parent
        return exe.parent
    return Path.cwd()


def settings_path() -> Path:
    """Neben dem Programm, sonst (schreibgeschützter Ordner) im Benutzerordner."""
    portable = program_dir() / FILENAME
    if portable.exists() or os.access(portable.parent, os.W_OK):
        return portable
    return Path.home() / f".{FILENAME}"


def load(path: Optional[Path] = None) -> Settings:
    path = path or settings_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Settings()
    known = {f.name for f in fields(Settings)}
    try:
        return Settings(**{k: v for k, v in data.items() if k in known}).validate()
    except TypeError:
        return Settings()


def save(settings: Settings, path: Optional[Path] = None) -> None:
    path = path or settings_path()
    path.write_text(json.dumps(asdict(settings), indent=2, ensure_ascii=False), encoding="utf-8")
