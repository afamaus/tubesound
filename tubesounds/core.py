"""Download-Kern: lädt die Tonspur eines Videos und wandelt sie ins gewünschte Format."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import imageio_ffmpeg
import yt_dlp

FORMATS = ("mp3", "m4a", "wav")


@dataclass
class Progress:
    """Fortschrittsmeldung für die Oberfläche."""

    stage: str  # "download", "convert" oder "done"
    percent: Optional[float] = None
    filename: Optional[str] = None


ProgressCallback = Callable[[Progress], None]


class DownloadError(Exception):
    """Wird geworfen, wenn ein Download fehlschlägt."""


def default_output_dir() -> Path:
    """Standard-Zielordner: der Downloads-Ordner des Benutzers."""
    downloads = Path.home() / "Downloads"
    return downloads if downloads.is_dir() else Path.home()


def build_options(fmt: str, output_dir: Path, hook: Optional[Callable] = None) -> dict:
    """Erzeugt die yt-dlp-Optionen für das gewählte Audioformat."""
    fmt = fmt.lower()
    if fmt not in FORMATS:
        raise ValueError(f"Unbekanntes Format: {fmt} (erlaubt: {', '.join(FORMATS)})")

    postprocessor = {"key": "FFmpegExtractAudio", "preferredcodec": fmt}
    if fmt == "mp3":
        postprocessor["preferredquality"] = "192"

    options = {
        "format": "bestaudio/best",
        "outtmpl": str(output_dir / "%(title)s.%(ext)s"),
        "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),
        "postprocessors": [postprocessor],
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
    }
    if hook:
        options["progress_hooks"] = [hook]
    return options


def download_audio(
    url: str,
    fmt: str = "mp3",
    output_dir: Optional[Path] = None,
    on_progress: Optional[ProgressCallback] = None,
) -> Path:
    """Lädt die Tonspur von `url` herunter und gibt den Pfad der fertigen Datei zurück."""
    url = url.strip()
    if not url:
        raise DownloadError("Bitte einen Link eingeben.")
    output_dir = Path(output_dir) if output_dir else default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    def hook(d: dict) -> None:
        if not on_progress:
            return
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            percent = d.get("downloaded_bytes", 0) * 100 / total if total else None
            on_progress(Progress("download", percent, d.get("filename")))
        elif d["status"] == "finished":
            on_progress(Progress("convert", 100.0, d.get("filename")))

    try:
        with yt_dlp.YoutubeDL(build_options(fmt, output_dir, hook)) as ydl:
            info = ydl.extract_info(url, download=True)
            source = Path(ydl.prepare_filename(info))
    except yt_dlp.utils.DownloadError as exc:
        raise DownloadError(str(exc)) from exc

    result = source.with_suffix(f".{fmt.lower()}")
    if on_progress:
        on_progress(Progress("done", 100.0, str(result)))
    return result
