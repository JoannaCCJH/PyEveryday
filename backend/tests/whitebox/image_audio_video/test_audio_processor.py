"""Whitebox coverage for ``scripts/image_audio_video/audio_processor.py``.

Trimmed to the unique branches: info success, mono conversion + already-mono
short-circuit, change_volume with clipping and the non-16-bit branch,
concatenate param-mismatch arm, and analyze_audio happy path.
"""

from __future__ import annotations

import struct
import wave

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


class TestGetAudioInfo:
    def test_success(self, tmp_path, proc):
        p = _write_wav(tmp_path / "x.wav")
        info = proc.get_audio_info(str(p))
        assert info["channels"] == 1
        assert info["frame_rate"] == 8000


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


class TestChangeVolume:
    def test_clipping_branch(self, tmp_path, proc):
        p = _write_wav(tmp_path / "in.wav", sampwidth=2, sample=20000, num_frames=10)
        out = tmp_path / "out.wav"
        assert proc.change_volume(str(p), str(out), 5.0) is True
        with wave.open(str(out), "rb") as w:
            frames = w.readframes(w.getnframes())
        max_sample = max(struct.unpack(f"{len(frames)//2}h", frames))
        assert max_sample == 32767

    def test_non16_bit_branch(self, tmp_path, proc, capsys):
        p = _write_wav(tmp_path / "in.wav", sampwidth=1, sample=10)
        out = tmp_path / "out.wav"
        assert proc.change_volume(str(p), str(out), 2.0) is False
        assert "Only 16-bit audio is supported" in capsys.readouterr().out


class TestConcatenate:
    def test_param_mismatch_branch(self, tmp_path, proc, capsys):
        a = _write_wav(tmp_path / "a.wav", channels=1)
        b = _write_wav(tmp_path / "b.wav", channels=2)
        out = tmp_path / "out.wav"
        assert proc.concatenate_audio([str(a), str(b)], str(out)) is False
        assert "parameters mismatch" in capsys.readouterr().out


class TestAnalyze:
    def test_16bit_success(self, tmp_path, proc):
        p = _write_wav(tmp_path / "in.wav", sample=1000, num_frames=500)
        info = proc.analyze_audio(str(p))
        assert info["max_amplitude"] == 1000
        assert info["rms"] > 0
