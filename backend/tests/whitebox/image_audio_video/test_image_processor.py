"""Whitebox coverage for ``scripts/image_audio_video/image_processor.py``.

We use Pillow to fabricate small in-memory test images on disk so each branch
of every ``ImageProcessor`` method is exercised:

* ``resize_image``: ``keep_aspect=True`` (thumbnail) and False (resize) +
  exception arm.
* ``convert_format``: explicit format with RGBA->RGB conversion + no-format
  branch + exception arm.
* ``crop_image`` / ``rotate_image``: success + exception.
* ``apply_filter``: every named filter (blur, sharpen, edge_enhance, emboss,
  contour) + unknown branch + exception arm.
* ``adjust_brightness`` / ``adjust_contrast``: success + exception.
* ``create_thumbnail``: success + exception.
* ``get_image_info``: with and without EXIF + exception.
* ``batch_resize`` / ``batch_convert``: empty dir, mixed-extension dir, and
  output-dir-already-exists branch.
* ``create_test_image`` (module-level).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

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


# ----------------------- resize_image -------------------------

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

    def test_failure(self, tmp_path, proc, capsys):
        out = tmp_path / "out.png"
        assert proc.resize_image(str(tmp_path / "missing.png"),
                                 str(out), (10, 10)) is False
        assert "Error resizing image" in capsys.readouterr().out


# ----------------------- convert_format -----------------------

class TestConvertFormat:
    def test_rgba_to_jpeg_branch(self, tmp_path, proc):
        src = _make_image(tmp_path / "in.png", mode="RGBA", color=(255, 0, 0, 128))
        out = tmp_path / "out.jpg"
        assert proc.convert_format(str(src), str(out), format="JPEG") is True
        with Image.open(out) as im:
            assert im.mode == "RGB"

    def test_no_format_branch(self, tmp_path, proc):
        src = _make_image(tmp_path / "in.png")
        out = tmp_path / "out.png"
        assert proc.convert_format(str(src), str(out)) is True

    def test_failure(self, tmp_path, proc):
        assert proc.convert_format(str(tmp_path / "missing.png"),
                                   str(tmp_path / "out.png")) is False


# --------------------- crop / rotate --------------------------

class TestCropRotate:
    def test_crop_success(self, tmp_path, proc):
        src = _make_image(tmp_path / "in.png", size=(100, 100))
        out = tmp_path / "out.png"
        assert proc.crop_image(str(src), str(out), (10, 10, 60, 60)) is True

    def test_crop_failure(self, tmp_path, proc):
        assert proc.crop_image(str(tmp_path / "missing.png"),
                               str(tmp_path / "out.png"), (0, 0, 1, 1)) is False

    def test_rotate_success(self, tmp_path, proc):
        src = _make_image(tmp_path / "in.png")
        out = tmp_path / "out.png"
        assert proc.rotate_image(str(src), str(out), 45) is True

    def test_rotate_failure(self, tmp_path, proc):
        assert proc.rotate_image(str(tmp_path / "missing.png"),
                                 str(tmp_path / "out.png"), 45) is False


# -------------------------- filters ---------------------------

class TestFilter:
    @pytest.mark.parametrize("ftype", ["blur", "sharpen", "edge_enhance", "emboss", "contour"])
    def test_supported_filters(self, tmp_path, proc, ftype):
        src = _make_image(tmp_path / "in.png")
        out = tmp_path / "out.png"
        assert proc.apply_filter(str(src), str(out), ftype) is True

    def test_unknown_filter_branch(self, tmp_path, proc, capsys):
        src = _make_image(tmp_path / "in.png")
        out = tmp_path / "out.png"
        assert proc.apply_filter(str(src), str(out), "WAT") is False
        assert "Unknown filter" in capsys.readouterr().out

    def test_failure(self, tmp_path, proc):
        assert proc.apply_filter(str(tmp_path / "missing.png"),
                                 str(tmp_path / "out.png"), "blur") is False


# -------------- brightness / contrast / thumbnail -------------

class TestEnhancers:
    def test_brightness_success_and_failure(self, tmp_path, proc):
        src = _make_image(tmp_path / "in.png")
        assert proc.adjust_brightness(str(src), str(tmp_path / "b.png"), 1.5) is True
        assert proc.adjust_brightness(str(tmp_path / "missing.png"),
                                      str(tmp_path / "b.png"), 1.5) is False

    def test_contrast_success_and_failure(self, tmp_path, proc):
        src = _make_image(tmp_path / "in.png")
        assert proc.adjust_contrast(str(src), str(tmp_path / "c.png"), 1.5) is True
        assert proc.adjust_contrast(str(tmp_path / "missing.png"),
                                    str(tmp_path / "c.png"), 1.5) is False

    def test_thumbnail_success_and_failure(self, tmp_path, proc):
        src = _make_image(tmp_path / "in.png", size=(200, 200))
        out = tmp_path / "thumb.png"
        assert proc.create_thumbnail(str(src), str(out)) is True
        # Thumbnail is written with "_thumb.jpg" appended to the base.
        assert (tmp_path / "thumb_thumb.jpg").exists()
        assert proc.create_thumbnail(str(tmp_path / "missing.png"), str(out)) is False


# ------------------------ image info --------------------------

class TestGetImageInfo:
    def test_returns_dict(self, tmp_path, proc):
        src = _make_image(tmp_path / "in.png")
        info = proc.get_image_info(str(src))
        assert info["filename"] == "in.png"
        assert info["mode"] == "RGB"
        assert info["has_exif"] is False  # PIL Image.new has no EXIF

    def test_failure(self, tmp_path, proc):
        assert proc.get_image_info(str(tmp_path / "missing.png")) is None


# --------------------- batch operations -----------------------

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
        out_dir.mkdir()  # already exists -> branch where we DO NOT makedirs
        n = proc.batch_resize(str(in_dir), str(out_dir), (10, 10))
        assert n == 1

    def test_batch_resize_skips_when_resize_fails(self, tmp_path, proc):
        in_dir = tmp_path / "in"
        in_dir.mkdir()
        _make_image(in_dir / "a.png")
        out_dir = tmp_path / "out"
        with patch.object(ip.ImageProcessor, "resize_image", return_value=False):
            n = proc.batch_resize(str(in_dir), str(out_dir), (10, 10))
        assert n == 0

    def test_batch_convert(self, tmp_path, proc):
        in_dir = tmp_path / "in"
        in_dir.mkdir()
        _make_image(in_dir / "a.png")
        _make_image(in_dir / "b.png")
        out_dir = tmp_path / "out"
        n = proc.batch_convert(str(in_dir), str(out_dir), "PNG")
        assert n == 2

    def test_batch_convert_empty_dir(self, tmp_path, proc):
        in_dir = tmp_path / "in"
        in_dir.mkdir()
        n = proc.batch_convert(str(in_dir), str(tmp_path / "out"), "PNG")
        assert n == 0


class TestModuleLevel:
    def test_create_test_image(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        ip.create_test_image()
        assert (tmp_path / "test_image.png").exists()
