"""Whitebox coverage for ``scripts/web_scraping/youtube_downloader.py``.

Every method calls into the third-party ``yt_dlp`` library; we patch the
``yt_dlp.YoutubeDL`` class with a configurable mock so we can exercise both
success and exception arms without touching the network.

Branches:

* ``__init__``: download path created when missing; existing path branch.
* ``get_video_info``: success returns a normalised dict; exception returns
  ``None``.
* ``download_video``: each quality value (mapped vs default fallback);
  exception arm.
* ``download_audio``: each format (mp3 default, wav, m4a); exception arm.
* ``download_playlist``: with and without ``max_videos``; exception arm.
* ``download_subtitles_only``: success and exception.
* ``get_available_formats``: separates video/audio/none branches; exception
  arm.
* ``download_custom_format``: success and exception.
* ``search_youtube``: success and exception.
* ``format_duration``: zero, sub-hour, multi-hour branches.
* ``display_video_info``: ``None`` and populated.
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from scripts.web_scraping import youtube_downloader as yd


@contextmanager
def _mock_ydl(extract_info=None, download=None, raise_on_init=None):
    """Context manager that patches ``yt_dlp.YoutubeDL`` with a configurable mock."""
    ydl_instance = MagicMock()
    if extract_info is not None:
        ydl_instance.extract_info.return_value = extract_info
    if download is not None:
        ydl_instance.download.side_effect = download
    cls = MagicMock()
    if raise_on_init is not None:
        cls.side_effect = raise_on_init
    else:
        cls.return_value.__enter__.return_value = ydl_instance
        cls.return_value.__exit__.return_value = False
    with patch.object(yd, "yt_dlp", new=MagicMock(YoutubeDL=cls)):
        yield ydl_instance, cls


# ----------------------- __init__ -----------------------------

class TestInit:
    def test_creates_missing_download_path(self, tmp_path):
        target = tmp_path / "downloads"
        downloader = yd.YouTubeDownloader(download_path=str(target))
        assert target.exists() and downloader.download_path == str(target)

    def test_existing_download_path_branch(self, tmp_path):
        target = tmp_path / "exists"
        target.mkdir()
        yd.YouTubeDownloader(download_path=str(target))
        assert target.exists()


# ----------------------- get_video_info -----------------------

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


# ----------------------- download_video -----------------------

class TestDownloadVideo:
    @pytest.mark.parametrize("quality", ["1080p", "720p", "480p", "360p", "best", "worst", "weird"])
    def test_each_quality(self, tmp_path, quality):
        downloader = yd.YouTubeDownloader(str(tmp_path / "d"))
        with _mock_ydl(extract_info={}):
            assert downloader.download_video("https://yt/x", quality) is True

    def test_exception_branch(self, tmp_path):
        downloader = yd.YouTubeDownloader(str(tmp_path / "d"))
        with _mock_ydl(raise_on_init=RuntimeError("boom")):
            assert downloader.download_video("https://yt/x") is False


# ----------------------- download_audio -----------------------

class TestDownloadAudio:
    @pytest.mark.parametrize("fmt", ["mp3", "wav", "m4a"])
    def test_each_format(self, tmp_path, fmt):
        downloader = yd.YouTubeDownloader(str(tmp_path / "d"))
        with _mock_ydl(extract_info={}):
            assert downloader.download_audio("https://yt/x", fmt) is True

    def test_exception_branch(self, tmp_path):
        downloader = yd.YouTubeDownloader(str(tmp_path / "d"))
        with _mock_ydl(raise_on_init=RuntimeError("boom")):
            assert downloader.download_audio("https://yt/x") is False


# --------------------- download_playlist ----------------------

class TestDownloadPlaylist:
    def test_with_max_videos(self, tmp_path):
        downloader = yd.YouTubeDownloader(str(tmp_path / "d"))
        with _mock_ydl(extract_info={}):
            assert downloader.download_playlist("https://yt/p", max_videos=3) is True

    def test_without_max_videos(self, tmp_path):
        downloader = yd.YouTubeDownloader(str(tmp_path / "d"))
        with _mock_ydl(extract_info={}):
            assert downloader.download_playlist("https://yt/p") is True

    def test_best_quality_branch(self, tmp_path):
        downloader = yd.YouTubeDownloader(str(tmp_path / "d"))
        with _mock_ydl(extract_info={}):
            assert downloader.download_playlist("https://yt/p", video_quality="best") is True

    def test_exception_branch(self, tmp_path):
        downloader = yd.YouTubeDownloader(str(tmp_path / "d"))
        with _mock_ydl(raise_on_init=RuntimeError("boom")):
            assert downloader.download_playlist("https://yt/p") is False


# ------------------- download_subtitles_only ------------------

class TestDownloadSubtitlesOnly:
    def test_success(self, tmp_path):
        downloader = yd.YouTubeDownloader(str(tmp_path / "d"))
        with _mock_ydl(extract_info={}):
            assert downloader.download_subtitles_only("https://yt/x") is True

    def test_exception_branch(self, tmp_path):
        downloader = yd.YouTubeDownloader(str(tmp_path / "d"))
        with _mock_ydl(raise_on_init=RuntimeError("boom")):
            assert downloader.download_subtitles_only("https://yt/x") is False


# -------------------- get_available_formats -------------------

class TestGetAvailableFormats:
    def test_separates_video_and_audio(self, tmp_path):
        info = {"formats": [
            {"format_id": "a", "ext": "mp4", "vcodec": "h264", "acodec": "aac"},
            {"format_id": "b", "ext": "m4a", "vcodec": "none", "acodec": "aac"},
            {"format_id": "c", "ext": "mp4", "vcodec": "h264", "acodec": "none"},  # unmatched (vcodec ok, acodec none) -> falls into elif branch False
        ]}
        downloader = yd.YouTubeDownloader(str(tmp_path / "d"))
        with _mock_ydl(extract_info=info):
            out = downloader.get_available_formats("https://yt/x")
        assert len(out["video"]) == 1 and out["video"][0]["format_id"] == "a"
        assert len(out["audio"]) == 1 and out["audio"][0]["format_id"] == "b"

    def test_exception_returns_none(self, tmp_path):
        downloader = yd.YouTubeDownloader(str(tmp_path / "d"))
        with _mock_ydl(raise_on_init=RuntimeError("boom")):
            assert downloader.get_available_formats("https://yt/x") is None


# ------------------- download_custom_format -------------------

class TestDownloadCustomFormat:
    def test_success(self, tmp_path):
        downloader = yd.YouTubeDownloader(str(tmp_path / "d"))
        with _mock_ydl(extract_info={}):
            assert downloader.download_custom_format("https://yt/x", "137") is True

    def test_exception_branch(self, tmp_path):
        downloader = yd.YouTubeDownloader(str(tmp_path / "d"))
        with _mock_ydl(raise_on_init=RuntimeError("boom")):
            assert downloader.download_custom_format("https://yt/x", "137") is False


# ------------------------ search_youtube ----------------------

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

    def test_exception_returns_empty(self, tmp_path):
        downloader = yd.YouTubeDownloader(str(tmp_path / "d"))
        with _mock_ydl(raise_on_init=RuntimeError("boom")):
            assert downloader.search_youtube("python") == []


# ------------------------ format_duration ---------------------

class TestFormatDuration:
    @pytest.mark.parametrize("seconds,expected", [
        (None, "Unknown"),
        (0, "Unknown"),  # 0 is falsy -> first branch
        (30, "00:30"),
        (90, "01:30"),
        (3661, "01:01:01"),
    ])
    def test_each_branch(self, tmp_path, seconds, expected):
        downloader = yd.YouTubeDownloader(str(tmp_path / "d"))
        assert downloader.format_duration(seconds) == expected


# ------------------------ display_video_info ------------------

class TestDisplayVideoInfo:
    def test_none_branch(self, tmp_path, capsys):
        yd.YouTubeDownloader(str(tmp_path / "d")).display_video_info(None)
        assert "No video information available" in capsys.readouterr().out

    def test_populated_branch(self, tmp_path, capsys):
        downloader = yd.YouTubeDownloader(str(tmp_path / "d"))
        downloader.display_video_info({
            "title": "T", "uploader": "U", "duration": 65,
            "view_count": 1234, "upload_date": "20250101",
            "formats": 5, "webpage_url": "wp",
        })
        out = capsys.readouterr().out
        assert "VIDEO INFORMATION" in out and "T" in out
