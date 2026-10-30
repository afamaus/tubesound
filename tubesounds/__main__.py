"""Einstieg: ohne Argumente startet die Oberfläche, sonst
python -m tubesounds <link> [-f mp3|m4a|wav] [-o ordner]"""

import argparse
import sys
from pathlib import Path

from .core import FORMATS, DownloadError, Progress, download_audio


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        from .gui import run

        run()
        return 0

    parser = argparse.ArgumentParser(prog="tubesounds", description=__doc__)
    parser.add_argument("url", help="Link zum YouTube-Video")
    parser.add_argument("-f", "--format", choices=FORMATS, default="mp3")
    parser.add_argument("-o", "--output", type=Path, help="Zielordner (Standard: Downloads)")
    args = parser.parse_args(argv)

    def show(p: Progress) -> None:
        if p.stage == "download" and p.percent is not None:
            print(f"\rLade herunter: {p.percent:5.1f} %", end="", flush=True)
        elif p.stage == "convert":
            print("\nWandle um ...", flush=True)

    try:
        path = download_audio(args.url, args.format, args.output, show)
    except DownloadError as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1
    print(f"Fertig: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
