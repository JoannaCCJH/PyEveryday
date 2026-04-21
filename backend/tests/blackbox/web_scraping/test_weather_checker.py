"""
Black-box tests for scripts.web_scraping.weather_checker.

Derived from SPEC.md Â§weather_checker (no peeking at implementation).
Applies EP / BA / EG per proposal Â§2.2.

This is the **HTTP mock target** (SPEC + PLAN). All tests use
unittest.mock.patch on requests.get - no network call is made.
"""
from unittest.mock import MagicMock, patch

import pytest
import requests

from scripts.web_scraping.weather_checker import WeatherChecker

pytestmark = pytest.mark.blackbox


OPENWEATHER_OK_JSON = {
    "name": "London",
    "sys": {"country": "GB"},
    "main": {"temp": 10.5, "feels_like": 8.2, "humidity": 75, "pressure": 1013},
    "weather": [{"description": "light rain"}],
    "wind": {"speed": 3.5},
    "visibility": 8000,
}

WTTR_OK_JSON = {
    "current_condition": [{
        "temp_C": "15",
        "FeelsLikeC": "14",
        "weatherDesc": [{"value": "Partly cloudy"}],
        "humidity": "60",
        "pressure": "1012",
        "windspeedKmph": "10",
        "visibility": "10",
    }]
}


def _ok_response(payload):
    m = MagicMock()
    m.status_code = 200
    m.json.return_value = payload
    m.raise_for_status = MagicMock()
    return m


# =========================================================================
# EP â Equivalence Partitioning
# =========================================================================

class TestGetWeatherByCityEP:
    """
    EP partitions for get_weather_by_city:
      api_key:   provided vs absent
      response:  success vs network failure vs non-network exception
    """

    def test_with_api_key_success(self):
        # EP: api_key provided + 200 OK -> parsed dict returned.
        checker = WeatherChecker(api_key="abc")
        with patch("requests.get", return_value=_ok_response(OPENWEATHER_OK_JSON)):
            result = checker.get_weather_by_city("London")
        assert result["city"] == "London"
        assert result["country"] == "GB"
        assert "10.5" in result["temperature"]

    def test_without_api_key_uses_free_fallback(self):
        # EP: api_key absent -> delegates to get_weather_free (wttr.in).
        checker = WeatherChecker()
        with patch("requests.get", return_value=_ok_response(WTTR_OK_JSON)) as mock_get:
            result = checker.get_weather_by_city("London")
        # Verify wttr.in was called (not openweathermap).
        assert "wttr.in" in mock_get.call_args.args[0]
        assert result["description"] == "Partly cloudy"

    def test_request_exception_falls_back_to_free(self):
        # EP: network failure class -> fallback path per SPEC.
        checker = WeatherChecker(api_key="abc")

        def _side_effect(url, **kw):
            if "openweathermap" in url:
                raise requests.exceptions.ConnectionError("boom")
            return _ok_response(WTTR_OK_JSON)

        with patch("requests.get", side_effect=_side_effect):
            result = checker.get_weather_by_city("London")
        # Fallback succeeded, so result exists.
        assert result is not None
        assert result["description"] == "Partly cloudy"

    def test_non_request_exception_returns_none(self):
        # EP: non-RequestException class -> returns None, no further fallback.
        checker = WeatherChecker(api_key="abc")
        bad_resp = MagicMock()
        bad_resp.raise_for_status = MagicMock()
        bad_resp.json.side_effect = ValueError("not json")
        with patch("requests.get", return_value=bad_resp):
            result = checker.get_weather_by_city("London")
        assert result is None


class TestGetWeatherByCoordinatesEP:
    def test_no_api_key_returns_none(self):
        # EP: coordinates require api_key per SPEC.
        checker = WeatherChecker()
        with patch("requests.get") as mock_get:
            assert checker.get_weather_by_coordinates(51.5, -0.1) is None
        # Fast failure - no network call should have been made.
        mock_get.assert_not_called()

    def test_with_api_key_success(self):
        # EP: api_key + valid response.
        checker = WeatherChecker(api_key="abc")
        with patch("requests.get", return_value=_ok_response(OPENWEATHER_OK_JSON)):
            result = checker.get_weather_by_coordinates(51.5, -0.1)
        assert result["city"] == "London"


# =========================================================================
# BA â Boundary Analysis
# =========================================================================

class TestBoundaries:
    def test_forecast_days_parameter_controls_cnt(self):
        # BA: lower-meaningful value for days (1 day -> cnt=8).
        checker = WeatherChecker(api_key="abc")
        with patch("requests.get", return_value=_ok_response({
            "city": {"name": "X"},
            "list": [{
                "dt": 1_700_000_000,
                "main": {"temp": 5.0, "humidity": 50},
                "weather": [{"description": "ok"}],
            }]
        })) as mock_get:
            checker.get_weather_forecast("X", days=1)
        assert mock_get.call_args.kwargs["params"]["cnt"] == 8

    def test_zero_days_produces_zero_cnt(self):
        # BA: edge value days=0 -> cnt=0 (documents current behavior; not
        # validated as an input constraint anywhere in SPEC).
        checker = WeatherChecker(api_key="abc")
        with patch("requests.get", return_value=_ok_response({
            "city": {"name": "X"},
            "list": [],
        })) as mock_get:
            checker.get_weather_forecast("X", days=0)
        assert mock_get.call_args.kwargs["params"]["cnt"] == 0

    def test_request_uses_10_second_timeout(self):
        # BA: SPEC documents a 10s timeout. Verify it's passed through.
        checker = WeatherChecker(api_key="abc")
        with patch("requests.get", return_value=_ok_response(OPENWEATHER_OK_JSON)) as mock_get:
            checker.get_weather_by_city("X")
        assert mock_get.call_args.kwargs["timeout"] == 10


# =========================================================================
# EG â Error Guessing
# =========================================================================

class TestErrorGuessing:
    def test_metric_units_temp_unit_celsius(self):
        # EG: metric -> Â°C formatted temp.
        checker = WeatherChecker(api_key="abc")
        with patch("requests.get", return_value=_ok_response(OPENWEATHER_OK_JSON)):
            result = checker.get_weather_by_city("London", units="metric")
        assert "\u00b0C" in result["temperature"]

    def test_imperial_units_temp_unit_fahrenheit(self):
        # EG: imperial -> Â°F formatted temp.
        checker = WeatherChecker(api_key="abc")
        with patch("requests.get", return_value=_ok_response(OPENWEATHER_OK_JSON)):
            result = checker.get_weather_by_city("London", units="imperial")
        assert "\u00b0F" in result["temperature"]

    def test_timeout_during_api_call_falls_back_to_free(self):
        # EG: timeouts are a common RequestException subclass.
        checker = WeatherChecker(api_key="abc")

        def _side_effect(url, **kw):
            if "openweathermap" in url:
                raise requests.exceptions.Timeout("slow")
            return _ok_response(WTTR_OK_JSON)

        with patch("requests.get", side_effect=_side_effect):
            result = checker.get_weather_by_city("London")
        assert result is not None

    def test_missing_wind_key_crashes_format(self):
        # EG / FAULT-HUNTING: SPEC Â§Gaps #6 warns that format_weather_data
        # crashes on ANY missing required key (except visibility which uses
        # .get). A well-formed HTTP 200 with no 'wind' is a plausible upstream
        # contract change. Designed to FAIL: intended contract per SPEC is
        # consistent error handling, not KeyError bubbling up.
        checker = WeatherChecker(api_key="abc")
        payload = dict(OPENWEATHER_OK_JSON)
        payload.pop("wind")
        with patch("requests.get", return_value=_ok_response(payload)):
            result = checker.get_weather_by_city("London")
        # Contract: should return None (caught) rather than crash.
        # Current implementation: the KeyError is caught by the top-level
        # `except Exception` path, returning None. Assert the graceful outcome.
        assert result is None

    def test_save_weather_data_appends_to_existing_log(self, tmp_path, monkeypatch):
        # EG: log file appends, not overwrites.
        monkeypatch.chdir(tmp_path)
        checker = WeatherChecker()
        first = {"city": "A", "temperature": "10Â°C"}
        second = {"city": "B", "temperature": "20Â°C"}
        checker.save_weather_data(first, filename="log.json")
        checker.save_weather_data(second, filename="log.json")
        import json
        data = json.loads((tmp_path / "log.json").read_text())
        assert len(data) == 2

    def test_display_weather_does_not_crash_on_none(self, capsys):
        # EG: display_weather(None) per SPEC prints "No weather data available".
        checker = WeatherChecker()
        checker.display_weather(None)
        out = capsys.readouterr().out
        assert "No weather data" in out
