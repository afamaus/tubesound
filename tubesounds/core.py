"""Download-Kern: lädt die Tonspur eines Videos und wandelt sie ins gewünschte Format."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import imageio_ffmpeg
import yt_dlp
from yt_dlp.postprocessor import FFmpegExtractAudioPP, get_postprocessor

FORMATS = ("mp3", "m4a", "wav")
BITRATES = (128, 192, 256, 320)  # kbit/s, gilt für MP3 und M4A
SAMPLE_RATES = (0, 44100, 48000)  # 0 = wie im Original


@dataclass
class AudioOptions:
    """Einstellungen für die Umwandlung."""

    bitrate: int = 192
    sample_rate: int = 0
    mono: bool = False
    embed_metadata: bool = True


@dataclass
class Progress:
    """Fortschrittsmeldung für die Oberfläche."""

    stage: str  # "download", "convert" oder "done"
    percent: Optional[float] = None
    filename: Optional[str] = None


ProgressCallback = Callable[[Progress], None]


class ReencodeAudioPP(FFmpegExtractAudioPP):
    """Wie FFmpegExtractAudio, wandelt aber immer um.

    yt-dlp kopiert sonst passende Quellen (z. B. AAC nach M4A) unverändert,
    und Bitrate, Abtastrate und Kanäle aus den Einstellungen würden ignoriert.
    """

    @classmethod
    def pp_key(cls):
        return "ExtractAudio"  # wie das Original, damit postprocessor_args["extractaudio"] greift

    def get_audio_codec(self, path):
        codec = super().get_audio_codec(path)
        return codec and f"{codec}-reencode"


class DownloadError(Exception):
    """Wird geworfen, wenn ein Download fehlschlägt."""


def default_output_dir() -> Path:
    """Standard-Zielordner: der Downloads-Ordner des Benutzers."""
    downloads = Path.home() / "Downloads"
    return downloads if downloads.is_dir() else Path.home()


def build_options(
    fmt: str,
    output_dir: Path,
    hook: Optional[Callable] = None,
    audio: Optional[AudioOptions] = None,
) -> dict:
    """Erzeugt die yt-dlp-Optionen für das gewählte Audioformat."""
    fmt = fmt.lower()
    if fmt not in FORMATS:
        raise ValueError(f"Unbekanntes Format: {fmt} (erlaubt: {', '.join(FORMATS)})")
    audio = audio or AudioOptions()

    postprocessors = [{"key": "FFmpegExtractAudio", "preferredcodec": fmt}]
    if fmt != "wav":
        postprocessors[0]["preferredquality"] = str(audio.bitrate)
    if audio.embed_metadata:
        postprocessors.append({"key": "FFmpegMetadata", "add_metadata": True})

    ffmpeg_args = []
    if audio.sample_rate:
        ffmpeg_args += ["-ar", str(audio.sample_rate)]
    if audio.mono:
        ffmpeg_args += ["-ac", "1"]

    options = {
        "format": "bestaudio/best",
        "outtmpl": str(output_dir / "%(title)s.%(ext)s"),
        "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),
        "postprocessors": postprocessors,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
    }
    if ffmpeg_args:
        options["postprocessor_args"] = {"extractaudio": ffmpeg_args}
    if hook:
        options["progress_hooks"] = [hook]
    return options


def download_audio(
    url: str,
    fmt: str = "mp3",
    output_dir: Optional[Path] = None,
    on_progress: Optional[ProgressCallback] = None,
    audio: Optional[AudioOptions] = None,
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
        options = build_options(fmt, output_dir, hook, audio)
        postprocessors = options.pop("postprocessors")
        with yt_dlp.YoutubeDL(options) as ydl:
            for pp in postprocessors:
                pp = dict(pp)
                key = pp.pop("key")
                cls = ReencodeAudioPP if key == "FFmpegExtractAudio" else get_postprocessor(key)
                ydl.add_post_processor(cls(ydl, **pp))
            info = ydl.extract_info(url, download=True)
            source = Path(ydl.prepare_filename(info))
    except yt_dlp.utils.DownloadError as exc:
        raise DownloadError(str(exc)) from exc

    result = source.with_suffix(f".{fmt.lower()}")
    if on_progress:
        on_progress(Progress("done", 100.0, str(result)))
    return result
