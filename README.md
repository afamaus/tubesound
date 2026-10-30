# TubeSounds

Einfacher, portabler Downloader, der die Tonspur von YouTube-Videos als **MP3**, **M4A** oder **WAV** speichert.

## Stand

- [x] Schritt 1: Download-Kern (yt-dlp + mitgeliefertes ffmpeg)
- [x] Schritt 2: Oberfläche im Matrix-Look
- [x] Schritt 3: Portable Builds für Windows, macOS und Linux

## Portable Version

Unter [Releases](../../releases) gibt es fertige Dateien, die ohne Installation starten:

| System  | Datei | Hinweis |
|---------|-------|---------|
| Windows | `TubeSounds-windows.exe` | SmartScreen warnt beim ersten Start: *Weitere Informationen → Trotzdem ausführen* |
| macOS (Apple Silicon) | `TubeSounds-macos.zip` | Entpacken, dann *Rechtsklick → Öffnen*, weil die App nicht signiert ist |
| Linux   | `TubeSounds-linux` | `chmod +x TubeSounds-linux` und starten |

Eine neue Version entsteht, sobald ein Tag wie `v0.1.0` gepusht wird:

```bash
git tag v0.1.0 && git push origin v0.1.0
```

Bei jedem Pull Request baut GitHub Actions die Dateien ebenfalls. Sie liegen dann unter *Actions → Artifacts*.
Wenn YouTube Downloads blockiert, reicht meist ein neuer Tag: Der Build holt automatisch die aktuelle yt-dlp-Version.

## Aus dem Quellcode starten

```bash
pip install -r requirements.txt
python -m tubesounds
```

Ohne Argumente öffnet sich das Fenster im Matrix-Look: Link einfügen (Strg+V oder Rechtsklick), Format wählen, *Download* klicken oder Enter drücken.
Die Datei landet im Downloads-Ordner. Unter Linux wird für die Oberfläche Tkinter benötigt (`sudo apt install python3-tk`).

### Kommandozeile

```bash
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
