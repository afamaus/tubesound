"""Oberfläche im Matrix-Look: Linkfeld, Formatwahl, Download-Button und Digital Rain."""

from __future__ import annotations

import queue
import random
import threading
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path

from . import __version__
from .core import FORMATS, DownloadError, Progress, default_output_dir, download_audio

BANNER = Path(__file__).parent / "assets" / "banner.png"

BLACK = "#000000"
PANEL = "#020a02"
GREEN = "#00ff41"
GREEN_MID = "#00b32d"
GREEN_DIM = "#005f17"
HEAD = "#d6ffd9"
ERROR = "#ff3b3b"

RAIN_CHARS = "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ0123456789"
RAIN_STEP = 16  # Pixel zwischen Spalten und Zeilen
RAIN_TRAIL = 14  # Länge der Spur hinter dem Kopf
RAIN_TICK_MS = 70
# Farbverlauf der Spur: vom hellen Kopf bis fast schwarz
RAIN_COLORS = [HEAD, GREEN, GREEN, GREEN_MID, GREEN_MID] + [
    f"#00{g:02x}{g // 4:02x}" for g in range(140, 10, -130 // (RAIN_TRAIL - 4))
]

BAR_WIDTH = 24


def pick_font(root: tk.Tk) -> str:
    """Erste vorhandene Monospace-Schrift."""
    available = set(tkfont.families(root))
    for name in ("Consolas", "Menlo", "DejaVu Sans Mono", "Liberation Mono", "Courier New"):
        if name in available:
            return name
    return "Courier"


def progress_bar(percent: float) -> str:
    filled = int(BAR_WIDTH * percent / 100)
    return "[" + "█" * filled + "░" * (BAR_WIDTH - filled) + f"] {percent:5.1f} %"


class DigitalRain:
    """Fallende Zeichen im Hintergrund einer Canvas."""

    def __init__(self, canvas: tk.Canvas, font: tuple):
        self.canvas = canvas
        self.font = font
        self.columns: list[dict] = []
        self.canvas.bind("<Configure>", self._layout, add="+")

    def _layout(self, _event=None) -> None:
        width = self.canvas.winfo_width()
        count = max(1, width // RAIN_STEP)
        while len(self.columns) < count:
            self.columns.append(self._new_column(len(self.columns), initial=True))
        for column in self.columns[count:]:
            for item in filter(None, column["items"]):
                self.canvas.delete(item)
        del self.columns[count:]

    def _new_column(self, index: int, initial: bool = False) -> dict:
        rows = max(1, self.canvas.winfo_height() // RAIN_STEP)
        start = random.randint(-rows, rows) if initial else random.randint(-rows // 2, 0)
        return {"x": index * RAIN_STEP + RAIN_STEP // 2, "row": start,
                "speed": random.choice((1, 1, 1, 2)), "tick": 0, "items": []}

    def step(self) -> None:
        height = self.canvas.winfo_height()
        for i, column in enumerate(self.columns):
            column["tick"] += 1
            if column["tick"] % column["speed"]:
                continue
            column["row"] += 1
            y = column["row"] * RAIN_STEP
            item = None  # außerhalb des Fensters: Platzhalter, damit die Spur weiter altert
            if 0 <= y <= height:
                item = self.canvas.create_text(column["x"], y, text=random.choice(RAIN_CHARS),
                                               fill=HEAD, font=self.font, tags="rain")
            column["items"].insert(0, item)
            # Spur einfärben und alte Zeichen entfernen
            for age, item in enumerate(column["items"]):
                if item is None:
                    continue
                if age >= len(RAIN_COLORS):
                    self.canvas.delete(item)
                else:
                    self.canvas.itemconfigure(item, fill=RAIN_COLORS[age])
                    if age and random.random() < 0.03:
                        self.canvas.itemconfigure(item, text=random.choice(RAIN_CHARS))
            del column["items"][len(RAIN_COLORS):]
            if y > height and not any(column["items"]):
                self.columns[i] = self._new_column(i)
        self.canvas.tag_lower("rain")


class TubeSoundsApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.events: queue.Queue = queue.Queue()
        self.busy = False

        family = pick_font(root)
        self.font = (family, 11)
        self.font_bold = (family, 11, "bold")
        self.font_title = (family, 26, "bold")
        self.font_rain = (family, 11)

        root.title("TubeSounds")
        root.configure(bg=BLACK)
        root.geometry("760x760")
        root.minsize(640, 700)

        self.canvas = tk.Canvas(root, bg=BLACK, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.rain = DigitalRain(self.canvas, self.font_rain)

        self.panel = self._build_panel()
        self.panel_window = self.canvas.create_window(0, 0, window=self.panel)
        self.canvas.bind("<Configure>", self._center_panel, add="+")

        root.bind("<Return>", lambda _e: self.start_download())
        self.url_entry.focus_set()
        self._animate()
        self._poll_events()

    # ---------- Aufbau ----------

    def _build_panel(self) -> tk.Frame:
        panel = tk.Frame(self.canvas, bg=PANEL, highlightbackground=GREEN,
                         highlightcolor=GREEN, highlightthickness=1, padx=24, pady=18)

        try:
            self.banner = tk.PhotoImage(file=str(BANNER))
            tk.Label(panel, image=self.banner, bg=PANEL, bd=0).grid(row=0, column=0,
                                                                   columnspan=2)
        except tk.TclError:  # Bild fehlt: Schriftzug als Ersatz
            tk.Label(panel, text="T U B E S O U N D S", font=self.font_title,
                     fg=GREEN, bg=PANEL).grid(row=0, column=0, columnspan=2, sticky="w")
        tk.Label(panel, text=f"// audio extraction protocol v{__version__}", font=self.font,
                 fg=GREEN_MID, bg=PANEL).grid(row=1, column=0, columnspan=2, sticky="w",
                                              pady=(6, 14))

        tk.Label(panel, text="> LINK", font=self.font_bold, fg=GREEN,
                 bg=PANEL).grid(row=2, column=0, columnspan=2, sticky="w")
        self.url_var = tk.StringVar()
        self.url_entry = tk.Entry(panel, textvariable=self.url_var, font=self.font, width=48,
                                  bg=BLACK, fg=GREEN, insertbackground=GREEN,
                                  selectbackground=GREEN_DIM, selectforeground=HEAD,
                                  relief="flat", highlightthickness=1,
                                  highlightbackground=GREEN_DIM, highlightcolor=GREEN)
        self.url_entry.grid(row=3, column=0, columnspan=2, sticky="ew", ipady=6, pady=(4, 16))
        self._add_paste_menu(self.url_entry)

        tk.Label(panel, text="> FORMAT", font=self.font_bold, fg=GREEN,
                 bg=PANEL).grid(row=4, column=0, sticky="w")
        self.format_var = tk.StringVar(value=FORMATS[0].upper())
        self.format_menu = tk.OptionMenu(panel, self.format_var, *(f.upper() for f in FORMATS))
        self.format_menu.configure(font=self.font_bold, bg=BLACK, fg=GREEN,
                                   activebackground=GREEN_DIM, activeforeground=HEAD,
                                   relief="flat", highlightthickness=1,
                                   highlightbackground=GREEN_DIM, indicatoron=False,
                                   width=8, cursor="hand2")
        self.format_menu["menu"].configure(font=self.font, bg=BLACK, fg=GREEN,
                                           activebackground=GREEN, activeforeground=BLACK,
                                           relief="flat", bd=0)
        self.format_menu.grid(row=5, column=0, sticky="w", pady=(4, 0), ipady=4)

        self.button = tk.Button(panel, text="[ DOWNLOAD ]", font=self.font_bold, bg=BLACK,
                                fg=GREEN, activebackground=GREEN, activeforeground=BLACK,
                                relief="flat", bd=0, highlightthickness=1,
                                highlightbackground=GREEN, cursor="hand2", padx=18, pady=6,
                                command=self.start_download)
        self.button.grid(row=5, column=1, sticky="e", pady=(4, 0))
        self.button.bind("<Enter>", lambda _e: self._hover(True))
        self.button.bind("<Leave>", lambda _e: self._hover(False))

        self.bar_var = tk.StringVar(value="")
        tk.Label(panel, textvariable=self.bar_var, font=self.font, fg=GREEN,
                 bg=PANEL).grid(row=6, column=0, columnspan=2, sticky="w", pady=(18, 0))
        self.status_var = tk.StringVar(value=f"> bereit. ziel: {default_output_dir()}")
        self.status = tk.Label(panel, textvariable=self.status_var, font=self.font,
                               fg=GREEN_MID, bg=PANEL, wraplength=540, justify="left")
        self.status.grid(row=7, column=0, columnspan=2, sticky="w")

        panel.columnconfigure(1, weight=1)
        return panel

    def _add_paste_menu(self, entry: tk.Entry) -> None:
        menu = tk.Menu(entry, tearoff=False, font=self.font, bg=BLACK, fg=GREEN,
                       activebackground=GREEN, activeforeground=BLACK)
        menu.add_command(label="Einfügen", command=lambda: entry.event_generate("<<Paste>>"))
        menu.add_command(label="Leeren", command=lambda: self.url_var.set(""))
        for button in ("<Button-3>", "<Button-2>"):
            entry.bind(button, lambda e: menu.tk_popup(e.x_root, e.y_root))

    def _center_panel(self, event) -> None:
        self.canvas.coords(self.panel_window, event.width / 2, event.height / 2)

    def _hover(self, inside: bool) -> None:
        if self.busy:
            return
        self.button.configure(bg=GREEN if inside else BLACK, fg=BLACK if inside else GREEN)

    def _animate(self) -> None:
        self.rain.step()
        self.root.after(RAIN_TICK_MS, self._animate)

    # ---------- Download ----------

    def start_download(self) -> None:
        if self.busy:
            return
        url = self.url_var.get().strip()
        if not url:
            self._set_status("> fehler: bitte zuerst einen link eingeben.", error=True)
            return
        fmt = self.format_var.get().lower()
        self.busy = True
        self.button.configure(text="[ LÄUFT... ]", state="disabled", bg=BLACK,
                              disabledforeground=GREEN_DIM)
        self.bar_var.set(progress_bar(0))
        self._set_status("> verbinde mit der matrix ...")
        threading.Thread(target=self._worker, args=(url, fmt), daemon=True).start()

    def _worker(self, url: str, fmt: str) -> None:
        try:
            path = download_audio(url, fmt, on_progress=self.events.put)
            self.events.put(("ok", path))
        except DownloadError as exc:
            self.events.put(("error", str(exc)))
        except Exception as exc:  # unerwartete Fehler trotzdem anzeigen
            self.events.put(("error", f"{type(exc).__name__}: {exc}"))

    def _poll_events(self) -> None:
        try:
            while True:
                self._handle(self.events.get_nowait())
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def _handle(self, event) -> None:
        if isinstance(event, Progress):
            if event.stage == "download":
                if event.percent is not None:
                    self.bar_var.set(progress_bar(event.percent))
                self._set_status("> lade tonspur herunter ...")
            elif event.stage == "convert":
                self.bar_var.set(progress_bar(100))
                self._set_status("> wandle um ...")
            return
        kind, payload = event
        if kind == "ok":
            self._set_status(f"> fertig: {payload}")
            self.url_var.set("")
        else:
            self.bar_var.set("")
            self._set_status(f"> fehler: {short_error(payload)}", error=True)
        self.busy = False
        self.button.configure(text="[ DOWNLOAD ]", state="normal", bg=BLACK, fg=GREEN)

    def _set_status(self, text: str, error: bool = False) -> None:
        self.status_var.set(text)
        self.status.configure(fg=ERROR if error else GREEN_MID)


def short_error(message: str) -> str:
    """Kürzt yt-dlp-Fehlermeldungen auf das Wesentliche."""
    message = message.removeprefix("ERROR: ").split("; please report")[0]
    return message if len(message) <= 220 else message[:217] + "..."


def run() -> None:
    root = tk.Tk()
    TubeSoundsApp(root)
    root.mainloop()


if __name__ == "__main__":
    run()
