"""Whitebox coverage for ``scripts/image_audio_video/image_processor.py``.

Trimmed to the unique branches: resize (both aspect modes), RGBA->JPEG
conversion, filter (one supported + unknown), get_info, and batch_resize
(new-dir + existing-dir branches).
"""

from __future__ import annotations

import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

from scripts.image_audio_video import image_processor as ip


@pytest.fixture
def proc():
    return ip.ImageProcessor()


def _make_image(path, mode="RGB", size=(50, 40), color="red"):
    Image.new(mode, size, color=color).save(path)
    return path


class TestResize:
    def test_keep_aspect_true(self, tmp_path, proc):
        src = _make_image(tmp_path / "in.png")
        out = tmp_path / "out.png"
        assert proc.resize_image(str(src), str(out), (10, 10), keep_aspect=True) is True
        with Image.open(out) as im:
            assert max(im.size) <= 10

    def test_keep_aspect_false(self, tmp_path, proc):
        src = _make_image(tmp_path / "in.png")
        out = tmp_path / "out.png"
        assert proc.resize_image(str(src), str(out), (10, 10), keep_aspect=False) is True
        with Image.open(out) as im:
            assert im.size == (10, 10)


class TestConvertFormat:
    def test_rgba_to_jpeg_branch(self, tmp_path, proc):
        src = _make_image(tmp_path / "in.png", mode="RGBA", color=(255, 0, 0, 128))
        out = tmp_path / "out.jpg"
        assert proc.convert_format(str(src), str(out), format="JPEG") is True
        with Image.open(out) as im:
            assert im.mode == "RGB"


class TestFilter:
    def test_blur_supported(self, tmp_path, proc):
        src = _make_image(tmp_path / "in.png")
        out = tmp_path / "out.png"
        assert proc.apply_filter(str(src), str(out), "blur") is True

    def test_unknown_filter_branch(self, tmp_path, proc, capsys):
        src = _make_image(tmp_path / "in.png")
        out = tmp_path / "out.png"
        assert proc.apply_filter(str(src), str(out), "WAT") is False
        assert "Unknown filter" in capsys.readouterr().out


class TestGetImageInfo:
    def test_returns_dict(self, tmp_path, proc):
        src = _make_image(tmp_path / "in.png")
        info = proc.get_image_info(str(src))
        assert info["filename"] == "in.png"
        assert info["mode"] == "RGB"
        assert info["has_exif"] is False


class TestBatch:
    def test_batch_resize_creates_output_dir(self, tmp_path, proc):
        in_dir = tmp_path / "in"
        in_dir.mkdir()
        _make_image(in_dir / "a.png")
        _make_image(in_dir / "b.PNG")
        (in_dir / "ignore.txt").write_text("noop")
        out_dir = tmp_path / "out"
        n = proc.batch_resize(str(in_dir), str(out_dir), (10, 10))
        assert n == 2
        assert (out_dir / "a.png").exists()

    def test_batch_resize_existing_output_dir_branch(self, tmp_path, proc):
        in_dir = tmp_path / "in"
        in_dir.mkdir()
        _make_image(in_dir / "a.png")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        n = proc.batch_resize(str(in_dir), str(out_dir), (10, 10))
        assert n == 1
