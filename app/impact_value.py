"""What the district officer gets back, in rupees and clinic-days, from the transfers approved so far.

Every figure is either computed from this visitor's own approved transfers or labelled as an estimate,
with its source, in `assumptions`.
"""
from typing import Dict, List

ACTIVE_STATUSES = ("APPROVED_RESERVED", "DISPATCHED", "RECEIVED")
COVER_WINDOW_DAYS = 7.0  # the first week of a surge, where redistribution helps most (see scripts/simulate_impact.py)
PROJECTED_MONTHLY_COST_INR = 1000

ASSUMPTIONS: List[str] = [
    "Unit prices are Jan Aushadhi (PMBJP) MRPs, per medicine in data/medicines.json with the list row cited.",
    "Stock counts as saved from expiry when the batch moved expires within 90 days at the donor "
    "(the same rule as the 'prevents expiry waste' badge).",
    f"Stockout days avoided: for each transfer, the recipient's days of medicine gained, counted only inside the "
    f"first {int(COVER_WINDOW_DAYS)} days.",
    "Running cost is an estimate: about ₹1,000 a month for a 20-clinic district at Google's published "
    "Gemini prices (voice reports, transfer checks, questions, read-aloud and photo checks).",
    "Clinic stock is sample data; the figures show the method, not field results.",
]


def region_value_summary(consignments: Dict[str, dict], medicines: Dict[str, dict]) -> dict:
    saved_inr = 0.0
    days_avoided = 0.0
    approved = 0
    unpriced = set()
    for c in consignments.values():
        if c.get("status") not in ACTIVE_STATUSES:
            continue
        approved += 1
        snap = c.get("recommendation_snapshot") or {}
        old = float(snap.get("recipient_initial_coverage_days", 0) or 0)
        new = float(snap.get("recipient_new_coverage_days", old) or old)
        days_avoided += max(0.0, min(new, COVER_WINDOW_DAYS) - min(old, COVER_WINDOW_DAYS))
        if snap.get("expiry_waste_prevented"):
            price = (medicines.get(c.get("medicine_id"), {}) or {}).get("unit_price_inr")
            if price is None:
                unpriced.add(c.get("medicine_id"))
            else:
                saved_inr += price * int(c.get("units_requested", 0) or 0)
    return {
        "transfers_approved": approved,
        "expiry_value_saved_inr": int(round(saved_inr)),
        "stockout_days_avoided": round(days_avoided, 1),
        "projected_monthly_cost_inr": PROJECTED_MONTHLY_COST_INR,
        "unpriced_medicines": sorted(m for m in unpriced if m),
        "assumptions": ASSUMPTIONS,
    }
