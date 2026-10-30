from pathlib import Path

import pytest

from tubesounds.core import DownloadError, build_options, download_audio


@pytest.mark.parametrize("fmt", ["mp3", "M4A", "wav"])
def test_build_options_sets_codec(fmt):
    opts = build_options(fmt, Path("/tmp/out"))
    assert opts["postprocessors"][0]["preferredcodec"] == fmt.lower()
    assert opts["outtmpl"].startswith("/tmp/out")
    assert Path(opts["ffmpeg_location"]).exists()


def test_build_options_rejects_unknown_format():
    with pytest.raises(ValueError):
        build_options("flac", Path("/tmp/out"))


def test_empty_url_is_rejected():
    with pytest.raises(DownloadError):
        download_audio("   ")
