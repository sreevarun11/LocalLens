import os
import json
import httpx
import logging
import asyncio
from datetime import datetime
from typing import Literal, Any
from shapely.geometry import shape, Point
from backend.app.providers.base import AirQualityProvider, WaterQualityProvider, CrimeProvider, StoragePolicy
from backend.app.schemas.base import ModuleResult, DataSourceInfo, Coverage
from backend.app.schemas.modules import AirQualityData, WeatherData, WaterQualityData, CrimeData
from backend.app.schemas.location import Coordinates
from backend.app.utils.geo import haversine_distance_m
from backend.app.config import settings

WMO_WEATHER_CODES: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail"
}

def compute_pm25_aqi(pm25: float) -> int:
    """Computes US EPA AQI index from PM2.5 concentration in µg/m³."""
    if pm25 < 0:
        return 0
    breakpoints = [
        (0.0, 12.0, 0, 50),
        (12.1, 35.4, 51, 100),
        (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200),
        (150.5, 250.4, 201, 300),
        (250.5, 350.4, 301, 400),
        (350.5, 500.4, 401, 500),
    ]
    for c_low, c_high, i_low, i_high in breakpoints:
        if c_low <= pm25 <= c_high:
            return int(round(((i_high - i_low) / (c_high - c_low)) * (pm25 - c_low) + i_low))
    return 500


def get_cams_model_metadata(lat: float, lng: float) -> dict[str, Any]:
    """
    Determines the applicable Copernicus Atmosphere Monitoring Service (CAMS)
    model domain, name, and resolution based on geographic coordinates.
    - Europe (lat 34-72, lng -25-45): CAMS European Regional Ensemble (~0.1° / ~11 km)
    - Global / India: CAMS Global Atmospheric Model (ECMWF IFS, ~0.4° / ~40 km)
    """
    is_europe = (34.0 <= lat <= 72.0) and (-25.0 <= lng <= 45.0)
    if is_europe:
        return {
            "domain": "cams_europe",
            "model_name": "Copernicus CAMS European Regional Ensemble",
            "resolution_km": 11.0,
            "description": "European CAMS regional ensemble model (~11 km grid)",
            "coverage_note": "Grid cell ~11 km resolution from Copernicus CAMS European Regional Ensemble and Open-Meteo forecast."
        }
    return {
        "domain": "cams_global",
        "model_name": "Copernicus CAMS Global (ECMWF IFS)",
        "resolution_km": 40.0,
        "description": "ECMWF CAMS Global atmospheric model (~0.4° / ~40 km grid)",
        "coverage_note": "Grid cell ~40 km (~0.4°) resolution from Copernicus CAMS Global atmospheric model (ECMWF IFS) and Open-Meteo forecast."
    }


class OpenMeteoAirQualityProvider(AirQualityProvider):
    """
    Open-Meteo Air Quality & Weather Provider.
    Based on European Copernicus CAMS atmospheric models and Open-Meteo Weather models.
    Storage policy: storable.
    Provenance kind: modeled_estimate.
    """
    @property
    def name(self) -> str:
        return "Open-Meteo Weather & Copernicus Atmosphere Model"

    @property
    def license(self) -> str:
        return "Open-Meteo Terms / Copernicus Atmosphere Monitoring Service"

    @property
    def attribution_url(self) -> str:
        return "https://open-meteo.com"

    @property
    def storage_policy(self) -> StoragePolicy:
        return "storable"

    @property
    def max_results(self) -> int:
        return 1

    @property
    def capabilities(self) -> list[str]:
        return [
            "pm2_5", "pm10", "us_aqi", "european_aqi",
            "temperature", "humidity", "wind", "precipitation", "uv_index"
        ]

    async def get_air_quality(self, lat: float, lng: float) -> ModuleResult[AirQualityData]:
        url_aq = "https://air-quality-api.open-meteo.com/v1/air-quality"
        params_aq = {
            "latitude": lat,
            "longitude": lng,
            "current": "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone,us_aqi,european_aqi"
        }

        url_w = "https://api.open-meteo.com/v1/forecast"
        params_w = {
            "latitude": lat,
            "longitude": lng,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m",
            "hourly": "uv_index,precipitation_probability",
            "timezone": "auto",
            "forecast_days": 1
        }

        source_info = self.get_data_source_info()
        headers = {"User-Agent": "LocalLens/4.0 (contact: info@locallens.app)"}

        aq_data_dict: dict = {}
        weather_data_dict: dict = {}
        measured_at = None

        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                res_aq, res_w = await asyncio.gather(
                    client.get(url_aq, params=params_aq, headers=headers),
                    client.get(url_w, params=params_w, headers=headers),
                    return_exceptions=True
                )

                if isinstance(res_aq, httpx.Response) and res_aq.status_code == 200:
                    aq_data_dict = res_aq.json().get("current", {})
                    measured_iso = aq_data_dict.get("time")
                    if measured_iso:
                        try:
                            measured_at = datetime.fromisoformat(measured_iso)
                        except Exception:
                            measured_at = None

                if isinstance(res_w, httpx.Response) and res_w.status_code == 200:
                    weather_data_dict = res_w.json()

        except Exception as e:
            logger.error(f"Open-Meteo network error: {e}")

        # Parse weather details if available
        weather_obj: WeatherData | None = None
        temp_c = None
        app_temp_c = None
        humidity_pct = None
        wind_speed = None
        precip_prob = None
        uv_idx = None
        weather_desc = None

        if weather_data_dict:
            w_curr = weather_data_dict.get("current", {})
            w_code = w_curr.get("weather_code")
            weather_desc = WMO_WEATHER_CODES.get(w_code, "Fair" if w_code is not None else None)
            temp_c = w_curr.get("temperature_2m")
            app_temp_c = w_curr.get("apparent_temperature_c", w_curr.get("apparent_temperature"))
            humidity_pct = w_curr.get("relative_humidity_2m")
            wind_speed = w_curr.get("wind_speed_10m")

            # Extract current hour UV and precipitation probability from hourly forecast
            hourly = weather_data_dict.get("hourly", {})
            times = hourly.get("time", [])
            uv_list = hourly.get("uv_index", [])
            prob_list = hourly.get("precipitation_probability", [])
            curr_hour = str(w_curr.get("time", ""))[:13]

            if times and curr_hour:
                for idx, t in enumerate(times):
                    if t.startswith(curr_hour):
                        if idx < len(uv_list):
                            uv_idx = uv_list[idx]
                        if idx < len(prob_list):
                            precip_prob = prob_list[idx]
                        break

            if uv_idx is None and uv_list:
                uv_idx = uv_list[0]
            if precip_prob is None and prob_list:
                precip_prob = prob_list[0]

            weather_obj = WeatherData(
                temperature_c=temp_c,
                apparent_temperature_c=app_temp_c,
                humidity_pct=humidity_pct,
                wind_speed_kmh=wind_speed,
                wind_direction_deg=w_curr.get("wind_direction_10m"),
                precipitation_mm=w_curr.get("precipitation"),
                precipitation_probability_pct=precip_prob,
                uv_index=uv_idx,
                weather_desc=weather_desc,
                forecast_time=w_curr.get("time")
            )

        cams_meta = get_cams_model_metadata(lat, lng)

        # Build AirQualityData model
        aq_data = AirQualityData(
            aqi=aq_data_dict.get("us_aqi"),
            aqi_scale="US AQI",
            pm25=aq_data_dict.get("pm2_5"),
            pm10=aq_data_dict.get("pm10"),
            co=aq_data_dict.get("carbon_monoxide"),
            no2=aq_data_dict.get("nitrogen_dioxide"),
            so2=aq_data_dict.get("sulphur_dioxide"),
            o3=aq_data_dict.get("ozone"),
            model_grid_resolution_km=cams_meta["resolution_km"],
            advisory=f"Ambient atmospheric values are modeled regional estimates from {cams_meta['model_name']}.",
            weather=weather_obj,
            temperature_c=temp_c,
            apparent_temperature_c=app_temp_c,
            humidity_pct=humidity_pct,
            wind_speed_kmh=wind_speed,
            precipitation_probability_pct=precip_prob,
            uv_index=uv_idx,
            weather_desc=weather_desc
        )

        has_aqi = aq_data.aqi is not None
        has_weather = weather_obj is not None

        if not has_aqi and not has_weather:
            return ModuleResult[AirQualityData](
                module="environment",
                status="error",
                provenance_kind="modeled_estimate",
                data=None,
                sources=[source_info],
                coverage=Coverage(granularity="unknown"),
                fetched_at=datetime.utcnow(),
                limitations=["Open-Meteo service was unreachable."],
                message="Environmental air quality and weather service temporarily unavailable."
            )

        status: Literal["available", "limited"] = "available" if (has_aqi and has_weather) else "limited"
        limitations = [
            "Modeled estimate — not an on-site property monitoring sensor.",
            f"Measurement represents regional atmospheric grid ({cams_meta['description']}) and may not reflect microclimates or street-level dust.",
            "Weather metrics are numerical atmospheric model forecasts for the selected coordinates."
        ]

        return ModuleResult[AirQualityData](
            module="environment",
            status=status,
            provenance_kind="modeled_estimate",
            data=aq_data,
            sources=[source_info],
            coverage=Coverage(
                granularity="city",
                radius_m=int(cams_meta["resolution_km"] * 1000),
                note=cams_meta["coverage_note"]
            ),
            fetched_at=datetime.utcnow(),
            measured_at=measured_at or datetime.utcnow(),
            source_updated_at=measured_at,
            limitations=limitations
        )


class OpenAQAirQualityProvider(AirQualityProvider):
    """
    OpenAQ v3 Provider.
    Ground station physical measurements.
    Requires OPENAQ_API_KEY.
    """
    def __init__(self, api_key: str | None = None, max_distance_m: int = 25000):
        self.api_key = api_key or settings.OPENAQ_API_KEY
        self.max_distance_m = max_distance_m

    @property
    def name(self) -> str:
        return "OpenAQ Ground Stations"

    @property
    def license(self) -> str:
        return "Creative Commons Attribution 4.0 (CC BY 4.0)"

    @property
    def attribution_url(self) -> str:
        return "https://openaq.org"

    @property
    def storage_policy(self) -> StoragePolicy:
        return "storable"

    @property
    def max_results(self) -> int:
        return 1

    @property
    def capabilities(self) -> list[str]:
        return ["station_pm2_5", "station_pm10", "sensor_metadata"]

    async def get_air_quality(self, lat: float, lng: float) -> ModuleResult[AirQualityData]:
        source_info = self.get_data_source_info()
        if not self.api_key:
            return ModuleResult[AirQualityData](
                module="environment",
                status="unavailable",
                provenance_kind="station_measurement",
                data=None,
                sources=[source_info],
                coverage=Coverage(granularity="monitoring_station"),
                fetched_at=datetime.utcnow(),
                limitations=["OpenAQ API key is not configured in backend environment."],
                message="OpenAQ station measurements unavailable: API key not configured."
            )

        url_locations = "https://api.openaq.org/v3/locations"
        headers = {
            "X-API-Key": self.api_key,
            "User-Agent": "LocalLens/4.0 (contact: info@locallens.app)"
        }
        params = {
            "coordinates": f"{lat},{lng}",
            "radius": self.max_distance_m,
            "order_by": "distance",
            "sort_order": "asc",
            "limit": 3
        }

        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(url_locations, params=params, headers=headers)
                if resp.status_code == 401:
                    logger.warning("OpenAQ authentication failed (HTTP 401). Check OPENAQ_API_KEY.")
                    return ModuleResult[AirQualityData](
                        module="environment",
                        status="unavailable",
                        provenance_kind="station_measurement",
                        data=None,
                        sources=[source_info],
                        coverage=Coverage(granularity="monitoring_station"),
                        fetched_at=datetime.utcnow(),
                        limitations=["OpenAQ API key authentication failed."],
                        message="OpenAQ authentication failed."
                    )

                if resp.status_code != 200:
                    logger.warning(f"OpenAQ returned HTTP {resp.status_code}")
                    return ModuleResult[AirQualityData](
                        module="environment",
                        status="unavailable",
                        provenance_kind="station_measurement",
                        data=None,
                        sources=[source_info],
                        coverage=Coverage(granularity="monitoring_station"),
                        fetched_at=datetime.utcnow(),
                        limitations=[f"OpenAQ request failed with HTTP {resp.status_code}."],
                        message="OpenAQ request failed."
                    )

                data = resp.json()
                results = data.get("results", [])
                if not results:
                    return ModuleResult[AirQualityData](
                        module="environment",
                        status="unavailable",
                        provenance_kind="station_measurement",
                        data=None,
                        sources=[source_info],
                        coverage=Coverage(granularity="monitoring_station"),
                        fetched_at=datetime.utcnow(),
                        limitations=[f"No physical monitoring station found within {int(self.max_distance_m / 1000)} km."],
                        message=f"No monitoring station active within {int(self.max_distance_m / 1000)} km of this locality."
                    )

                # Nearest physical station
                nearest_loc = results[0]
                station_name = nearest_loc.get("name") or "Physical Monitoring Station"
                loc_id = nearest_loc.get("id")
                coords = nearest_loc.get("coordinates", {})
                st_lat = coords.get("latitude")
                st_lng = coords.get("longitude")

                dist_m = nearest_loc.get("distance")
                if dist_m is None and st_lat is not None and st_lng is not None:
                    dist_m = haversine_distance_m(lat, lng, st_lat, st_lng)
                dist_m = int(round(dist_m)) if dist_m is not None else None

                if dist_m is not None and dist_m > self.max_distance_m:
                    return ModuleResult[AirQualityData](
                        module="environment",
                        status="unavailable",
                        provenance_kind="station_measurement",
                        data=None,
                        sources=[source_info],
                        coverage=Coverage(granularity="monitoring_station"),
                        fetched_at=datetime.utcnow(),
                        limitations=[f"Nearest physical station '{station_name}' is {dist_m}m away (exceeds {int(self.max_distance_m / 1000)} km threshold)."],
                        message="Nearest station is beyond supported association distance."
                    )

                # Fetch latest readings for this station
                url_latest = f"https://api.openaq.org/v3/locations/{loc_id}/latest"
                resp_latest = await client.get(url_latest, headers=headers)
                measurements = {}
                measured_at = None

                if resp_latest.status_code == 200:
                    latest_data = resp_latest.json()
                    for item in latest_data.get("results", []):
                        param = item.get("parameter", {}).get("name", "").lower()
                        val = item.get("value")
                        if param and val is not None:
                            measurements[param] = val
                        dt_obj = item.get("datetime", {})
                        iso_str = dt_obj.get("utc") or dt_obj.get("local")
                        if iso_str and not measured_at:
                            try:
                                measured_at = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
                            except Exception:
                                measured_at = None

                pm25 = measurements.get("pm25") or measurements.get("pm2.5")
                pm10 = measurements.get("pm10")
                no2 = measurements.get("no2")
                so2 = measurements.get("so2")
                o3 = measurements.get("o3") or measurements.get("ozone")
                co = measurements.get("co")

                aqi = compute_pm25_aqi(pm25) if pm25 is not None else None

                aq_data = AirQualityData(
                    aqi=aqi,
                    aqi_scale="US AQI",
                    pm25=pm25,
                    pm10=pm10,
                    co=co,
                    no2=no2,
                    so2=so2,
                    o3=o3,
                    station_name=station_name,
                    station_distance_m=dist_m,
                    station_coordinates=Coordinates(lat=st_lat, lng=st_lng) if st_lat and st_lng else None,
                    advisory=f"Physical ground station observation from '{station_name}' ({round(dist_m / 1000.0, 1) if dist_m else '—'} km away)."
                )

                return ModuleResult[AirQualityData](
                    module="environment",
                    status="available" if (aqi is not None or pm25 is not None) else "limited",
                    provenance_kind="station_measurement",
                    data=aq_data,
                    sources=[source_info],
                    coverage=Coverage(
                        granularity="monitoring_station",
                        station_distance_m=dist_m,
                        nearest_distance_m=dist_m
                    ),
                    fetched_at=datetime.utcnow(),
                    measured_at=measured_at,
                    source_updated_at=measured_at,
                    limitations=[
                        f"Physical station readings from '{station_name}' located {dist_m}m away.",
                        "Air quality varies street by street; physical station measurements reflect the station location and not every microclimate."
                    ]
                )

        except Exception as e:
            logger.error(f"OpenAQ provider error: {e}")
            return ModuleResult[AirQualityData](
                module="environment",
                status="error",
                provenance_kind="station_measurement",
                data=None,
                sources=[source_info],
                coverage=Coverage(granularity="monitoring_station"),
                fetched_at=datetime.utcnow(),
                limitations=["OpenAQ service encountered a connection error."],
                message="OpenAQ ground station service temporarily unavailable."
            )


class TelanganaWaterQualityProvider(WaterQualityProvider):
    """
    Official Groundwater Resources & Water Table Provider for Telangana.
    Sourced from:
    1. 'Dynamic Ground Water Resources of Telangana State' (GWRA 2022 / Water Year 2021-22),
       jointly published by Ground Water Department, Government of Telangana &
       Central Ground Water Board (CGWB), Department of Water Resources, RD & GR, Ministry of Jal Shakti, Government of India.
    2. 'National Compilation on Dynamic Ground Water Resources of India, 2023 / 2024',
       Central Ground Water Board, Ministry of Jal Shakti.
    3. Official 33-district boundaries GeoJSON (udit-001 / Survey of India).
    """
    def __init__(self):
        self._loaded = False
        self._dataset: dict | None = None
        self._district_polygons: list[tuple[str, any]] = []
        self._init_data()

    def _init_data(self):
        if self._loaded:
            return
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = os.path.join(backend_dir, "data")
        water_json_path = os.path.join(data_dir, "telangana_water_resources.json")
        geojson_path = os.path.join(data_dir, "telangana_districts.geojson")

        if os.path.exists(water_json_path):
            try:
                with open(water_json_path, "r", encoding="utf-8") as f:
                    self._dataset = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load telangana_water_resources.json: {e}")

        if os.path.exists(geojson_path):
            try:
                with open(geojson_path, "r", encoding="utf-8") as f:
                    gj = json.load(f)
                for feat in gj.get("features", []):
                    dname = feat.get("properties", {}).get("district")
                    geom = feat.get("geometry")
                    if dname and geom:
                        self._district_polygons.append((dname, shape(geom)))
            except Exception as e:
                logger.error(f"Failed to load telangana_districts.geojson: {e}")

        self._loaded = True

    @property
    def name(self) -> str:
        return "Central Ground Water Board (CGWB) & Ground Water Department, Govt. of Telangana"

    @property
    def license(self) -> str:
        return "National Data Sharing and Accessibility Policy (NDSAP)"

    @property
    def attribution_url(self) -> str:
        return "https://cgwb.gov.in/old_website/GW-Assessment/GWR-2022-Reports%20State/Telangana.pdf"

    @property
    def storage_policy(self) -> StoragePolicy:
        return "storable"

    @property
    def max_results(self) -> int:
        return 1

    @property
    def capabilities(self) -> list[str]:
        return ["district_assessment", "groundwater_extraction_stage", "mandal_categorization", "water_table_depth"]

    def _normalize_name(self, name: str) -> str:
        import re
        return re.sub(r'[^a-z0-9\s]', ' ', name.lower()).strip()

    def _match_district(self, lat: float, lng: float) -> str | None:
        self._init_data()
        pt = Point(lng, lat)
        for dname, poly in self._district_polygons:
            if poly.contains(pt):
                return dname
        # Buffer tolerance for boundary points within ~0.02 deg (~2.2 km)
        for dname, poly in self._district_polygons:
            if poly.buffer(0.02).contains(pt):
                return dname
        return None

    def _find_district_record(self, district_name: str) -> tuple[str | None, dict | None]:
        if not self._dataset or "districts" not in self._dataset:
            return None, None
        districts = self._dataset["districts"]
        if district_name in districts:
            return district_name, districts[district_name]

        norm_target = self._normalize_name(district_name)
        aliases = {
            "ranga reddy": "Ranga Reddy",
            "rangareddy": "Ranga Reddy",
            "medchal": "Medchal Malkajgiri",
            "medchal malkajgiri": "Medchal Malkajgiri",
            "warangal": "Warangal",
            "warangal urban": "Hanumakonda",
            "warangal rural": "Warangal",
            "hanumakonda": "Hanumakonda",
            "komaram bheem": "Komaram Bheem",
            "komarambheem asifabad": "Komaram Bheem",
            "rajanna sircilla": "Rajanna Sircilla",
            "rajanna siricilla": "Rajanna Sircilla",
            "yadadri": "Yadadri Bhuvanagiri",
            "yadadri bhuvanagiri": "Yadadri Bhuvanagiri",
            "jogulamba": "Jogulamba Gadwal",
            "jogulamba gadwal": "Jogulamba Gadwal",
            "jayashankar": "Jayashankar Bhupalapally",
            "jayashankar bhupalapally": "Jayashankar Bhupalapally",
            "bhadradri": "Bhadradri Kothagudem",
            "bhadradri kothagudem": "Bhadradri Kothagudem"
        }
        if norm_target in aliases:
            canonical = aliases[norm_target]
            if canonical in districts:
                return canonical, districts[canonical]

        for k, v in districts.items():
            if self._normalize_name(k) == norm_target:
                return k, v
        return None, None

    async def get_water_quality(self, lat: float, lng: float, locality: str | None = None) -> ModuleResult[WaterQualityData]:
        self._init_data()
        source_info = self.get_data_source_info()

        if not self._dataset or not self._district_polygons:
            return ModuleResult[WaterQualityData](
                module="water",
                status="unavailable",
                provenance_kind="official_dataset",
                data=None,
                sources=[source_info],
                coverage=Coverage(granularity="district"),
                fetched_at=datetime.utcnow(),
                limitations=["Official water resources dataset not initialized."],
                message="Official Telangana groundwater resource dataset file not found."
            )

        matched_dname = self._match_district(lat, lng)
        if not matched_dname:
            return ModuleResult[WaterQualityData](
                module="water",
                status="unavailable",
                provenance_kind="official_dataset",
                data=None,
                sources=[source_info],
                coverage=Coverage(granularity="district"),
                fetched_at=datetime.utcnow(),
                limitations=[
                    "Location coordinates fall outside Telangana state boundaries.",
                    "Official CGWB Telangana groundwater dataset only covers districts within Telangana state."
                ],
                message="Official CGWB Telangana water resources dataset covers Telangana state only. This location is outside Telangana."
            )

        canonical_dname, d_rec = self._find_district_record(matched_dname)
        if not d_rec:
            return ModuleResult[WaterQualityData](
                module="water",
                status="limited",
                provenance_kind="official_dataset",
                data=None,
                sources=[source_info],
                coverage=Coverage(granularity="district"),
                fetched_at=datetime.utcnow(),
                limitations=[f"District '{matched_dname}' identified but official assessment table entry missing."],
                message=f"Official records incomplete for district '{matched_dname}'."
            )

        # Mandal-level resolution with verified district constraint and exact token/alias matching
        mandal_name = None
        mandal_category = None
        data_level: Literal["mandal", "district"] = "district"
        ocs_mandals = self._dataset.get("ocs_mandals", {})
        urban_locality_map = self._dataset.get("urban_locality_map", {})

        if locality:
            norm_loc = self._normalize_name(locality)
            loc_tokens = set(norm_loc.split())

            # 1. Check validated urban locality-to-mandal mappings within the matched district
            matched_m_key = None
            if norm_loc in urban_locality_map:
                map_entry = urban_locality_map[norm_loc]
                if self._normalize_name(map_entry.get("district", "")) == self._normalize_name(canonical_dname):
                    matched_m_key = map_entry.get("mandal")
            else:
                for token in loc_tokens:
                    if token in urban_locality_map:
                        map_entry = urban_locality_map[token]
                        if self._normalize_name(map_entry.get("district", "")) == self._normalize_name(canonical_dname):
                            matched_m_key = map_entry.get("mandal")
                            break

            # 2. Check OCS mandals registry belonging strictly to this district
            if not matched_m_key:
                for m_key, m_val in ocs_mandals.items():
                    if self._normalize_name(m_val.get("district", "")) == self._normalize_name(canonical_dname):
                        if norm_loc == m_key or m_key in loc_tokens or norm_loc.startswith(f"{m_key} ") or norm_loc.endswith(f" {m_key}"):
                            matched_m_key = m_key
                            break

            if matched_m_key and matched_m_key in ocs_mandals:
                m_info = ocs_mandals[matched_m_key]
                mandal_name = matched_m_key.title()
                mandal_category = m_info.get("category")
                data_level = "mandal"

        assessment_cat = mandal_category or d_rec.get("category", "Safe")

        m_counts = d_rec.get("mandals", {})
        total_m = m_counts.get("total", 0)
        safe_m = m_counts.get("safe", 0)
        semi_m = m_counts.get("semi_critical", 0)
        crit_m = m_counts.get("critical", 0)
        oe_m = m_counts.get("over_exploited", 0)

        summary_parts = [f"{safe_m}/{total_m} Safe"]
        if semi_m > 0:
            summary_parts.append(f"{semi_m} Semi-Critical")
        if crit_m > 0:
            summary_parts.append(f"{crit_m} Critical")
        if oe_m > 0:
            summary_parts.append(f"{oe_m} Over-Exploited")
        mandals_summary_text = f"{canonical_dname} District ({', '.join(summary_parts)})"

        meta = self._dataset.get("metadata", {})
        rep_year = meta.get("reporting_period", "Assessment Year 2022 (As on May, 2022 / Water Year 2021-22)")
        methodology = meta.get("methodology", "Ground Water Resource Estimation Committee (GEC-2015) Norms via IN-GRES")
        pub_title = meta.get("title", "Dynamic Ground Water Resources of Telangana State (2022)")
        disclaimer = meta.get("mandatory_limitation")

        # Crucial integrity check: If at mandal level, do NOT present district SOE as mandal SOE
        district_soe = d_rec.get("soe_pct")
        if data_level == "mandal":
            stage_of_extraction = None  # Mandal-specific numeric % not published in summary table
            mandal_soe = None
            geo_res_label = f"Mandal: {mandal_name} (Categorization) / District: {canonical_dname} (Extraction Balance)"
        else:
            stage_of_extraction = district_soe
            mandal_soe = None
            geo_res_label = f"District: {canonical_dname} (Regional Aggregate)"

        water_data = WaterQualityData(
            sample_count=total_m,
            data_level=data_level,
            district_name=canonical_dname,
            district_code=d_rec.get("dt_code"),
            mandal_name=mandal_name,
            assessment_category=assessment_cat,
            stage_of_extraction_pct=stage_of_extraction,
            mandal_stage_of_extraction_pct=mandal_soe,
            district_stage_of_extraction_pct=district_soe,
            annual_extractable_ham=d_rec.get("extractable_ham"),
            annual_extraction_ham=d_rec.get("annual_extraction_ham"),
            water_table_pre_monsoon_mbgl=d_rec.get("water_table_pre_mbgl"),
            water_table_post_monsoon_mbgl=d_rec.get("water_table_post_mbgl"),
            seasonal_water_table_rise_m=d_rec.get("seasonal_rise_m"),
            reporting_year=rep_year,
            assessment_methodology=methodology,
            mandals_summary=mandals_summary_text,
            tds_range_mg_l=d_rec.get("tds_range_mg_l"),
            ph_range=d_rec.get("ph_range"),
            is_historical_baseline=True,
            dataset_publication=f"CGWB & TGWD {pub_title}",
            geographic_resolution=geo_res_label,
            disclaimer=disclaimer
        )

        measured_at_dt = datetime(2022, 5, 31, 0, 0, 0)
        source_updated_dt = datetime(2024, 1, 15, 0, 0, 0)

        specific_limitations = [
            "Groundwater assessment categories (Safe / Semi-Critical / Critical / Over-Exploited) evaluate regional aquifer recharge vs extraction balances and do NOT certify drinking-water potability.",
            "Never claim or assume groundwater is safe to drink solely because an assessment category is Safe.",
            "Regional groundwater chemistry (TDS and pH) reflects ambient monitoring well baselines from CGWB network, not municipal tap supply.",
            "Building-level tap-water quality, Krishna/Godavari municipal piped supply schedules, TDS, hardness, pH, and private borewell depth require on-site testing and local records."
        ]
        if data_level == "mandal":
            specific_limitations.insert(0, f"Mandal category '{assessment_cat}' for {mandal_name} is derived from CGWB Annexure IV OCS registry. Mandal-specific extraction percentage is not published in state summary tables; parent {canonical_dname} district aggregate is {district_soe}%.")

        return ModuleResult[WaterQualityData](
            module="water",
            status="available",
            provenance_kind="official_dataset",
            data=water_data,
            sources=[source_info],
            coverage=Coverage(
                granularity=data_level,
                radius_m=None,
                note=f"Official CGWB GEC-2015 assessment for {canonical_dname} district." if data_level == "district" else f"Official CGWB mandal assessment for {mandal_name}, {canonical_dname}."
            ),
            fetched_at=datetime.utcnow(),
            source_updated_at=source_updated_dt,
            measured_at=measured_at_dt,
            limitations=specific_limitations,
            served_from="live"
        )


DefaultWaterQualityProvider = TelanganaWaterQualityProvider


from backend.app.providers.safety import TelanganaSafetyProvider, DefaultCrimeProvider
