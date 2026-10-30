from tubesounds import settings
from tubesounds.core import AudioOptions


def test_roundtrip(tmp_path):
    path = tmp_path / "tubesounds.json"
    s = settings.Settings(output_dir=str(tmp_path), format="wav", bitrate=320, mono=True)
    settings.save(s, path)
    assert settings.load(path) == s


def test_missing_or_broken_file_gives_defaults(tmp_path):
    assert settings.load(tmp_path / "fehlt.json") == settings.Settings()
    broken = tmp_path / "kaputt.json"
    broken.write_text("{nicht json", encoding="utf-8")
    assert settings.load(broken) == settings.Settings()


def test_invalid_values_are_reset(tmp_path):
    path = tmp_path / "tubesounds.json"
    path.write_text('{"format": "flac", "bitrate": 999, "unbekannt": 1}', encoding="utf-8")
    loaded = settings.load(path)
    assert (loaded.format, loaded.bitrate) == ("mp3", 192)


def test_audio_options():
    s = settings.Settings(bitrate=256, sample_rate=48000, mono=True, embed_metadata=False)
    assert s.audio() == AudioOptions(256, 48000, True, False)
