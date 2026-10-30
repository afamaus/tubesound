import pytest

pytest.importorskip("tkinter")

from tubesounds.gui import BAR_WIDTH, progress_bar, short_error  # noqa: E402


def test_progress_bar():
    assert progress_bar(0).startswith("[" + "░" * BAR_WIDTH + "]")
    assert progress_bar(100).startswith("[" + "█" * BAR_WIDTH + "]")


def test_short_error_strips_noise():
    msg = "ERROR: [youtube] abc: Video unavailable; please report this issue on https://..."
    assert short_error(msg) == "[youtube] abc: Video unavailable"
