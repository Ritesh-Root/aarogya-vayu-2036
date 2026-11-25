"""Region registry: one source of truth, unknown regions rejected, no silent Lucknow fallback."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.regions import REGIONS, UnknownRegionError, get_region, region_for_district
from app.storage import StorageManager
import app.main as main_module

DATA = Path(__file__).resolve().parent.parent / "data"
client = TestClient(main_module.app)


def test_unknown_region_raises():
    with pytest.raises(UnknownRegionError):
        get_region("mars")


def test_none_region_is_default():
    assert get_region(None).id in REGIONS


def test_api_unknown_region_400():
    assert client.get("/api/risks?region=mars").status_code == 400


def test_storage_paths_per_region(tmp_path):
    (tmp_path / "data").mkdir()
    sm = StorageManager(base_dir=tmp_path)
    assert sm._get_region_paths("bhubaneswar")[0].name == "inventory_bhubaneswar.json"
    assert sm._get_region_paths("lucknow")[0].name == "inventory.json"
    with pytest.raises(UnknownRegionError):
        sm._get_region_paths("mars")


@pytest.mark.parametrize("region_id", ["lucknow", "bhubaneswar"])
def test_facility_region_by_district(region_id):
    facilities = json.loads((DATA / get_region(region_id).facilities_file).read_text())
    for fac in facilities:
        assert region_for_district(fac["district"]) == region_id
        assert main_module.domain_service.get_region_for_facility(fac["id"]) == region_id


def test_unknown_facility_region_raises():
    with pytest.raises(UnknownRegionError):
        main_module.domain_service.get_region_for_facility("NOPE-XYZ-99")


def test_state_code():
    assert main_module.domain_service._state_code("PHC-LKO-01") == "UP"
    assert main_module.domain_service._state_code("PHC-BBS-01") == "OD"


def test_optimizer_radius_per_region():
    assert main_module.optimizer.radius_for("PHC-LKO-01") == 35.0
    assert main_module.optimizer.radius_for("PHC-BBS-01") == 35.0


def test_telemetry_coordinates_from_registry():
    from app.telemetry_service import coordinates_for
    for rid, cfg in REGIONS.items():
        c = coordinates_for(rid)
        assert (c["lat"], c["lng"]) == cfg.centroid
    with pytest.raises(UnknownRegionError):
        coordinates_for("mars")
