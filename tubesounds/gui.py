"""Oberfläche im Matrix-Look: Linkfeld, Formatwahl, Download-Button und Digital Rain."""

from __future__ import annotations

import queue
import random
import threading
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog

from . import __version__, settings
from .core import BITRATES, FORMATS, SAMPLE_RATES, DownloadError, Progress, download_audio
from .legal import DISCLAIMER_CONFIRM, DISCLAIMER_TEXT, DISCLAIMER_TITLE, DISCLAIMER_VERSION

ASSETS = Path(__file__).parent / "assets"
BANNER = ASSETS / "banner.png"
ICON = ASSETS / "icon.png"

# Farben aus dem Banner: tiefes Petrol als Hintergrund, Mint und Türkis als Akzente
BLACK = "#01080b"
PANEL = "#03131a"
MINT = "#3fcf9f"
TEAL = "#4fbfc8"
TEAL_MID = "#2f8f8f"
TEAL_DIM = "#0f3d40"
TEXT = "#dff7f2"
HEAD = "#e6fffa"
ERROR = "#ff5a6a"

RAIN_CHARS = "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ0123456789"
RAIN_STEP = 16  # Pixel zwischen Spalten und Zeilen
RAIN_TRAIL = 14  # Länge der Spur hinter dem Kopf
RAIN_TICK_MS = 70
# Farbverlauf der Spur: vom hellen Kopf über Mint und Türkis bis fast schwarz
RAIN_COLORS = [HEAD, MINT, MINT, TEAL, TEAL_MID] + [
    f"#{g // 8:02x}{g:02x}{g:02x}" for g in range(120, 10, -110 // (RAIN_TRAIL - 4))
]

BAR_WIDTH = 24

SAMPLE_RATE_LABELS = {0: "Original", 44100: "44,1 kHz", 48000: "48 kHz"}
CHANNEL_LABELS = {False: "Stereo", True: "Mono"}


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
        self.settings = settings.load()

        family = pick_font(root)
        self.font = (family, 11)
        self.font_bold = (family, 11, "bold")
        self.font_title = (family, 26, "bold")
        self.font_rain = (family, 11)

        root.title("TubeSounds")
        try:
            self.icon = tk.PhotoImage(file=str(ICON))
            root.iconphoto(True, self.icon)
        except tk.TclError:
            pass
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
        if self.settings.disclaimer_accepted != DISCLAIMER_VERSION:
            root.after(200, lambda: self.show_disclaimer(first_start=True))

    # ---------- Aufbau ----------

    def _build_panel(self) -> tk.Frame:
        panel = tk.Frame(self.canvas, bg=PANEL, highlightbackground=TEAL_MID,
                         highlightcolor=TEAL_MID, highlightthickness=1, padx=24, pady=18)

        try:
            self.banner = tk.PhotoImage(file=str(BANNER))
            tk.Label(panel, image=self.banner, bg=PANEL, bd=0).grid(row=0, column=0,
                                                                   columnspan=2)
        except tk.TclError:  # Bild fehlt: Schriftzug als Ersatz
            tk.Label(panel, text="T U B E S O U N D S", font=self.font_title,
                     fg=MINT, bg=PANEL).grid(row=0, column=0, columnspan=2, sticky="w")
        tk.Label(panel, text=f"// audio extraction protocol v{__version__}", font=self.font,
                 fg=TEAL, bg=PANEL).grid(row=1, column=0, sticky="w", pady=(6, 14))
        self.make_button(panel, "[ EINSTELLUNGEN ]", self.show_settings, accent=False).grid(
            row=1, column=1, sticky="e", pady=(6, 14))

        tk.Label(panel, text="> LINK", font=self.font_bold, fg=MINT,
                 bg=PANEL).grid(row=2, column=0, columnspan=2, sticky="w")
        self.url_var = tk.StringVar()
        self.url_entry = tk.Entry(panel, textvariable=self.url_var, font=self.font, width=48,
                                  bg=BLACK, fg=TEXT, insertbackground=MINT,
                                  selectbackground=TEAL_DIM, selectforeground=HEAD,
                                  relief="flat", highlightthickness=1,
                                  highlightbackground=TEAL_MID, highlightcolor=MINT)
        self.url_entry.grid(row=3, column=0, columnspan=2, sticky="ew", ipady=6, pady=(4, 16))
        self._add_paste_menu(self.url_entry)

        tk.Label(panel, text="> FORMAT", font=self.font_bold, fg=MINT,
                 bg=PANEL).grid(row=4, column=0, sticky="w")
        self.format_var = tk.StringVar(value=self.settings.format.upper())
        self.format_var.trace_add("write", lambda *_: self._remember_format())
        self.make_option_menu(panel, self.format_var, [f.upper() for f in FORMATS]).grid(
            row=5, column=0, sticky="w", pady=(4, 0), ipady=4)

        self.button = self.make_button(panel, "[ DOWNLOAD ]", self.start_download)
        self.button.grid(row=5, column=1, sticky="e", pady=(4, 0))

        self.bar_var = tk.StringVar(value="")
        tk.Label(panel, textvariable=self.bar_var, font=self.font, fg=TEAL,
                 bg=PANEL).grid(row=6, column=0, columnspan=2, sticky="w", pady=(18, 0))
        self.status_var = tk.StringVar()
        self.status = tk.Label(panel, textvariable=self.status_var, font=self.font,
                               fg=TEAL, bg=PANEL, wraplength=540, justify="left")
        self.status.grid(row=7, column=0, columnspan=2, sticky="w")
        self._show_ready()

        panel.columnconfigure(1, weight=1)
        return panel

    def make_button(self, parent, text: str, command, accent: bool = True) -> tk.Button:
        """Button im Terminal-Stil, beim Überfahren invertiert."""
        color = MINT if accent else TEAL
        button = tk.Button(parent, text=text, font=self.font_bold, bg=BLACK, fg=color,
                           activebackground=color, activeforeground=BLACK, relief="flat",
                           bd=0, highlightthickness=1, highlightbackground=color,
                           disabledforeground=TEAL_DIM, cursor="hand2",
                           padx=18 if accent else 10, pady=6 if accent else 3, command=command)

        def hover(inside: bool) -> None:
            if str(button["state"]) != "disabled":
                button.configure(bg=color if inside else BLACK, fg=BLACK if inside else color)

        button.bind("<Enter>", lambda _e: hover(True))
        button.bind("<Leave>", lambda _e: hover(False))
        return button

    def make_option_menu(self, parent, variable: tk.StringVar, values: list) -> tk.OptionMenu:
        menu = tk.OptionMenu(parent, variable, *values)
        menu.configure(font=self.font_bold, bg=BLACK, fg=MINT, activebackground=TEAL_DIM,
                       activeforeground=HEAD, relief="flat", highlightthickness=1,
                       highlightbackground=TEAL_MID, indicatoron=False,
                       width=max(8, max(len(v) for v in values) + 2), cursor="hand2")
        menu["menu"].configure(font=self.font, bg=BLACK, fg=MINT, activebackground=MINT,
                               activeforeground=BLACK, relief="flat", bd=0)
        return menu

    def make_dialog(self, title: str) -> tuple[tk.Toplevel, tk.Frame]:
        """Modales Fenster im gleichen Look."""
        dialog = tk.Toplevel(self.root, bg=BLACK)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.resizable(False, False)
        body = tk.Frame(dialog, bg=PANEL, highlightbackground=TEAL_MID,
                        highlightthickness=1, padx=22, pady=18)
        body.pack(fill="both", expand=True, padx=10, pady=10)
        tk.Label(body, text=f"> {title.upper()}", font=self.font_bold, fg=MINT,
                 bg=PANEL).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))
        return dialog, body

    def _open_modal(self, dialog: tk.Toplevel) -> None:
        dialog.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - dialog.winfo_reqwidth()) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - dialog.winfo_reqheight()) // 2
        dialog.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        dialog.grab_set()
        dialog.focus_set()

    def label(self, parent, text: str, **grid) -> None:
        tk.Label(parent, text=text, font=self.font, fg=TEAL, bg=PANEL).grid(sticky="w", **grid)

    # ---------- Einstellungen ----------

    def _remember_format(self) -> None:
        self.settings.format = self.format_var.get().lower()
        self._save_settings()

    def _save_settings(self) -> bool:
        try:
            settings.save(self.settings)
            return True
        except OSError as exc:
            self._set_status(f"> fehler: einstellungen nicht gespeichert ({exc})", error=True)
            return False

    def show_settings(self) -> None:
        if self.busy:
            return
        dialog, body = self.make_dialog("Einstellungen")
        current = self.settings

        self.label(body, "ZIELORDNER", row=1, column=0, columnspan=3)
        folder_var = tk.StringVar(value=current.output_dir)
        shown_var = tk.StringVar()

        def show_folder(*_):
            shown_var.set(folder_var.get() or f"{settings.default_output_dir()}  (Standard)")

        folder_var.trace_add("write", show_folder)
        show_folder()
        tk.Entry(body, textvariable=shown_var, font=self.font, width=46, state="readonly",
                 readonlybackground=BLACK, fg=TEXT, relief="flat", highlightthickness=1,
                 highlightbackground=TEAL_MID).grid(row=2, column=0, columnspan=3, sticky="ew",
                                                    ipady=5, pady=(4, 6))

        def choose_folder():
            chosen = filedialog.askdirectory(parent=dialog, initialdir=str(current.target_dir()),
                                             title="Zielordner wählen")
            if chosen:
                folder_var.set(chosen)

        folder_buttons = tk.Frame(body, bg=PANEL)
        folder_buttons.grid(row=3, column=0, columnspan=3, sticky="w", pady=(0, 16))
        self.make_button(folder_buttons, "[ ÄNDERN ... ]", choose_folder, accent=False).pack(
            side="left")
        self.make_button(folder_buttons, "[ STANDARD ]", lambda: folder_var.set(""),
                         accent=False).pack(side="left", padx=(8, 0))

        bitrate_var = tk.StringVar(value=f"{current.bitrate} kbit/s")
        rate_var = tk.StringVar(value=SAMPLE_RATE_LABELS[current.sample_rate])
        channel_var = tk.StringVar(value=CHANNEL_LABELS[current.mono])
        rows = [
            ("BITRATE (MP3/M4A)", bitrate_var, [f"{b} kbit/s" for b in BITRATES]),
            ("ABTASTRATE", rate_var, [SAMPLE_RATE_LABELS[r] for r in SAMPLE_RATES]),
            ("KANÄLE", channel_var, list(CHANNEL_LABELS.values())),
        ]
        for i, (text, var, values) in enumerate(rows):
            self.label(body, text, row=4 + i, column=0, pady=4)
            self.make_option_menu(body, var, values).grid(row=4 + i, column=1, columnspan=2,
                                                          sticky="w", padx=(16, 0), pady=4)

        metadata_var = tk.BooleanVar(value=current.embed_metadata)
        tk.Checkbutton(body, text="Titel, Kanal und Datum in die Datei schreiben",
                       variable=metadata_var, font=self.font, fg=TEXT, bg=PANEL,
                       activebackground=PANEL, activeforeground=MINT, selectcolor=BLACK,
                       highlightthickness=0, bd=0, cursor="hand2").grid(
            row=7, column=0, columnspan=3, sticky="w", pady=(12, 4))

        tk.Label(body, text=f"gespeichert in: {settings.settings_path()}", font=(self.font[0], 9),
                 fg=TEAL_MID, bg=PANEL, wraplength=520, justify="left").grid(
            row=8, column=0, columnspan=3, sticky="w", pady=(8, 14))

        def save():
            self.settings.output_dir = folder_var.get()
            self.settings.bitrate = int(bitrate_var.get().split()[0])
            self.settings.sample_rate = next(r for r, t in SAMPLE_RATE_LABELS.items()
                                             if t == rate_var.get())
            self.settings.mono = channel_var.get() == CHANNEL_LABELS[True]
            self.settings.embed_metadata = metadata_var.get()
            if self._save_settings():
                self._show_ready()
            dialog.destroy()

        buttons = tk.Frame(body, bg=PANEL)
        buttons.grid(row=9, column=0, columnspan=3, sticky="ew")
        self.make_button(buttons, "[ RECHTLICHES ]", self.show_disclaimer, accent=False).pack(
            side="left", padx=(0, 24))
        self.make_button(buttons, "[ SPEICHERN ]", save).pack(side="right")
        self.make_button(buttons, "[ ABBRECHEN ]", dialog.destroy, accent=False).pack(
            side="right", padx=(0, 8))
        dialog.bind("<Escape>", lambda _e: dialog.destroy())
        self._open_modal(dialog)

    def show_disclaimer(self, first_start: bool = False) -> None:
        """Rechtlicher Hinweis; beim ersten Start muss er bestätigt werden."""
        previous_grab = self.root.grab_current()
        dialog, body = self.make_dialog(DISCLAIMER_TITLE)
        text = tk.Text(body, font=self.font, fg=TEXT, bg=BLACK, wrap="word", width=64,
                       height=25, relief="flat", highlightthickness=1,
                       highlightbackground=TEAL_MID, padx=12, pady=10, cursor="arrow")
        text.insert("1.0", DISCLAIMER_TEXT)
        text.configure(state="disabled")
        text.grid(row=1, column=0, sticky="nsew")

        buttons = tk.Frame(body, bg=PANEL)
        buttons.grid(row=3, column=0, sticky="ew", pady=(14, 0))

        def close():
            dialog.destroy()
            if previous_grab is not None and previous_grab.winfo_exists():
                previous_grab.grab_set()

        if first_start:
            tk.Label(body, text=DISCLAIMER_CONFIRM, font=self.font_bold, fg=MINT, bg=PANEL,
                     wraplength=600, justify="left").grid(row=2, column=0, sticky="w",
                                                          pady=(12, 0))

            def accept():
                self.settings.disclaimer_accepted = DISCLAIMER_VERSION
                self._save_settings()
                dialog.destroy()

            self.make_button(buttons, "[ AKZEPTIEREN ]", accept).pack(side="right")
            self.make_button(buttons, "[ BEENDEN ]", self.root.destroy, accent=False).pack(
                side="right", padx=(0, 8))
            dialog.protocol("WM_DELETE_WINDOW", self.root.destroy)
        else:
            self.make_button(buttons, "[ SCHLIESSEN ]", close).pack(side="right")
            dialog.protocol("WM_DELETE_WINDOW", close)
            dialog.bind("<Escape>", lambda _e: close())
        self._open_modal(dialog)

    def _add_paste_menu(self, entry: tk.Entry) -> None:
        menu = tk.Menu(entry, tearoff=False, font=self.font, bg=BLACK, fg=MINT,
                       activebackground=MINT, activeforeground=BLACK)
        menu.add_command(label="Einfügen", command=lambda: entry.event_generate("<<Paste>>"))
        menu.add_command(label="Leeren", command=lambda: self.url_var.set(""))
        for button in ("<Button-3>", "<Button-2>"):
            entry.bind(button, lambda e: menu.tk_popup(e.x_root, e.y_root))

    def _center_panel(self, event) -> None:
        self.canvas.coords(self.panel_window, event.width / 2, event.height / 2)

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
        self.button.configure(text="[ LÄUFT... ]", state="disabled", bg=BLACK)
        self.bar_var.set(progress_bar(0))
        self._set_status("> verbinde mit der matrix ...")
        args = (url, fmt, self.settings.target_dir(), self.settings.audio())
        threading.Thread(target=self._worker, args=args, daemon=True).start()

    def _worker(self, url: str, fmt: str, output_dir: Path, audio) -> None:
        try:
            path = download_audio(url, fmt, output_dir, self.events.put, audio)
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
        self.button.configure(text="[ DOWNLOAD ]", state="normal", bg=BLACK, fg=MINT)

    def _show_ready(self) -> None:
        self._set_status(f"> bereit. ziel: {self.settings.target_dir()}")

    def _set_status(self, text: str, error: bool = False) -> None:
        self.status_var.set(text)
        self.status.configure(fg=ERROR if error else TEAL)


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
