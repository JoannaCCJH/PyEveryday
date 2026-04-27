from __future__ import annotations

import runpy

import sys

from unittest.mock import MagicMock, patch

import pytest


# Defines the run helper.
def _run(module_name, argv, **patches):
    ctxs = [patch.object(sys, "argv", list(argv))]
    for target, value in patches.items():
        ctxs.append(patch(target, value))
    for c in ctxs:
        c.__enter__()
    try:
        try:
            runpy.run_module(module_name, run_name="__main__")
        except SystemExit:
            pass
    finally:
        for c in reversed(ctxs):
            c.__exit__(None, None, None)


# Provides the isolate_cwd fixture.
@pytest.fixture(autouse=True)
def _isolate_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


# Defines the resp helper.
def _resp(payload, status_code=200, content=b""):
    r = MagicMock()
    r.status_code = status_code
    r.content = content
    r.text = ""
    r.json.return_value = payload
    r.raise_for_status.return_value = None
    return r
WC = "scripts.web_scraping.weather_checker"


# Defines the weather_payload helper.
def _weather_payload():
    return {
        "name": "Mysuru", "sys": {"country": "IN"},
        "main": {"temp": 25.0, "feels_like": 26.0, "humidity": 80, "pressure": 1010},
        "weather": [{"description": "clear sky"}],
        "wind": {"speed": 3.5}, "visibility": 10000,
    }


# Defines the wttr_payload helper.
def _wttr_payload():
    return {"current_condition": [{
        "temp_C": "20", "FeelsLikeC": "21",
        "weatherDesc": [{"value": "Sunny"}],
        "humidity": "70", "pressure": "1015",
        "windspeedKmph": "10", "visibility": "10",
    }]}


# Defines the forecast_payload helper.
def _forecast_payload():
    return {
        "city": {"name": "C"},
        "list": [{"dt": 1700000000, "main": {"temp": 20, "humidity": 50},
                  "weather": [{"description": "sunny"}]}] * 40,
    }


class TestWeatherCheckerCLI:
    # Tests dispatch.
    @pytest.mark.parametrize("argv", [
        [WC],
        [WC, "Mysuru"],
        [WC, "Mysuru", "key", "imperial"],
        [WC, "forecast"],
        [WC, "forecast", "C", "key"],
        [WC, "coords"],
        [WC, "coords", "0", "0", "key"],
    ])
    def test_dispatch(self, argv, capsys):
        _run(WC, argv,
             **{"scripts.web_scraping.weather_checker.requests.get":
                MagicMock(return_value=_resp(_weather_payload())),
                "builtins.input": lambda *a, **kw: "n"})
        capsys.readouterr()

    # Tests forecast with payload.
    def test_forecast_with_payload(self, capsys):
        _run(WC, [WC, "forecast", "C", "key", "5"],
             **{"scripts.web_scraping.weather_checker.requests.get":
                MagicMock(return_value=_resp(_forecast_payload()))})
        capsys.readouterr()
NF = "scripts.web_scraping.news_fetcher"


# Defines the hn_payload helper.
def _hn_payload():
    return [1, 2, 3]


class TestNewsFetcherCLI:
    # Tests dispatch.
    @pytest.mark.parametrize("argv", [
        [NF],
        [NF, "all", "2"],
        [NF, "source"],
        [NF, "source", "hackernews", "3"],
        [NF, "custom"],
        [NF, "custom", "https://example.com/rss"],
        [NF, "search"],
        [NF, "search", "python", "tips"],
        [NF, "trending"],
        [NF, "wat"],
    ])
    def test_dispatch(self, argv, capsys):
        _run(NF, argv,
             **{"scripts.web_scraping.news_fetcher.requests.get":
                MagicMock(side_effect=RuntimeError("net")),
                "builtins.input": lambda *a, **kw: "n"})
        capsys.readouterr()
WS = "scripts.web_scraping.web_scraper"


class TestWebScraperCLI:
    # Tests usage dispatch.
    @pytest.mark.parametrize("argv", [
        [WS],
        [WS, "text"],
        [WS, "text", "https://x", "{not-json"],
        [WS, "links"],
        [WS, "images"],
        [WS, "table"],
        [WS, "forms"],
        [WS, "metadata"],
        [WS, "config"],
        [WS, "wat"],
    ])
    def test_usage_dispatch(self, argv, capsys):
        _run(WS, argv,
             **{"scripts.web_scraping.web_scraper.requests.Session":
                MagicMock()})
        capsys.readouterr()

    # Tests real dispatch.
    @pytest.mark.parametrize("argv", [
        [WS, "text", "https://x", '{"t": "h1"}'],
        [WS, "links", "https://x"],
        [WS, "images", "https://x"],
        [WS, "table", "https://x"],
        [WS, "forms", "https://x"],
        [WS, "metadata", "https://x"],
    ])
    def test_real_dispatch(self, argv, capsys):
        html = b"""<html lang='en'><head><title>T</title></head><body>
            <h1>A</h1><a href='/x'>x</a>
            <img src='/a.png' alt='A' width='10' height='10'/>
            <table><tr><th>h</th></tr><tr><td>1</td></tr></table>
            <form action='/s' method='get'><input name='q'/></form>
        </body></html>"""
        sess = MagicMock()
        sess.return_value.get.return_value = _resp({}, content=html)
        _run(WS, argv,
             **{"scripts.web_scraping.web_scraper.requests.Session": sess})
        capsys.readouterr()
YT = "scripts.web_scraping.youtube_downloader"


# Defines the ydl_mock helper.
def _ydl_mock(extract_info):
    inst = MagicMock()
    inst.extract_info.return_value = extract_info
    cls = MagicMock()
    cls.return_value.__enter__.return_value = inst
    cls.return_value.__exit__.return_value = False
    return MagicMock(YoutubeDL=cls)
class TestYoutubeDownloaderCLI:
    # Tests usage dispatch.
    @pytest.mark.parametrize("argv", [
        [YT],
        [YT, "info"],
        [YT, "video"],
        [YT, "audio"],
        [YT, "playlist"],
        [YT, "subtitles"],
        [YT, "formats"],
        [YT, "custom"],
        [YT, "search"],
        [YT, "wat"],
    ])
    def test_usage_dispatch(self, argv, capsys):
        _run(YT, argv,
             **{"scripts.web_scraping.youtube_downloader.yt_dlp":
                _ydl_mock({})})
        capsys.readouterr()

    # Tests real dispatch.
    @pytest.mark.parametrize("argv,info", [
        ([YT, "info", "https://yt/x"],
         {"title": "T", "uploader": "U", "duration": 65, "view_count": 100,
          "upload_date": "20250101", "description": "d", "formats": [],
          "thumbnail": "th", "webpage_url": "wp"}),
        ([YT, "video", "https://yt/x", "720p"], {}),
        ([YT, "audio", "https://yt/x", "mp3"], {}),
        ([YT, "playlist", "https://yt/p", "2"], {}),
        ([YT, "subtitles", "https://yt/x", "en,fr"], {}),
        ([YT, "formats", "https://yt/x"],
         {"formats": [{"format_id": "a", "ext": "mp4",
                       "vcodec": "h264", "acodec": "aac"}]}),
        ([YT, "custom", "https://yt/x", "22"], {}),
        ([YT, "search", "python", "3"],
         {"entries": [{"title": "T", "uploader": "U", "duration": 30,
                       "view_count": 1, "webpage_url": "wp",
                       "thumbnail": "th"}]}),
    ])
    def test_real_dispatch(self, argv, info, capsys):
        _run(YT, argv,
             **{"scripts.web_scraping.youtube_downloader.yt_dlp":
                _ydl_mock(info)})
        capsys.readouterr()
