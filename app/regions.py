"""Single source of truth for the demo regions. Unknown regions raise; nothing falls back silently."""
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


class UnknownRegionError(ValueError):
    """A region id (or a facility's district) that is not in the registry."""


@dataclass(frozen=True)
class RegionConfig:
    id: str
    label: str
    short_name: str
    state: str
    state_code: str
    districts: Tuple[str, ...]
    centroid: Tuple[float, float]
    centroid_district: str
    heatwave_threshold_c: float
    max_distance_km: float
    default_facility_id: str
    facilities_file: str
    inventory_file: str
    consignments_file: str
    idempotency_file: str
    audit_file: str
    corridor_name: str
    map_center: Tuple[float, float]
    map_zoom: int
    polygon: Tuple[Tuple[float, float], ...]
    corridor_title: str = ""
    constituency: str = ""
    news_query_place: str = ""
    edl_label: str = ""
    initial_env: Dict = field(default_factory=dict)
    fallback_env: Dict = field(default_factory=dict)


REGIONS: Dict[str, RegionConfig] = {
    "bhubaneswar": RegionConfig(
        id="bhubaneswar",
        label="Bhubaneswar–Cuttack Coastal & Industrial Corridor (Odisha)",
        short_name="Bhubaneswar (Odisha)",
        state="Odisha",
        state_code="OD",
        districts=("Khordha", "Cuttack"),
        centroid=(20.2961, 85.8245),
        centroid_district="Khordha",
        # IMD heatwave criterion: 37°C for coastal stations, 40°C for the plains
        heatwave_threshold_c=37.0,
        max_distance_km=35.0,
        default_facility_id="PHC-BBS-01",
        facilities_file="facilities_bhubaneswar.json",
        inventory_file="inventory_bhubaneswar.json",
        consignments_file="consignments_bhubaneswar.json",
        idempotency_file="idempotency_bhubaneswar.json",
        audit_file="audit_log_bhubaneswar.json",
        corridor_name="Bhubaneswar–Cuttack Coastal & Industrial Corridor (Odisha)",
        corridor_title="Bhubaneswar–Cuttack Health Corridor",
        constituency="Bhubaneswar & Cuttack Parliamentary Constituencies",
        news_query_place="Bhubaneswar",
        edl_label="Odisha State EDL",
        map_center=(20.30, 85.83),
        map_zoom=10,
        polygon=((20.62, 85.65), (20.65, 86.18), (20.45, 86.22), (20.10, 86.12),
                 (19.90, 85.35), (20.15, 85.25), (20.40, 85.60)),
        initial_env=dict(aqi=168, pm25=80.4, temperature_c=39.5, humidity_pct=72.0,
                         heatwave_alert=True, smog_episode=False,
                         corridor="Bhubaneswar–Cuttack Coastal & Industrial Corridor (Odisha)"),
        fallback_env=dict(aqi=68, pm25=40.8, temperature_c=27.5, humidity_pct=82.0, wind_speed_kmh=9.5),
    ),
    "lucknow": RegionConfig(
        id="lucknow",
        label="Lucknow-Unnao Indo-Gangetic Corridor (UP)",
        short_name="Lucknow (UP)",
        state="Uttar Pradesh",
        state_code="UP",
        districts=("Lucknow", "Unnao"),
        centroid=(26.8467, 80.9462),
        centroid_district="Lucknow",
        heatwave_threshold_c=40.0,
        max_distance_km=35.0,
        default_facility_id="PHC-LKO-01",
        facilities_file="facilities.json",
        inventory_file="inventory.json",
        consignments_file="consignments.json",
        idempotency_file="idempotency.json",
        audit_file="audit_log.json",
        corridor_name="Lucknow-Unnao Indo-Gangetic Corridor (UP)",
        corridor_title="Lucknow-Unnao Health Corridor",
        constituency="Lucknow & Mohanlalganj Parliamentary Constituencies",
        news_query_place="Lucknow",
        edl_label="",
        map_center=(26.75, 80.72),
        map_zoom=10,
        polygon=((27.02, 80.45), (27.00, 80.85), (26.90, 81.16), (26.72, 81.15),
                 (26.54, 80.70), (26.46, 80.35), (26.60, 80.22), (26.85, 80.32)),
        initial_env=dict(aqi=385, pm25=230.5, temperature_c=17.5, humidity_pct=78.0,
                         heatwave_alert=False, smog_episode=True,
                         corridor="Lucknow-Unnao Indo-Gangetic Smog Corridor (Severe Inversion)"),
        fallback_env=dict(aqi=78, pm25=46.8, temperature_c=28.0, humidity_pct=76.0, wind_speed_kmh=12.0),
    ),
}

_IS_PYTEST = ("pytest" in sys.modules) or ("PYTEST_CURRENT_TEST" in os.environ)
DEFAULT_REGION = os.environ.get("DEFAULT_REGION", "lucknow" if _IS_PYTEST else "bhubaneswar").strip().lower()
if DEFAULT_REGION not in REGIONS:
    raise UnknownRegionError(f"DEFAULT_REGION '{DEFAULT_REGION}' is not one of {list(REGIONS)}")

_DISTRICT_TO_REGION = {d: r.id for r in REGIONS.values() for d in r.districts}


def get_region(region_id: Optional[str]) -> RegionConfig:
    if region_id is None or str(region_id).strip() == "":
        return REGIONS[DEFAULT_REGION]
    rid = str(region_id).strip().lower()
    if rid not in REGIONS:
        raise UnknownRegionError(f"Unknown region '{rid}'. Available: {list(REGIONS)}")
    return REGIONS[rid]


def region_for_district(district: str) -> Optional[str]:
    return _DISTRICT_TO_REGION.get(district)


def region_of_facility(facilities: Dict[str, dict], facility_id: str) -> Optional[str]:
    fac = facilities.get(facility_id)
    return region_for_district(fac.get("district", "")) if fac else None
