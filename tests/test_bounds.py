"""Every write endpoint rejects absurd values (audit finding: count of 1e12 and AQI -99999 were accepted)."""
from fastapi.testclient import TestClient

import pytest

import app.main as main_module

client = TestClient(main_module.app)


@pytest.fixture(autouse=True)
def _sandbox(sandboxed):
    yield


FAC = "PHC-LKO-01"


def _item():
    return client.get(f"/api/clinic/{FAC}/desk").json()["inventory"][0]


def _stock(qty, **extra):
    it = _item()
    body = {"facility_id": FAC, "medicine_id": it["medicine_id"], "batch_number": it["batch_number"],
            "action_type": "PHYSICAL_COUNT", "quantity": qty, "reason": "bounds test", **extra}
    return client.post(f"/api/clinic/{FAC}/stock-action", json=body)


def test_physical_count_huge_rejected():
    assert _stock(10**12).status_code == 422


def test_negative_quantity_rejected():
    assert _stock(-5).status_code == 422


def test_overlong_id_rejected():
    assert _stock(10, batch_number="X" * 200).status_code == 422


def test_env_negative_aqi_rejected():
    assert client.post("/api/environmental?region=lucknow", json={"aqi": -99999}).status_code == 422


def test_env_absurd_temp_rejected():
    assert client.post("/api/environmental?region=lucknow", json={"temperature_c": 1e9}).status_code == 422


def test_env_humidity_over_100_rejected():
    assert client.post("/api/environmental?region=lucknow", json={"humidity_pct": 150}).status_code == 422


def test_receive_units_capped():
    res = client.post("/api/transfer/receive", json={"consignment_id": "C-1", "accepted_units": 10**9})
    assert res.status_code == 422


def test_valid_stock_action_still_200():
    it = _item()
    assert _stock(it["on_hand"]).status_code == 200
