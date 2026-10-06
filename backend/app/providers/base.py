from abc import ABC, abstractmethod
from typing import Literal
from backend.app.schemas.base import ModuleResult, DataSourceInfo, Coverage
from backend.app.schemas.location import AutocompletePrediction, LocationDetails, PlacesData, Coordinates
from backend.app.schemas.modules import AirQualityData, WaterQualityData, CrimeData, CommuteData

StoragePolicy = Literal["live_only", "storable"]

class BaseProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def license(self) -> str:
        pass

    @property
    @abstractmethod
    def attribution_url(self) -> str:
        pass

    @property
    @abstractmethod
    def storage_policy(self) -> StoragePolicy:
        pass

    @property
    @abstractmethod
    def max_results(self) -> int:
        pass

    @property
    @abstractmethod
    def capabilities(self) -> list[str]:
        pass

    def get_data_source_info(self) -> DataSourceInfo:
        return DataSourceInfo(
            name=self.name,
            url=self.attribution_url,
            license=self.license,
            attribution=f"Data provided by {self.name} under {self.license}"
        )


class GeocodingProvider(BaseProvider):
    @abstractmethod
    async def autocomplete(self, query: str, session_token: str | None = None) -> list[AutocompletePrediction]:
        pass

    @abstractmethod
    async def get_details(self, place_id: str, session_token: str | None = None) -> LocationDetails | None:
        pass

    @abstractmethod
    async def reverse_geocode(self, lat: float, lng: float) -> LocationDetails | None:
        pass


class PlacesProvider(BaseProvider):
    @abstractmethod
    async def get_nearby_places(
        self,
        lat: float,
        lng: float,
        radius_m: int = 1500,
        categories: list[str] | None = None
    ) -> ModuleResult[PlacesData]:
        pass


class AirQualityProvider(BaseProvider):
    @abstractmethod
    async def get_air_quality(self, lat: float, lng: float) -> ModuleResult[AirQualityData]:
        pass


class WaterQualityProvider(BaseProvider):
    @abstractmethod
    async def get_water_quality(self, lat: float, lng: float) -> ModuleResult[WaterQualityData]:
        pass


class CrimeProvider(BaseProvider):
    @abstractmethod
    async def get_crime_data(self, lat: float, lng: float) -> ModuleResult[CrimeData]:
        pass


class RoutingProvider(BaseProvider):
    @abstractmethod
    async def get_commute(
        self,
        origin: Coordinates,
        destination_coords: Coordinates,
        destination_name: str,
        departure_time: str | None = None
    ) -> ModuleResult[CommuteData]:
        pass


class LLMProvider(BaseProvider):
    @abstractmethod
    async def generate_summary(self, system_prompt: str, user_prompt: str) -> str:
        pass
