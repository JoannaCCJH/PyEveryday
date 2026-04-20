"""Whitebox coverage for ``scripts/web_scraping/weather_checker.py``.

The SUT layers OpenWeatherMap → wttr.in fallbacks behind ``requests.get``.
We patch the network so each branch is reached deterministically:

* ``get_weather_by_city``: no API key -> free fallback; with API key success;
  with API key + ``RequestException`` -> falls to free; generic ``Exception``
  -> returns ``None``.
* ``get_weather_by_coordinates``: no API key short-circuits to ``None``;
  success; ``Exception``.
* ``get_weather_forecast``: no API key short-circuits to ``None``; success;
  failure.
* ``get_weather_free``: success and exception arms.
* ``format_weather_data``: metric and imperial branches.
* ``format_forecast_data``: metric path.
* ``format_wttr_data``: success path.
* ``display_weather`` / ``display_forecast``: ``None`` and full-data
  branches.
* ``save_weather_data``: append branch and missing-file branch.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from scripts.web_scraping.weather_checker import WeatherChecker


def _resp(payload, raises=None):
    r = MagicMock()
    r.json.return_value = payload
    if raises is not None:
        r.raise_for_status.side_effect = raises
    else:
        r.raise_for_status.return_value = None
    return r


@pytest.fixture
def metric_payload():
    return {
        "name": "Mysuru",
        "sys": {"country": "IN"},
        "main": {"temp": 25.0, "feels_like": 26.0, "humidity": 80, "pressure": 1010},
        "weather": [{"description": "clear sky"}],
        "wind": {"speed": 3.5},
        "visibility": 10000,
    }


@pytest.fixture
def wttr_payload():
    return {
        "current_condition": [{
            "temp_C": "20", "FeelsLikeC": "21",
            "weatherDesc": [{"value": "Sunny"}],
            "humidity": "70", "pressure": "1015",
            "windspeedKmph": "10", "visibility": "10",
        }]
    }


# -------------------- get_weather_by_city ---------------------

class TestGetWeatherByCity:
    def test_no_api_key_uses_free(self, wttr_payload):
        checker = WeatherChecker(api_key=None)
        with patch("scripts.web_scraping.weather_checker.requests.get",
                   return_value=_resp(wttr_payload)):
            out = checker.get_weather_by_city("anywhere")
        assert out["temperature"] == "20°C"

    def test_api_key_success(self, metric_payload):
        checker = WeatherChecker(api_key="key")
        with patch("scripts.web_scraping.weather_checker.requests.get",
                   return_value=_resp(metric_payload)):
            out = checker.get_weather_by_city("Mysuru")
        assert out["city"] == "Mysuru" and out["temperature"] == "25.0°C"

    def test_api_key_request_exception_falls_back(self, wttr_payload):
        checker = WeatherChecker(api_key="key")
        # First call (with key) raises; second call (free) returns wttr payload.
        with patch("scripts.web_scraping.weather_checker.requests.get",
                   side_effect=[requests.exceptions.RequestException("boom"),
                                _resp(wttr_payload)]):
            out = checker.get_weather_by_city("anywhere")
        assert out is not None and out["temperature"] == "20°C"

    def test_generic_exception_returns_none(self, capsys):
        checker = WeatherChecker(api_key="key")
        with patch("scripts.web_scraping.weather_checker.requests.get",
                   return_value=MagicMock(
                       raise_for_status=MagicMock(),
                       json=MagicMock(side_effect=KeyError("malformed")))):
            out = checker.get_weather_by_city("anywhere")
        assert out is None


# ----------------- get_weather_by_coordinates -----------------

class TestGetWeatherByCoordinates:
    def test_no_api_key_short_circuits(self, capsys):
        checker = WeatherChecker(api_key=None)
        assert checker.get_weather_by_coordinates(0, 0) is None
        assert "Coordinates require API key" in capsys.readouterr().out

    def test_success(self, metric_payload):
        checker = WeatherChecker(api_key="k")
        with patch("scripts.web_scraping.weather_checker.requests.get",
                   return_value=_resp(metric_payload)):
            out = checker.get_weather_by_coordinates(1, 2)
        assert out["city"] == "Mysuru"

    def test_exception_returns_none(self):
        checker = WeatherChecker(api_key="k")
        with patch("scripts.web_scraping.weather_checker.requests.get",
                   side_effect=RuntimeError("net")):
            assert checker.get_weather_by_coordinates(1, 2) is None


# -------------------- get_weather_forecast --------------------

class TestForecast:
    def test_no_api_key_short_circuits(self, capsys):
        checker = WeatherChecker(api_key=None)
        assert checker.get_weather_forecast("X") is None
        assert "Forecast requires API key" in capsys.readouterr().out

    def test_success(self):
        checker = WeatherChecker(api_key="k")
        payload = {
            "city": {"name": "C"},
            "list": [
                {"dt": 1700000000, "main": {"temp": 20, "humidity": 50},
                 "weather": [{"description": "sunny"}]},
            ] * 40,
        }
        with patch("scripts.web_scraping.weather_checker.requests.get",
                   return_value=_resp(payload)):
            out = checker.get_weather_forecast("C", days=5)
        assert out["city"] == "C" and len(out["forecast"]) == 5

    def test_exception_returns_none(self):
        checker = WeatherChecker(api_key="k")
        with patch("scripts.web_scraping.weather_checker.requests.get",
                   side_effect=RuntimeError("net")):
            assert checker.get_weather_forecast("C") is None


# ----------------------- format_* helpers ---------------------

class TestFormatHelpers:
    def test_format_metric(self, metric_payload):
        out = WeatherChecker().format_weather_data(metric_payload, "metric")
        assert out["temperature"].endswith("°C") and out["wind_speed"].endswith("m/s")

    def test_format_imperial(self, metric_payload):
        out = WeatherChecker().format_weather_data(metric_payload, "imperial")
        assert out["temperature"].endswith("°F") and out["wind_speed"].endswith("mph")

    def test_format_wttr(self, wttr_payload):
        out = WeatherChecker().format_wttr_data(wttr_payload)
        assert out["temperature"] == "20°C"


# ------------------------ display methods ---------------------

class TestDisplay:
    def test_display_weather_none(self, capsys):
        WeatherChecker().display_weather(None)
        assert "No weather data available" in capsys.readouterr().out

    def test_display_weather_full(self, capsys, metric_payload):
        out = WeatherChecker().format_weather_data(metric_payload, "metric")
        WeatherChecker().display_weather(out)
        assert "WEATHER INFORMATION" in capsys.readouterr().out

    def test_display_forecast_none(self, capsys):
        WeatherChecker().display_forecast(None)
        assert "No forecast data available" in capsys.readouterr().out

    def test_display_forecast_full(self, capsys):
        WeatherChecker().display_forecast({
            "city": "C", "forecast": [
                {"date": "2024-01-01", "temperature": "20°C",
                 "description": "sunny", "humidity": "50%"}
            ]
        })
        assert "5-Day Forecast for C" in capsys.readouterr().out


# ----------------------- save_weather_data --------------------

class TestSaveWeather:
    def test_no_data_short_circuits(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        WeatherChecker().save_weather_data(None)
        # No file should be created.
        assert not (tmp_path / "weather_log.json").exists()

    def test_creates_new_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        WeatherChecker().save_weather_data({"a": 1})
        data = json.loads((tmp_path / "weather_log.json").read_text())
        assert data == [{"a": 1}]

    def test_appends_existing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "weather_log.json").write_text(json.dumps([{"a": 1}]))
        WeatherChecker().save_weather_data({"b": 2})
        data = json.loads((tmp_path / "weather_log.json").read_text())
        assert data == [{"a": 1}, {"b": 2}]

    def test_corrupt_existing_file_resets(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "weather_log.json").write_text("not-json")
        WeatherChecker().save_weather_data({"b": 2})
        data = json.loads((tmp_path / "weather_log.json").read_text())
        assert data == [{"b": 2}]
