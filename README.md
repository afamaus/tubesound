# TubeSounds

Einfacher, portabler Downloader, der die Tonspur von YouTube-Videos als **MP3**, **M4A** oder **WAV** speichert.

## Stand

- [x] Schritt 1: Download-Kern (yt-dlp + mitgeliefertes ffmpeg)
- [ ] Schritt 2: Oberfläche im Matrix-Look
- [ ] Schritt 3: Portable Builds für Windows, macOS und Linux

## Ausprobieren (Kommandozeile)

```bash
pip install -r requirements.txt
python -m tubesounds "https://www.youtube.com/watch?v=..." -f mp3
```

Optionen: `-f mp3|m4a|wav` (Standard: mp3), `-o ORDNER` (Standard: Downloads-Ordner).
ffmpeg wird über `imageio-ffmpeg` mitgeliefert und muss nicht separat installiert werden.

## Tests

```bash
pip install pytest
python -m pytest
```

## Hinweis

Die Nutzungsbedingungen von YouTube erlauben das Herunterladen nur für eigene oder frei lizenzierte Inhalte.
