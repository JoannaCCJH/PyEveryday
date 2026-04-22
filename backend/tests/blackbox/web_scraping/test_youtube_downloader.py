"""
Black-box tests for scripts.web_scraping.youtube_downloader.

Applies EP / BA / EG. All yt_dlp interactions are mocked.
"""
from unittest.mock import MagicMock, patch

import pytest

from scripts.web_scraping.youtube_downloader import YouTubeDownloader

pytestmark = pytest.mark.blackbox


class _FakeYDL:
    """Context manager that returns a configurable fake YDL."""

    def __init__(self, extract_info_return=None, download_side_effect=None):
        self.extract_info_return = extract_info_return or {}
        self.download_side_effect = download_side_effect
        self.download_calls = []
        self.extract_info_calls = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def extract_info(self, url, download=False):
        self.extract_info_calls.append((url, download))
        if isinstance(self.extract_info_return, Exception):
            raise self.extract_info_return
        return self.extract_info_return

    def download(self, urls):
        self.download_calls.append(urls)
        if self.download_side_effect:
            raise self.download_side_effect


@pytest.fixture
def downloader(tmp_path):
    return YouTubeDownloader(download_path=str(tmp_path / "dl"))


# =========================================================================
# EP â Equivalence Partitioning
# =========================================================================

class TestConstructorEP:
    def test_download_path_created_if_missing(self, tmp_path):
        # EP: missing directory class -> created.
        target = tmp_path / "new_dl"
        assert not target.exists()
        YouTubeDownloader(download_path=str(target))
        assert target.exists()

    def test_download_path_reused_if_exists(self, tmp_path):
        # EP: existing directory class -> no error.
        target = tmp_path / "existing"
        target.mkdir()
        YouTubeDownloader(download_path=str(target))
        assert target.exists()


class TestGetVideoInfoEP:
    def test_info_success_returns_normalized_dict(self, downloader):
        # EP: success class -> dict with all documented keys.
        fake = _FakeYDL(extract_info_return={
            "title": "T", "uploader": "U", "duration": 120,
            "view_count": 1000, "upload_date": "20240101",
            "description": "d" * 600, "formats": [1, 2, 3],
            "thumbnail": "http://thumb", "webpage_url": "http://w",
        })
        with patch("scripts.web_scraping.youtube_downloader.yt_dlp.YoutubeDL", return_value=fake):
            info = downloader.get_video_info("http://x")
        assert info["title"] == "T"
        assert info["formats"] == 3
        # Description is truncated to 500 chars + "...".
        assert info["description"].endswith("...")

    def test_info_exception_returns_none(self, downloader, capsys):
        # EP: error class -> None + printed error.
        fake = _FakeYDL(extract_info_return=RuntimeError("fail"))
        with patch("scripts.web_scraping.youtube_downloader.yt_dlp.YoutubeDL", return_value=fake):
            assert downloader.get_video_info("http://x") is None
        assert "Error getting video info" in capsys.readouterr().out


class TestDownloadEP:
    def test_download_video_success(self, downloader):
        # EP: success class -> returns True.
        fake = _FakeYDL()
        with patch("scripts.web_scraping.youtube_downloader.yt_dlp.YoutubeDL", return_value=fake):
            assert downloader.download_video("http://x") is True
        assert fake.download_calls == [["http://x"]]

    def test_download_video_failure(self, downloader):
        # EP: error class -> returns False.
        fake = _FakeYDL(download_side_effect=RuntimeError("bad"))
        with patch("scripts.web_scraping.youtube_downloader.yt_dlp.YoutubeDL", return_value=fake):
            assert downloader.download_video("http://x") is False

    def test_download_audio_success(self, downloader):
        # EP: audio class -> returns True.
        fake = _FakeYDL()
        with patch("scripts.web_scraping.youtube_downloader.yt_dlp.YoutubeDL", return_value=fake):
            assert downloader.download_audio("http://x") is True

    def test_download_audio_custom_format(self, downloader):
        # EP: wav format class -> postprocessor's preferredcodec updated.
        fake = _FakeYDL()
        captured_opts = {}

        def _capture(opts):
            captured_opts.update(opts)
            return fake

        with patch("scripts.web_scraping.youtube_downloader.yt_dlp.YoutubeDL", side_effect=_capture):
            downloader.download_audio("http://x", format="wav")
        assert captured_opts["postprocessors"][0]["preferredcodec"] == "wav"


# =========================================================================
# BA â Boundary Analysis
# =========================================================================

class TestFormatDurationBA:
    @pytest.mark.parametrize("seconds, expected", [
        (0, "Unknown"),
        (None, "Unknown"),
        (1, "00:01"),
        (59, "00:59"),
        (60, "01:00"),
        (3599, "59:59"),
        (3600, "01:00:00"),
        (3661, "01:01:01"),
    ])
    def test_format_duration_boundaries(self, downloader, seconds, expected):
        # BA: each boundary between seconds / minutes / hours.
        assert downloader.format_duration(seconds) == expected


class TestQualityMappingBA:
    def test_known_quality_maps_to_format_filter(self, downloader):
        # BA: documented quality class -> corresponding format string passed.
        fake = _FakeYDL()
        captured = {}

        def _capture(opts):
            captured.update(opts)
            return fake

        with patch("scripts.web_scraping.youtube_downloader.yt_dlp.YoutubeDL", side_effect=_capture):
            downloader.download_video("http://x", quality="480p")
        assert "height<=480" in captured["format"]

    def test_unknown_quality_falls_back_to_720(self, downloader):
        # BA: unknown-quality class -> default 720p filter.
        fake = _FakeYDL()
        captured = {}

        def _capture(opts):
            captured.update(opts)
            return fake

        with patch("scripts.web_scraping.youtube_downloader.yt_dlp.YoutubeDL", side_effect=_capture):
            downloader.download_video("http://x", quality="not_a_real_quality")
        assert "height<=720" in captured["format"]


# =========================================================================
# EG â Error Guessing
# =========================================================================

class TestErrorGuessing:
    def test_search_youtube_returns_empty_on_error(self, downloader):
        # EG: exception in search -> empty list, no crash.
        fake = _FakeYDL(extract_info_return=RuntimeError("fail"))
        with patch("scripts.web_scraping.youtube_downloader.yt_dlp.YoutubeDL", return_value=fake):
            assert downloader.search_youtube("query") == []

    def test_search_youtube_success_normalizes_results(self, downloader):
        # EG: extract_info returns entries -> normalized dict per entry.
        fake = _FakeYDL(extract_info_return={
            "entries": [
                {"title": "A", "uploader": "U", "duration": 10, "view_count": 5,
                 "webpage_url": "http://a", "thumbnail": "t"},
            ]
        })
        with patch("scripts.web_scraping.youtube_downloader.yt_dlp.YoutubeDL", return_value=fake):
            results = downloader.search_youtube("q", max_results=1)
        assert results[0]["title"] == "A"

    def test_download_playlist_max_videos_sets_playlistend(self, downloader):
        # EG: max_videos class -> opts['playlistend'] set.
        fake = _FakeYDL()
        captured = {}

        def _capture(opts):
            captured.update(opts)
            return fake

        with patch("scripts.web_scraping.youtube_downloader.yt_dlp.YoutubeDL", side_effect=_capture):
            downloader.download_playlist("http://x", max_videos=5)
        assert captured["playlistend"] == 5

    def test_download_subtitles_only_sets_skip_download(self, downloader):
        # EG: subtitles_only -> skip_download=True in opts.
        fake = _FakeYDL()
        captured = {}

        def _capture(opts):
            captured.update(opts)
            return fake

        with patch("scripts.web_scraping.youtube_downloader.yt_dlp.YoutubeDL", side_effect=_capture):
            downloader.download_subtitles_only("http://x")
        assert captured.get("skip_download") is True
