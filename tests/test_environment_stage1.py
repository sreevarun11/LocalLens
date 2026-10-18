import unittest
from datetime import datetime
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.providers.environment import (
    OpenMeteoAirQualityProvider,
    OpenAQAirQualityProvider,
    compute_pm25_aqi,
    WMO_WEATHER_CODES
)
from backend.app.schemas.modules import AirQualityData, WeatherData
from backend.app.schemas.base import ModuleResult

client = TestClient(app)

class TestEnvironmentStage1(unittest.TestCase):
    def test_pm25_aqi_computation(self):
        """Verifies standard US EPA AQI piecewise linear computation."""
        # Good category: 0 - 12 µg/m³ -> 0 - 50 AQI
        self.assertEqual(compute_pm25_aqi(0.0), 0)
        self.assertEqual(compute_pm25_aqi(12.0), 50)
        # Moderate category: 12.1 - 35.4 µg/m³ -> 51 - 100 AQI
        self.assertTrue(51 <= compute_pm25_aqi(25.0) <= 100)
        # Unhealthy category: 55.5 - 150.4 µg/m³ -> 151 - 200 AQI
        self.assertTrue(151 <= compute_pm25_aqi(75.0) <= 200)

    def test_wmo_weather_codes(self):
        """Verifies clear descriptive strings for common WMO weather codes."""
        self.assertEqual(WMO_WEATHER_CODES.get(0), "Clear sky")
        self.assertEqual(WMO_WEATHER_CODES.get(2), "Partly cloudy")
        self.assertEqual(WMO_WEATHER_CODES.get(61), "Slight rain")
        self.assertEqual(WMO_WEATHER_CODES.get(95), "Thunderstorm")

    def test_open_meteo_live_weather_and_air_quality(self):
        """Verifies live Open-Meteo endpoint returns both weather and air quality for Telangana coordinates."""
        # Charminar, Hyderabad
        resp = client.get("/api/modules/environment?lat=17.3616&lng=78.4747")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["module"], "environment")
        self.assertIn(data["status"], ["available", "limited"])
        self.assertEqual(data["provenance_kind"], "modeled_estimate")

        env_data = data["data"]
        self.assertIsNotNone(env_data)

        # Weather attributes
        self.assertIn("temperature_c", env_data)
        self.assertIsInstance(env_data["temperature_c"], (int, float))
        self.assertIn("humidity_pct", env_data)
        self.assertIn("weather_desc", env_data)
        self.assertIn("weather", env_data)
        if env_data["weather"]:
            self.assertIn("wind_speed_kmh", env_data["weather"])
            self.assertIn("uv_index", env_data["weather"])

        # Air quality attributes
        self.assertIn("aqi", env_data)
        self.assertIn("pm25", env_data)
        self.assertIn("pm10", env_data)

        # Provenance and model grid disclosures
        self.assertEqual(data["coverage"]["granularity"], "city")
        lim_str = " ".join(data["limitations"])
        self.assertIn("Modeled estimate", lim_str)
        self.assertTrue("~40 km" in lim_str or "~11 km" in lim_str, "Limitations must disclose regional grid resolution")

    def test_openaq_unconfigured_auth_fallback(self):
        """Verifies OpenAQ provider returns clean unavailable state when API key is missing."""
        provider = OpenAQAirQualityProvider(api_key=None)
        import asyncio
        res = asyncio.run(provider.get_air_quality(17.3616, 78.4747))
        self.assertEqual(res.status, "unavailable")
        self.assertEqual(res.provenance_kind, "station_measurement")
        self.assertIn("API key is not configured", res.limitations[0])

    def test_openaq_station_distance_filtering(self):
        """Verifies station distance threshold enforces 25 km association boundary."""
        provider = OpenAQAirQualityProvider(api_key="mock_test_key", max_distance_m=25000)
        self.assertEqual(provider.max_distance_m, 25000)

    def test_weather_data_schema_missing_fields_safe(self):
        """Verifies WeatherData model instantiates safely with missing or null fields."""
        w = WeatherData()
        self.assertIsNone(w.temperature_c)
        self.assertIsNone(w.humidity_pct)
        self.assertIsNone(w.weather_desc)

        aq = AirQualityData(weather=w)
        self.assertIsNone(aq.aqi)
        self.assertEqual(aq.aqi_scale, "US AQI")
        self.assertIsNotNone(aq.weather)

if __name__ == "__main__":
    unittest.main()
