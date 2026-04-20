"""Whitebox coverage for ``scripts/image_audio_video/audio_processor.py``.

We synthesise tiny WAV files (mono and stereo, 16-bit) inside ``tmp_path`` so
the SUT exercises real ``wave`` / ``struct`` code paths.  We also force the
24-bit branch of ``change_volume`` and ``analyze_audio`` (the "only 16-bit
supported" arm) by writing an 8-bit WAV file.

Branches hit:

* ``get_audio_info``: success + exception.
* ``convert_to_mono``: already-mono early return; stereo conversion; exception.
* ``change_volume``: success; non-16-bit branch; exception; clipping branch.
* ``trim_audio``: success + exception.
* ``concatenate_audio``: matching params; mismatched params; exception.
* ``generate_silence`` / ``generate_tone``: success + exception.
* ``analyze_audio``: 16-bit success; non-16-bit branch; exception.
"""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

import pytest

from scripts.image_audio_video import audio_processor as ap


def _write_wav(path, channels=1, sampwidth=2, framerate=8000, num_frames=200,
               sample=1000):
    fmt = {1: "b", 2: "h", 4: "i"}[sampwidth]
    data = struct.pack(f"{num_frames * channels}{fmt}", *([sample] * num_frames * channels))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(sampwidth)
        w.setframerate(framerate)
        w.writeframes(data)
    return path


@pytest.fixture
def proc():
    return ap.AudioProcessor()


# ----------------------- get_audio_info -----------------------

class TestGetAudioInfo:
    def test_success(self, tmp_path, proc):
        p = _write_wav(tmp_path / "x.wav")
        info = proc.get_audio_info(str(p))
        assert info["channels"] == 1
        assert info["frame_rate"] == 8000

    def test_failure(self, tmp_path, proc, capsys):
        assert proc.get_audio_info(str(tmp_path / "missing.wav")) is None
        assert "Error" in capsys.readouterr().out


# ----------------------- convert_to_mono ----------------------

class TestConvertToMono:
    def test_already_mono_short_circuits(self, tmp_path, proc, capsys):
        p = _write_wav(tmp_path / "in.wav", channels=1)
        out = tmp_path / "out.wav"
        assert proc.convert_to_mono(str(p), str(out)) is False
        assert "already mono" in capsys.readouterr().out

    def test_stereo_to_mono(self, tmp_path, proc):
        p = _write_wav(tmp_path / "in.wav", channels=2)
        out = tmp_path / "out.wav"
        assert proc.convert_to_mono(str(p), str(out)) is True
        with wave.open(str(out), "rb") as w:
            assert w.getnchannels() == 1

    def test_failure(self, tmp_path, proc):
        assert proc.convert_to_mono(str(tmp_path / "missing.wav"),
                                    str(tmp_path / "out.wav")) is False


# ------------------------ change_volume -----------------------

class TestChangeVolume:
    def test_16bit_success(self, tmp_path, proc):
        p = _write_wav(tmp_path / "in.wav", sampwidth=2, sample=100)
        out = tmp_path / "out.wav"
        assert proc.change_volume(str(p), str(out), 2.0) is True

    def test_clipping_branch(self, tmp_path, proc):
        # Use values close to int16 max so doubling forces clipping.
        p = _write_wav(tmp_path / "in.wav", sampwidth=2, sample=20000, num_frames=10)
        out = tmp_path / "out.wav"
        assert proc.change_volume(str(p), str(out), 5.0) is True
        with wave.open(str(out), "rb") as w:
            frames = w.readframes(w.getnframes())
        # Make sure the maximum is bounded.
        max_sample = max(struct.unpack(f"{len(frames)//2}h", frames))
        assert max_sample == 32767

    def test_non16_bit_branch(self, tmp_path, proc, capsys):
        p = _write_wav(tmp_path / "in.wav", sampwidth=1, sample=10)
        out = tmp_path / "out.wav"
        assert proc.change_volume(str(p), str(out), 2.0) is False
        assert "Only 16-bit audio is supported" in capsys.readouterr().out

    def test_failure(self, tmp_path, proc):
        assert proc.change_volume(str(tmp_path / "missing.wav"),
                                  str(tmp_path / "out.wav"), 1.0) is False


# ------------------------- trim_audio -------------------------

class TestTrim:
    def test_success(self, tmp_path, proc):
        p = _write_wav(tmp_path / "in.wav", num_frames=8000)
        out = tmp_path / "out.wav"
        assert proc.trim_audio(str(p), str(out), 0.0, 0.5) is True

    def test_failure(self, tmp_path, proc):
        assert proc.trim_audio(str(tmp_path / "missing.wav"),
                               str(tmp_path / "out.wav"), 0, 1) is False


# ----------------------- concatenate_audio --------------------

class TestConcatenate:
    def test_success_with_matching_params(self, tmp_path, proc):
        a = _write_wav(tmp_path / "a.wav")
        b = _write_wav(tmp_path / "b.wav")
        out = tmp_path / "out.wav"
        assert proc.concatenate_audio([str(a), str(b)], str(out)) is True

    def test_param_mismatch_branch(self, tmp_path, proc, capsys):
        a = _write_wav(tmp_path / "a.wav", channels=1)
        b = _write_wav(tmp_path / "b.wav", channels=2)
        out = tmp_path / "out.wav"
        assert proc.concatenate_audio([str(a), str(b)], str(out)) is False
        assert "parameters mismatch" in capsys.readouterr().out

    def test_failure(self, tmp_path, proc):
        assert proc.concatenate_audio([str(tmp_path / "missing.wav")],
                                      str(tmp_path / "out.wav")) is False


# ------------------ generate_silence / tone -------------------

class TestGenerators:
    def test_silence_success(self, tmp_path, proc):
        out = tmp_path / "s.wav"
        assert proc.generate_silence(str(out), 0.05) is True
        assert out.exists()

    def test_silence_failure(self, tmp_path, proc):
        assert proc.generate_silence(str(tmp_path / "no" / "dir.wav"), 0.05) is False

    def test_tone_success(self, tmp_path, proc):
        out = tmp_path / "t.wav"
        assert proc.generate_tone(str(out), 440, 0.05) is True
        assert out.exists()

    def test_tone_failure(self, tmp_path, proc):
        assert proc.generate_tone(str(tmp_path / "no" / "dir.wav"), 440, 0.05) is False


# ------------------------ analyze_audio -----------------------

class TestAnalyze:
    def test_16bit_success(self, tmp_path, proc):
        p = _write_wav(tmp_path / "in.wav", sample=1000, num_frames=500)
        info = proc.analyze_audio(str(p))
        assert info["max_amplitude"] == 1000
        assert info["rms"] > 0

    def test_non16_bit_branch(self, tmp_path, proc, capsys):
        p = _write_wav(tmp_path / "in.wav", sampwidth=1, sample=10)
        assert proc.analyze_audio(str(p)) is None
        assert "Only 16-bit audio analysis is supported" in capsys.readouterr().out

    def test_failure(self, tmp_path, proc):
        assert proc.analyze_audio(str(tmp_path / "missing.wav")) is None
