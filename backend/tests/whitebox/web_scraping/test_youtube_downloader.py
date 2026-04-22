"""Whitebox coverage for ``scripts/web_scraping/youtube_downloader.py``.

Slimmed: CLI tests already drive every command via ``runpy``.  Here we
keep direct-method assertions for the ones whose return value matters
(success/failure booleans, format separation, duration formatting).
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from scripts.web_scraping import youtube_downloader as yd


@contextmanager
def _mock_ydl(extract_info=None, raise_on_init=None):
    ydl_instance = MagicMock()
    if extract_info is not None:
        ydl_instance.extract_info.return_value = extract_info
    cls = MagicMock()
    if raise_on_init is not None:
        cls.side_effect = raise_on_init
    else:
        cls.return_value.__enter__.return_value = ydl_instance
        cls.return_value.__exit__.return_value = False
    with patch.object(yd, "yt_dlp", new=MagicMock(YoutubeDL=cls)):
        yield ydl_instance, cls


class TestDownloadVideo:
    def test_success_and_failure(self, tmp_path, capsys):
        downloader = yd.YouTubeDownloader(str(tmp_path / "d"))
        with _mock_ydl(extract_info={}):
            assert downloader.download_video("https://yt/x", "720p") is True
        with _mock_ydl(raise_on_init=RuntimeError("boom")):
            assert downloader.download_video("https://yt/x", "720p") is False
        assert "Error downloading video" in capsys.readouterr().out


class TestGetAvailableFormats:
    def test_separates_video_and_audio(self, tmp_path):
        info = {"formats": [
            {"format_id": "a", "ext": "mp4", "vcodec": "h264", "acodec": "aac"},
            {"format_id": "b", "ext": "m4a", "vcodec": "none", "acodec": "aac"},
            {"format_id": "c", "ext": "mp4", "vcodec": "h264", "acodec": "none"},
        ]}
        downloader = yd.YouTubeDownloader(str(tmp_path / "d"))
        with _mock_ydl(extract_info=info):
            out = downloader.get_available_formats("https://yt/x")
        assert out["video"][0]["format_id"] == "a"
        assert out["audio"][0]["format_id"] == "b"


class TestFormatDuration:
    @pytest.mark.parametrize("sec,expected", [
        (3661, "01:01:01"),
        (0, "Unknown"),
    ])
    def test_branches(self, tmp_path, sec, expected):
        downloader = yd.YouTubeDownloader(str(tmp_path / "d"))
        assert downloader.format_duration(sec) == expected
