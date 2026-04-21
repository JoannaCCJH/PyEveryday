"""Whitebox coverage for ``scripts/web_scraping/youtube_downloader.py``.

Trimmed to: init (creates dir), info fetch (success + error), video download,
audio download, available-formats parsing, search, and duration formatting.
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


class TestInit:
    def test_creates_missing_download_path(self, tmp_path):
        target = tmp_path / "downloads"
        downloader = yd.YouTubeDownloader(download_path=str(target))
        assert target.exists() and downloader.download_path == str(target)


class TestGetVideoInfo:
    def test_success(self, tmp_path):
        info = {"title": "T", "uploader": "U", "duration": 65,
                "view_count": 100, "upload_date": "20250101",
                "description": "d", "formats": [], "thumbnail": "th",
                "webpage_url": "wp"}
        downloader = yd.YouTubeDownloader(str(tmp_path / "d"))
        with _mock_ydl(extract_info=info):
            out = downloader.get_video_info("https://yt/abc")
        assert out["title"] == "T" and out["uploader"] == "U"

    def test_exception_returns_none(self, tmp_path, capsys):
        downloader = yd.YouTubeDownloader(str(tmp_path / "d"))
        with _mock_ydl(raise_on_init=RuntimeError("boom")):
            out = downloader.get_video_info("https://yt/abc")
        assert out is None
        assert "Error getting video info" in capsys.readouterr().out


class TestDownloadVideo:
    def test_download_720p(self, tmp_path):
        downloader = yd.YouTubeDownloader(str(tmp_path / "d"))
        with _mock_ydl(extract_info={}):
            assert downloader.download_video("https://yt/x", "720p") is True


class TestDownloadAudio:
    def test_download_mp3(self, tmp_path):
        downloader = yd.YouTubeDownloader(str(tmp_path / "d"))
        with _mock_ydl(extract_info={}):
            assert downloader.download_audio("https://yt/x", "mp3") is True


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
        assert len(out["video"]) == 1 and out["video"][0]["format_id"] == "a"
        assert len(out["audio"]) == 1 and out["audio"][0]["format_id"] == "b"


class TestSearchYoutube:
    def test_returns_results(self, tmp_path):
        info = {"entries": [
            {"title": "T", "uploader": "U", "duration": 30, "view_count": 1,
             "webpage_url": "wp", "thumbnail": "th"}
        ]}
        downloader = yd.YouTubeDownloader(str(tmp_path / "d"))
        with _mock_ydl(extract_info=info):
            out = downloader.search_youtube("python", max_results=1)
        assert len(out) == 1 and out[0]["title"] == "T"


class TestFormatDuration:
    def test_multi_hour(self, tmp_path):
        downloader = yd.YouTubeDownloader(str(tmp_path / "d"))
        assert downloader.format_duration(3661) == "01:01:01"
