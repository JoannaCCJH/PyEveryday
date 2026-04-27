from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import requests

from scripts.web_scraping.weather_checker import WeatherChecker


# Defines the resp helper.
def _resp(payload):
    r = MagicMock()
    r.json.return_value = payload
    r.raise_for_status.return_value = None
    return r


# Provides the metric_payload fixture.
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


# Provides the wttr_payload fixture.
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


class TestGetWeatherByCity:
    # Tests api key success.
    def test_api_key_success(self, metric_payload):
        checker = WeatherChecker(api_key="key")
        with patch("scripts.web_scraping.weather_checker.requests.get",
                   return_value=_resp(metric_payload)):
            out = checker.get_weather_by_city("Mysuru")
        assert out["city"] == "Mysuru" and out["temperature"] == "25.0°C"

    # Tests api key request exception falls back.
    def test_api_key_request_exception_falls_back(self, wttr_payload):
        checker = WeatherChecker(api_key="key")
        with patch("scripts.web_scraping.weather_checker.requests.get",
                   side_effect=[requests.exceptions.RequestException("boom"),
                                _resp(wttr_payload)]):
            out = checker.get_weather_by_city("anywhere")
        assert out is not None and out["temperature"] == "20°C"


class TestGetWeatherByCoordinates:
    # Tests no api key short circuits.
    def test_no_api_key_short_circuits(self, capsys):
        checker = WeatherChecker(api_key=None)
        assert checker.get_weather_by_coordinates(0, 0) is None
        assert "Coordinates require API key" in capsys.readouterr().out


class TestFormatHelpers:
    # Tests format imperial.
    def test_format_imperial(self, metric_payload):
        out = WeatherChecker().format_weather_data(metric_payload, "imperial")
        assert out["temperature"].endswith("°F") and out["wind_speed"].endswith("mph")
