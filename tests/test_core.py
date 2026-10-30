from pathlib import Path

import pytest

from tubesounds.core import AudioOptions, DownloadError, build_options, download_audio


@pytest.mark.parametrize("fmt", ["mp3", "M4A", "wav"])
def test_build_options_sets_codec(fmt):
    out = Path("/tmp/out")
    opts = build_options(fmt, out)
    assert opts["postprocessors"][0]["preferredcodec"] == fmt.lower()
    assert opts["outtmpl"].startswith(str(out))
    assert Path(opts["ffmpeg_location"]).exists()


def test_build_options_rejects_unknown_format():
    with pytest.raises(ValueError):
        build_options("flac", Path("/tmp/out"))


def test_empty_url_is_rejected():
    with pytest.raises(DownloadError):
        download_audio("   ")


def test_audio_options_become_ffmpeg_args():
    opts = build_options("mp3", Path("/tmp/out"), audio=AudioOptions(320, 48000, True, False))
    assert opts["postprocessors"] == [
        {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "320"}
    ]
    assert opts["postprocessor_args"] == {"extractaudio": ["-ar", "48000", "-ac", "1"]}


def test_wav_has_no_bitrate_and_metadata_is_default():
    opts = build_options("wav", Path("/tmp/out"))
    assert "preferredquality" not in opts["postprocessors"][0]
    assert opts["postprocessors"][1]["key"] == "FFmpegMetadata"
    assert "postprocessor_args" not in opts
