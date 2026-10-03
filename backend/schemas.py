"""Hợp đồng JSON của API; EC giữ nguyên đơn vị mS/m và cờ chất lượng."""

from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_serializer

LOCAL_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
QualityFlag = Literal["UNVERIFIED", "VALIDATED", "SUSPECT", "INVALID"]
ObservationKind = Literal["O", "E"]


def local_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("Database timestamp must include a timezone")
    return value.astimezone(LOCAL_TZ).isoformat()


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    database_name: str
    transaction_read_only: bool


class PointGeometry(BaseModel):
    type: Literal["Point"] = "Point"
    coordinates: tuple[float, float]  # longitude, latitude


class StationProperties(BaseModel):
    site_code: str
    site_name: str
    external_site_code: str
    location_status: Literal["UNKNOWN", "REPORTED", "VERIFIED"]
    location_reference: str | None
    source_code: str
    source_name: str
    source_reference: str


class StationFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    id: str
    geometry: PointGeometry | None
    properties: StationProperties


class StationCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[StationFeature]
    coordinate_reference_system: str = "EPSG:4326"
    count: int


class DatasetSummary(BaseModel):
    dataset_id: int
    dataset_code: str
    sha256: str
    source_filename: str
    source_code: str
    imported_at: datetime
    observation_count: int
    first_observation: datetime
    last_observation: datetime
    observed_rows: int
    estimated_rows: int
    unverified_rows: int
    validated_rows: int
    suspect_rows: int
    invalid_rows: int

    @field_serializer("imported_at", "first_observation", "last_observation")
    def serialize_timestamp(self, value: datetime) -> str:
        return local_timestamp(value)


class DatasetCollection(BaseModel):
    site_code: str
    unit: Literal["mS/m"] = "mS/m"
    time_zone: str = "Asia/Ho_Chi_Minh"
    items: list[DatasetSummary]


class ECObservation(BaseModel):
    ec_observation_id: int
    source_row: int
    observed_at: datetime
    conductivity_ms_per_m: float = Field(ge=0, allow_inf_nan=False)
    unit: Literal["mS/m"]
    observed_or_estimated: ObservationKind
    quality_flag: QualityFlag
    approval_level: str
    grade: str
    source_label: str

    @field_serializer("observed_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return local_timestamp(value)


class HistoryFilters(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    quality_flag: QualityFlag | None = None
    observed_or_estimated: ObservationKind | None = None


class ECHistory(BaseModel):
    site_code: str
    dataset: DatasetSummary
    unit: Literal["mS/m"] = "mS/m"
    time_zone: str = "Asia/Ho_Chi_Minh"
    data_kind: Literal["historical_observations"] = "historical_observations"
    filters: HistoryFilters
    total: int
    limit: int
    offset: int
    has_more: bool
    items: list[ECObservation]
