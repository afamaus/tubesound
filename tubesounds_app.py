"""Startskript für die portablen Builds (PyInstaller)."""

import os
import sys

# Fensterbuilds unter Windows haben keine Konsole: stdout/stderr sind dann None,
# was yt-dlp beim Schreiben von Meldungen abstürzen ließe.
for name in ("stdout", "stderr"):
    if getattr(sys, name) is None:
        setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))

from tubesounds.__main__ import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
