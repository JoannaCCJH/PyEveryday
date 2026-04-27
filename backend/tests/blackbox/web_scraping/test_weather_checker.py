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


# Defines the ok_response helper.
def _ok_response(payload):
    m = MagicMock()
    m.status_code = 200
    m.json.return_value = payload
    m.raise_for_status = MagicMock()
    return m


class TestGetWeatherByCityEP:
    # Tests with api key success.
    def test_with_api_key_success(self):
        checker = WeatherChecker(api_key="abc")
        with patch("requests.get", return_value=_ok_response(OPENWEATHER_OK_JSON)):
            result = checker.get_weather_by_city("London")
        assert result["city"] == "London"
        assert result["country"] == "GB"
        assert "10.5" in result["temperature"]

    # Tests without api key uses free fallback.
    def test_without_api_key_uses_free_fallback(self):
        checker = WeatherChecker()
        with patch("requests.get", return_value=_ok_response(WTTR_OK_JSON)) as mock_get:
            result = checker.get_weather_by_city("London")
        assert "wttr.in" in mock_get.call_args.args[0]
        assert result["description"] == "Partly cloudy"

    # Tests request exception falls back to free.
    def test_request_exception_falls_back_to_free(self):
        checker = WeatherChecker(api_key="abc")

        # Defines the side_effect helper.
        def _side_effect(url, **kw):
            if "openweathermap" in url:
                raise requests.exceptions.ConnectionError("boom")
            return _ok_response(WTTR_OK_JSON)
        with patch("requests.get", side_effect=_side_effect):
            result = checker.get_weather_by_city("London")
        assert result is not None
        assert result["description"] == "Partly cloudy"

    # Tests non request exception returns none.
    def test_non_request_exception_returns_none(self):
        checker = WeatherChecker(api_key="abc")
        bad_resp = MagicMock()
        bad_resp.raise_for_status = MagicMock()
        bad_resp.json.side_effect = ValueError("not json")
        with patch("requests.get", return_value=bad_resp):
            result = checker.get_weather_by_city("London")
        assert result is None


class TestGetWeatherByCoordinatesEP:
    # Tests no api key returns none.
    def test_no_api_key_returns_none(self):
        checker = WeatherChecker()
        with patch("requests.get") as mock_get:
            assert checker.get_weather_by_coordinates(51.5, -0.1) is None
        mock_get.assert_not_called()

    # Tests with api key success.
    def test_with_api_key_success(self):
        checker = WeatherChecker(api_key="abc")
        with patch("requests.get", return_value=_ok_response(OPENWEATHER_OK_JSON)):
            result = checker.get_weather_by_coordinates(51.5, -0.1)
        assert result["city"] == "London"


class TestBoundaries:
    # Tests forecast days parameter controls cnt.
    def test_forecast_days_parameter_controls_cnt(self):
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

    # Tests zero days produces zero cnt.
    def test_zero_days_produces_zero_cnt(self):
        checker = WeatherChecker(api_key="abc")
        with patch("requests.get", return_value=_ok_response({
            "city": {"name": "X"},
            "list": [],
        })) as mock_get:
            checker.get_weather_forecast("X", days=0)
        assert mock_get.call_args.kwargs["params"]["cnt"] == 0

    # Tests request uses 10 second timeout.
    def test_request_uses_10_second_timeout(self):
        checker = WeatherChecker(api_key="abc")
        with patch("requests.get", return_value=_ok_response(OPENWEATHER_OK_JSON)) as mock_get:
            checker.get_weather_by_city("X")
        assert mock_get.call_args.kwargs["timeout"] == 10


class TestErrorGuessing:
    # Tests metric units temp unit celsius.
    def test_metric_units_temp_unit_celsius(self):
        checker = WeatherChecker(api_key="abc")
        with patch("requests.get", return_value=_ok_response(OPENWEATHER_OK_JSON)):
            result = checker.get_weather_by_city("London", units="metric")
        assert "\u00b0C" in result["temperature"]
        assert result["wind_speed"].endswith("m/s")

    # Tests imperial units temp unit fahrenheit.
    def test_imperial_units_temp_unit_fahrenheit(self):
        checker = WeatherChecker(api_key="abc")
        with patch("requests.get", return_value=_ok_response(OPENWEATHER_OK_JSON)):
            result = checker.get_weather_by_city("London", units="imperial")
        assert "\u00b0F" in result["temperature"]

    # Tests timeout during api call falls back to free.
    def test_timeout_during_api_call_falls_back_to_free(self):
        checker = WeatherChecker(api_key="abc")

        # Defines the side_effect helper.
        def _side_effect(url, **kw):
            if "openweathermap" in url:
                raise requests.exceptions.Timeout("slow")
            return _ok_response(WTTR_OK_JSON)
        with patch("requests.get", side_effect=_side_effect):
            result = checker.get_weather_by_city("London")
        assert result is not None

    # Tests missing wind key crashes format.
    def test_missing_wind_key_crashes_format(self):
        checker = WeatherChecker(api_key="abc")
        payload = dict(OPENWEATHER_OK_JSON)
        payload.pop("wind")
        with patch("requests.get", return_value=_ok_response(payload)):
            result = checker.get_weather_by_city("London")
        assert result is None

    # Tests save weather data appends to existing log.
    def test_save_weather_data_appends_to_existing_log(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        checker = WeatherChecker()
        first = {"city": "A", "temperature": "10Â°C"}
        second = {"city": "B", "temperature": "20Â°C"}
        checker.save_weather_data(first, filename="log.json")
        checker.save_weather_data(second, filename="log.json")

        import json

        data = json.loads((tmp_path / "log.json").read_text())
        assert len(data) == 2

    # Tests display weather does not crash on none.
    def test_display_weather_does_not_crash_on_none(self, capsys):
        checker = WeatherChecker()
        checker.display_weather(None)
        out = capsys.readouterr().out
        assert "No weather data" in out

    def test_forecast_metric_temperature_uses_celsius(self):
        checker = WeatherChecker(api_key="abc")
        payload = {
            "city": {"name": "X"},
            "list": [{
                "dt": 1_700_000_000,
                "main": {"temp": 5.0, "humidity": 50},
                "weather": [{"description": "ok"}],
            }],
        }
        with patch("requests.get", return_value=_ok_response(payload)):
            result = checker.get_weather_forecast("X", days=1, units="metric")
        assert result["forecast"][0]["temperature"].endswith("°C")

    def test_forecast_imperial_temperature_uses_fahrenheit(self):
        checker = WeatherChecker(api_key="abc")
        payload = {
            "city": {"name": "X"},
            "list": [{
                "dt": 1_700_000_000,
                "main": {"temp": 70.0, "humidity": 50},
                "weather": [{"description": "ok"}],
            }],
        }
        with patch("requests.get", return_value=_ok_response(payload)):
            result = checker.get_weather_forecast("X", days=1, units="imperial")
        assert result["forecast"][0]["temperature"].endswith("°F")
