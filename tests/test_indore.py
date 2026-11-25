"""Indore division (Madhya Pradesh): the BUILD 2036 home region."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
import app.telemetry_service as telemetry_module
from app.regions import get_region, region_for_district

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DISTRICTS = {"Indore", "Dhar", "Jhabua", "Alirajpur", "Barwani"}
client = TestClient(main_module.app)


@pytest.fixture(autouse=True)
def _sandbox(sandboxed):
    yield


def test_indore_registry_entry():
    cfg = get_region("indore")
    assert cfg.state_code == "MP" and set(cfg.districts) == DISTRICTS
    assert cfg.max_distance_km == 50.0 and cfg.heatwave_threshold_c == 40.0
    assert cfg.centroid == (22.77, 74.59)


def test_indore_facilities_in_districts():
    facs = json.loads((DATA / "facilities_indore.json").read_text())
    assert len(facs) == 20
    assert {f["district"] for f in facs} == DISTRICTS
    for f in facs:
        assert region_for_district(f["district"]) == "indore"
        assert main_module.domain_service.get_region_for_facility(f["id"]) == "indore"
        assert not any(tok in f["id"] for tok in ("BBS", "CTC", "LKO", "UNN"))
        assert 21.0 < f["lat"] < 23.5 and 74.0 < f["lng"] < 76.2


def test_generator_deterministic(tmp_path):
    env = {**os.environ, "MOCK_REFERENCE_DATE": "2026-12-01", "MOCK_OUTPUT_DIR": str(tmp_path)}
    outs = []
    for _ in range(2):
        subprocess.run([sys.executable, str(DATA / "generate_mock_data_indore.py")], env=env, check=True,
                       capture_output=True)
        outs.append((tmp_path / "inventory_indore.json").read_text())
    assert outs[0] == outs[1]


def test_heat_scenario_makes_transfers():
    recs = client.get("/api/recommendations?region=indore&scenario=heat").json()
    assert len(recs) >= 3
    assert all(r["distance_km"] <= 50.0 for r in recs)
    districts = {main_module.facilities_dict[r["recipient_facility_id"]]["district"] for r in recs}
    assert len(districts) >= 2  # transfers happen inside more than one district


def test_heat_preset_is_mp_heatwave():
    env = main_module.SCENARIO_PRESETS["indore"]["heat"]
    assert env.temperature_c == 46.0 and env.heatwave_alert is True


def test_every_scenario_has_indore_preset():
    for sc in ("smog", "heat", "flood", "cold", "normal"):
        assert client.get(f"/api/recommendations?region=indore&scenario={sc}").status_code == 200


def test_indore_challan_state_mp():
    recs = client.get("/api/recommendations?region=indore&scenario=heat").json()
    res = client.post("/api/approve-transfer?scenario=heat", json={"recommendation_id": recs[0]["id"]})
    assert res.status_code == 200
    assert res.json()["dispatch_challan_id"].startswith("CHALLAN-MP-")


def test_indore_outage_uses_indore_fallback(monkeypatch):
    def down(url, timeout=5):
        raise OSError("network down")

    monkeypatch.setattr(telemetry_module, "_get_json", down)
    reading = telemetry_module.LiveTelemetryService(cache_ttl_seconds=0).fetch_live_reading("indore")
    assert "Indore" in reading.corridor or "Madhya Pradesh" in reading.corridor


@pytest.mark.parametrize("region,scenario,recs,unmet", [
    ("lucknow", "smog", 4, 7), ("bhubaneswar", "heat", 6, 6), ("lucknow", "heat", 9, 7), ("bhubaneswar", "smog", 10, 13)])
def test_lucknow_bbs_unchanged(region, scenario, recs, unmet):
    inv, _, _, _ = main_module.storage.load_all(region=region)
    env = main_module.SCENARIO_PRESETS[region][scenario]
    got = main_module.optimizer.optimize(main_module.surge_engine.assess_facility_risks(inv, env, {}), inv)
    assert (len(got), len(main_module.optimizer.get_unmet_demands())) == (recs, unmet)
