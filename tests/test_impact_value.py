"""Rupees-saved panel for the district officer: every figure traceable to a price source or a stated assumption."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.impact_value import region_value_summary

MEDS = {m["id"]: m for m in json.loads((Path(__file__).resolve().parent.parent / "data" / "medicines.json").read_text())}


@pytest.fixture(autouse=True)
def _sandbox(sandboxed):
    yield


def _consignment(med, units, expiring_batch, old_days, new_days, status="APPROVED_RESERVED"):
    return {"id": f"C-{med}-{units}", "medicine_id": med, "units_requested": units, "status": status,
            "recommendation_snapshot": {"expiry_waste_prevented": expiring_batch,
                                        "recipient_initial_coverage_days": old_days,
                                        "recipient_new_coverage_days": new_days}}


def test_prices_have_sources():
    for mid, m in MEDS.items():
        assert "unit_price_inr" in m and "price_source" in m
        if m["unit_price_inr"] is not None:
            assert m["unit_price_inr"] > 0 and m["price_source"].startswith("http")


def test_value_zero_before_any_approval():
    v = region_value_summary({}, MEDS)
    assert v["transfers_approved"] == 0 and v["expiry_value_saved_inr"] == 0 and v["stockout_days_avoided"] == 0
    assert v["projected_monthly_cost_inr"] == 1000
    assert v["assumptions"]


def test_value_counts_expiring_stock_and_capped_cover():
    cons = {"a": _consignment("MED-002", 100, True, 1.0, 9.0),     # ORS from a batch expiring <= 90 days
            "b": _consignment("MED-005", 10, False, 2.0, 5.0),     # fresh batch: no expiry saving
            "c": _consignment("MED-002", 50, True, 1.0, 3.0, status="CANCELLED")}
    v = region_value_summary(cons, MEDS)
    assert v["transfers_approved"] == 2
    assert v["expiry_value_saved_inr"] == round(100 * MEDS["MED-002"]["unit_price_inr"])
    assert v["stockout_days_avoided"] == pytest.approx((7.0 - 1.0) + (5.0 - 2.0))


def test_unpriced_medicine_counts_zero_and_is_listed():
    unpriced = [mid for mid, m in MEDS.items() if m["unit_price_inr"] is None]
    assert unpriced, "at least one catalogue medicine has no sourced price"
    v = region_value_summary({"x": _consignment(unpriced[0], 40, True, 1.0, 4.0)}, MEDS)
    assert v["expiry_value_saved_inr"] == 0
    assert unpriced[0] in v["unpriced_medicines"]


def test_endpoint_after_approval_and_per_visitor():
    a, b = TestClient(main_module.app), TestClient(main_module.app)
    recs = a.get("/api/recommendations?region=indore&scenario=heat").json()
    assert a.post("/api/approve-transfer?scenario=heat", json={"recommendation_id": recs[0]["id"]}).status_code == 200
    va = a.get("/api/impact/value?region=indore").json()
    assert va["transfers_approved"] == 1 and va["stockout_days_avoided"] > 0
    assert va["expiry_value_saved_inr"] > 0  # Indore heat transfers move near-expiry heat medicines
    vb = b.get("/api/impact/value?region=indore").json()
    assert vb["transfers_approved"] == 0
