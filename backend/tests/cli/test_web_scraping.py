from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend.tests.cli.conftest import pairs


WC = "scripts.web_scraping.weather_checker"
YT = "scripts.web_scraping.youtube_downloader"


def _resp(payload):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = payload
    r.raise_for_status.return_value = None
    return r


_WEATHER = {
    "name": "X", "sys": {"country": "IN"},
    "main": {"temp": 25.0, "feels_like": 26.0, "humidity": 80, "pressure": 1010},
    "weather": [{"description": "clear sky"}],
    "wind": {"speed": 3.5}, "visibility": 10000,
}
_FORECAST = {
    "city": {"name": "C"},
    "list": [{"dt": 1700000000, "main": {"temp": 20, "humidity": 50},
              "weather": [{"description": "sunny"}]}] * 40,
}


@pytest.mark.parametrize("mode,units", pairs(
    ["city", "forecast", "coords"],
    ["metric", "imperial"],
))
def test_weather_checker_pair(invoke, mode, units):
    # Pairs of {mode: city / forecast / coords} x {units: metric / imperial}.
    if mode == "city":
        argv, payload = ["Mysuru", "key", units], _WEATHER
    elif mode == "forecast":
        argv, payload = ["forecast", "C", "key", "5"], _FORECAST
    else:
        argv, payload = ["coords", "0", "0", "key"], _WEATHER
    result = invoke(WC, argv,
                    patches={"scripts.web_scraping.weather_checker.requests.get":
                             MagicMock(return_value=_resp(payload))})
    assert result.exit_code == 0


def _ydl_mock(extract_info):
    inst = MagicMock()
    inst.extract_info.return_value = extract_info
    cls = MagicMock()
    cls.return_value.__enter__.return_value = inst
    cls.return_value.__exit__.return_value = False
    return MagicMock(YoutubeDL=cls)


@pytest.mark.parametrize("cmd,with_url", pairs(
    ["info", "search"],
    ["yes", "no"],
))
def test_youtube_downloader_pair(invoke, cmd, with_url):
    # Pairs of {command: info / search} x {URL or query provided / omitted}.
    if with_url == "no":
        argv = [cmd]
    elif cmd == "search":
        argv = ["search", "python", "2"]
    else:
        argv = ["info", "https://yt/x"]
    info = {"entries": [{"title": "T", "uploader": "U", "duration": 30,
                         "view_count": 1, "webpage_url": "wp", "thumbnail": "th"}]} \
        if cmd == "search" else {
            "title": "T", "uploader": "U", "duration": 65, "view_count": 100,
            "upload_date": "20250101", "description": "d", "formats": [],
            "thumbnail": "th", "webpage_url": "wp",
        }
    result = invoke(YT, argv,
                    patches={"scripts.web_scraping.youtube_downloader.yt_dlp":
                             _ydl_mock(info)})
    assert result.exit_code == 0
