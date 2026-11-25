"""Optimizer and voice-intake edge cases found by the 2026-11-26 audit."""
import asyncio

import pytest

import app.main as main_module
from app.models import EnvironmentalReading, VoiceIntakeRequest
from app.optimizer import RedistributionOptimizer
from app.surge_engine import SurgeEngine
from app.voice_service import VoiceIntakeService

MED = "MED-001"
NORMAL = EnvironmentalReading(aqi=40, pm25=24.0, temperature_c=26.0, humidity_pct=60.0,
                              heatwave_alert=False, smog_episode=False, corridor="test")

FACS = {
    "PHC-T-01": {"id": "PHC-T-01", "name": "PHC Needy", "district": "Lucknow", "type": "PHC", "lat": 26.80, "lng": 80.90},
    "CHC-T-02": {"id": "CHC-T-02", "name": "CHC Rich", "district": "Lucknow", "type": "CHC", "lat": 26.85, "lng": 80.92},
    "CHC-T-03": {"id": "CHC-T-03", "name": "CHC Other", "district": "Lucknow", "type": "CHC", "lat": 26.82, "lng": 80.95},
}


def _batch(fac, batch, stock, days, rate=10):
    return {"facility_id": fac, "facility_name": FACS[fac]["name"], "medicine_id": MED,
            "medicine_name": "Salbutamol Respirator Solution (Respules 2.5mg)", "current_stock": stock,
            "on_hand": stock, "reserved": 0, "quarantined": 0, "available": stock,
            "daily_consumption_base": rate, "batch_number": batch, "days_to_expiry": days,
            "expiry_date": "2027-12-31", "pack_size": 10}


def _run(inventory):
    surge = SurgeEngine(FACS, main_module.medicines_dict)
    opt = RedistributionOptimizer(FACS)
    risks = surge.assess_facility_risks(inventory, NORMAL, {})
    return opt.optimize(risks, inventory), opt.get_unmet_demands()


def test_donor_with_one_bad_batch_still_donates():
    inv = [_batch("PHC-T-01", "B-NEED", 10, 200),
           _batch("CHC-T-02", "B-OLD", 20, 10),      # expires in 10 days: not transferable
           _batch("CHC-T-02", "B-GOOD", 600, 300)]   # plenty of good stock
    recs, _ = _run(inv)
    assert any(r.donor_facility_id == "CHC-T-02" and r.batch_number == "B-GOOD" for r in recs)


def test_challan_batch_covers_quantity_hand_built():
    # Donor's good stock is split into two batches, neither big enough for the full need alone
    inv = [_batch("PHC-T-01", "B-NEED", 0, 200, rate=20),
           _batch("CHC-T-02", "B-A", 150, 100), _batch("CHC-T-02", "B-B", 200, 300)]  # 210 spare > any one batch
    recs, _ = _run(inv)
    by_batch = {b["batch_number"]: b["available"] for b in inv}
    assert recs
    for r in recs:
        assert by_batch[r.batch_number] >= r.units_to_transfer


@pytest.mark.parametrize("region", ["lucknow", "bhubaneswar"])
@pytest.mark.parametrize("scenario", ["smog", "heat", "flood", "cold", "normal"])
def test_challan_batch_covers_quantity_all_scenarios(region, scenario):
    inv, _, _, _ = main_module.storage.load_all(region=region)
    env = main_module.SCENARIO_PRESETS[region][scenario]
    risks = main_module.surge_engine.assess_facility_risks(inv, env, {})
    recs = main_module.optimizer.optimize(risks, inv)
    avail = {(i["facility_id"], i["batch_number"]): i.get("available", i.get("current_stock", 0)) for i in inv}
    for r in recs:
        assert avail[(r.donor_facility_id, r.batch_number)] >= r.units_to_transfer, r.id


def test_expiry_flag_follows_selected_batch():
    inv = [_batch("PHC-T-01", "B-NEED", 10, 200),
           _batch("CHC-T-02", "B-OLD", 20, 10),
           _batch("CHC-T-02", "B-GOOD", 600, 300)]
    recs, _ = _run(inv)
    rec = next(r for r in recs if r.batch_number == "B-GOOD")
    assert rec.expiry_waste_prevented is False  # the 300-day batch is not saving waste


def test_unmet_text_counts_partial_donors():
    # One small donor helps partly; the rest is unmet
    inv = [_batch("PHC-T-01", "B-NEED", 0, 200, rate=30),
           _batch("CHC-T-02", "B-R", 200, 300, rate=5),
           _batch("CHC-T-03", "B-O", 10, 300, rate=5)]
    recs, unmet = _run(inv)
    assert recs, "the partial donor should still send what it can spare"
    u = next(u for u in unmet if u.facility_id == "PHC-T-01")
    assert u.infeasibility_reason.startswith("1 of 2 peer facilities could donate")
    assert f"{u.unmet_units_needed} units still unmet" in u.infeasibility_reason


def test_voice_unknown_facility_asks(monkeypatch):
    import app.voice_service as voice_module

    async def no_model(*a, **k):
        return None  # AI unavailable: the rule-based parser runs

    monkeypatch.setattr(voice_module, "generate_json", no_model)
    svc = VoiceIntakeService(main_module.facilities_dict, main_module.medicines_dict)
    req = VoiceIntakeRequest(transcript_text="Salbutamol 15 bache hain, PHC Atlantis se bol rahe hain", language="hinglish")
    res = asyncio.run(svc.parse_and_validate(req))
    assert res.facility_id is None
    assert res.requires_confirmation is True
    assert "which clinic" in (res.anomaly_flag or "").lower()
