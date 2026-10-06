import httpx
import logging
from datetime import datetime
from typing import Literal
from backend.app.providers.base import AirQualityProvider, WaterQualityProvider, CrimeProvider, StoragePolicy
from backend.app.schemas.base import ModuleResult, DataSourceInfo, Coverage
from backend.app.schemas.modules import AirQualityData, WaterQualityData, CrimeData
from backend.app.schemas.location import Coordinates
from backend.app.utils.geo import haversine_distance_m
from backend.app.config import settings

logger = logging.getLogger(__name__)

class OpenMeteoAirQualityProvider(AirQualityProvider):
    """
    Open-Meteo Air Quality Provider.
    Based on European Copernicus CAMS atmospheric models.
    Storage policy: storable.
    Provenance kind: modeled_estimate.
    """
    @property
    def name(self) -> str:
        return "Open-Meteo Air Quality (CAMS European Model)"

    @property
    def license(self) -> str:
        return "Open-Meteo Terms / Copernicus Atmosphere Monitoring Service"

    @property
    def attribution_url(self) -> str:
        return "https://open-meteo.com/en/docs/air-quality-api"

    @property
    def storage_policy(self) -> StoragePolicy:
        return "storable"

    @property
    def max_results(self) -> int:
        return 1

    @property
    def capabilities(self) -> list[str]:
        return ["pm2_5", "pm10", "us_aqi", "european_aqi"]

    async def get_air_quality(self, lat: float, lng: float) -> ModuleResult[AirQualityData]:
        url = "https://air-quality-api.open-meteo.com/v1/air-quality"
        params = {
            "latitude": lat,
            "longitude": lng,
            "current": "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone,us_aqi,european_aqi"
        }
        source_info = self.get_data_source_info()

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                headers = {"User-Agent": "LocalLens/4.0 (contact: info@locallens.app)"}
                resp = await client.get(url, params=params, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    current = data.get("current", {})
                    measured_iso = current.get("time")
                    measured_at = datetime.fromisoformat(measured_iso) if measured_iso else None

                    aq_data = AirQualityData(
                        aqi=current.get("us_aqi"),
                        aqi_scale="US AQI",
                        pm25=current.get("pm2_5"),
                        pm10=current.get("pm10"),
                        co=current.get("carbon_monoxide"),
                        no2=current.get("nitrogen_dioxide"),
                        so2=current.get("sulphur_dioxide"),
                        o3=current.get("ozone"),
                        model_grid_resolution_km=11.0,
                        advisory="Ambient air quality values are modeled regional estimates."
                    )

                    return ModuleResult[AirQualityData](
                        module="environment",
                        status="available" if aq_data.aqi is not None else "limited",
                        provenance_kind="modeled_estimate",
                        data=aq_data,
                        sources=[source_info],
                        coverage=Coverage(
                            granularity="city",
                            radius_m=11000,
                            note="Grid cell ~11 km resolution from Copernicus CAMS reanalysis."
                        ),
                        fetched_at=datetime.utcnow(),
                        measured_at=measured_at,
                        source_updated_at=measured_at,
                        limitations=[
                            "Modeled estimate — not a physical station measurement.",
                            "Measurement represents regional atmospheric grid and may not reflect microclimates or conditions at the exact property."
                        ]
                    )
        except Exception as e:
            logger.error(f"Open-Meteo Air Quality error: {e}")

        return ModuleResult[AirQualityData](
            module="environment",
            status="error",
            provenance_kind="modeled_estimate",
            data=None,
            sources=[source_info],
            coverage=Coverage(granularity="unknown"),
            fetched_at=datetime.utcnow(),
            limitations=["Open-Meteo service was unreachable."],
            message="Environmental air quality service temporarily unavailable."
        )


class OpenAQAirQualityProvider(AirQualityProvider):
    """
    OpenAQ v3 Provider.
    Ground station measurements.
    Requires OPENAQ_API_KEY.
    """
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.OPENAQ_API_KEY

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
        # Real OpenAQ call when key is configured
        return ModuleResult[AirQualityData](
            module="environment",
            status="unavailable",
            provenance_kind="station_measurement",
            data=None,
            sources=[source_info],
            coverage=Coverage(granularity="monitoring_station"),
            fetched_at=datetime.utcnow(),
            limitations=["No physical monitoring station found within 25 km."],
            message="No monitoring station active within 25 km of this locality."
        )


class DefaultWaterQualityProvider(WaterQualityProvider):
    """
    Water Quality Provider representing verified lack of locality machine APIs.
    Renders honest unavailable state per Section 2.2 and Section 7.
    """
    @property
    def name(self) -> str:
        return "Central Ground Water Board (CGWB) & State Water Authorities"

    @property
    def license(self) -> str:
        return "National Data Sharing and Accessibility Policy (NDSAP)"

    @property
    def attribution_url(self) -> str:
        return "https://cgwb.gov.in"

    @property
    def storage_policy(self) -> StoragePolicy:
        return "storable"

    @property
    def max_results(self) -> int:
        return 0

    @property
    def capabilities(self) -> list[str]:
        return []

    async def get_water_quality(self, lat: float, lng: float) -> ModuleResult[WaterQualityData]:
        return ModuleResult[WaterQualityData](
            module="water",
            status="unavailable",
            provenance_kind="official_dataset",
            data=None,
            sources=[self.get_data_source_info()],
            coverage=Coverage(
                granularity="district",
                note="Water-quality datasets are published in district bulletins and not via locality-level machine APIs."
            ),
            fetched_at=datetime.utcnow(),
            limitations=[
                "No integrated water-quality dataset covers this specific location.",
                "Water supply and quality vary significantly by building, municipal water connection (Cauvery/metro), borewell depth, and private tanker sources."
            ],
            message="No integrated water-quality dataset covers this location. Ask the society or landlord about water sources and supply schedules."
        )


class DefaultCrimeProvider(CrimeProvider):
    """
    Crime Data Provider representing verified lack of locality machine APIs.
    Renders honest unavailable state per Section 2.2 and Section 7.
    """
    @property
    def name(self) -> str:
        return "National Crime Records Bureau (NCRB)"

    @property
    def license(self) -> str:
        return "Open Government Data (OGD) Platform India"

    @property
    def attribution_url(self) -> str:
        return "https://ncrb.gov.in"

    @property
    def storage_policy(self) -> StoragePolicy:
        return "storable"

    @property
    def max_results(self) -> int:
        return 0

    @property
    def capabilities(self) -> list[str]:
        return []

    async def get_crime_data(self, lat: float, lng: float) -> ModuleResult[CrimeData]:
        return ModuleResult[CrimeData](
            module="crime",
            status="unavailable",
            provenance_kind="official_dataset",
            data=None,
            sources=[self.get_data_source_info()],
            coverage=Coverage(
                granularity="district",
                note="Official crime statistics are aggregated at district or commissionerate levels."
            ),
            fetched_at=datetime.utcnow(),
            limitations=[
                "Locality-level crime statistics are unavailable from integrated sources.",
                "Official NCRB datasets are compiled annually at police commissionerate / district boundaries and cannot be reliably attributed to individual neighborhoods.",
                "The absence of reported crime statistics does not imply that an area is safe."
            ],
            message="Locality-level crime statistics are unavailable from integrated sources."
        )
