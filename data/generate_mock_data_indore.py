"""Indore division (Madhya Pradesh) demo region: facilities and SAMPLE inventory.

Facility names and towns are real block and district health facilities in Indore, Dhar, Jhabua,
Alirajpur and Barwani; coordinates are the towns' (Open-Meteo geocoding). Beds, population served
and every stock figure are sample data, not facility records. Jhabua, Alirajpur and Barwani are
rated "Very High" heat-health vulnerability in MP (Das et al. 2026, Springer Nature).

Engineered heatwave story: one clinic per district is critically short of heat medicines
(ORS, IV paracetamol, dexamethasone) while a larger hospital in the same district holds surplus
batches that expire in 55-85 days.

Run:  MOCK_REFERENCE_DATE=2026-12-01 python data/generate_mock_data_indore.py
      (MOCK_OUTPUT_DIR overrides the output folder; default is this folder)
"""
import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
OUT_DIR = Path(os.environ.get("MOCK_OUTPUT_DIR", DATA_DIR))
SAMPLE_DOCTOR = "Medical Officer (sample data)"

# id, name, district, type, lat, lng, population_served, beds
FACILITIES = [
    ("DH-JBA-01", "District Hospital Jhabua", "Jhabua", "DH", 22.7677, 74.5909, 210000, 300),
    ("CHC-JBA-02", "CHC Meghnagar", "Jhabua", "CHC", 22.9066, 74.5416, 120000, 30),
    ("CHC-JBA-03", "CHC Thandla", "Jhabua", "CHC", 23.0096, 74.5775, 115000, 30),
    ("CHC-JBA-04", "CHC Petlawad", "Jhabua", "CHC", 23.0110, 74.7977, 140000, 30),
    ("CHC-JBA-05", "CHC Ranapur", "Jhabua", "CHC", 22.6470, 74.5212, 105000, 30),
    ("DH-ARJ-01", "District Hospital Alirajpur", "Alirajpur", "DH", 22.3039, 74.3557, 180000, 200),
    ("CHC-ARJ-02", "CHC Jobat", "Alirajpur", "CHC", 22.4160, 74.5683, 95000, 30),
    ("CHC-ARJ-03", "CHC Bhabra", "Alirajpur", "CHC", 22.5305, 74.3285, 90000, 30),
    ("DH-BWN-01", "District Hospital Barwani", "Barwani", "DH", 22.0323, 74.8998, 200000, 300),
    ("CHC-BWN-02", "CHC Anjad", "Barwani", "CHC", 22.0417, 75.0552, 85000, 30),
    ("CHC-BWN-03", "CHC Rajpur", "Barwani", "CHC", 21.9402, 75.1361, 110000, 30),
    ("CHC-BWN-04", "CHC Sendhwa", "Barwani", "CHC", 21.6856, 75.0962, 150000, 50),
    ("DH-DHR-01", "District Hospital Dhar", "Dhar", "DH", 22.5937, 75.2977, 230000, 400),
    ("CHC-DHR-02", "CHC Sardarpur", "Dhar", "CHC", 22.6655, 74.9774, 100000, 30),
    ("CHC-DHR-03", "CHC Badnawar", "Dhar", "CHC", 23.0218, 75.2327, 125000, 30),
    ("CHC-DHR-04", "CHC Kukshi", "Dhar", "CHC", 22.2068, 74.7579, 115000, 30),
    ("CHC-DHR-05", "CHC Manawar", "Dhar", "CHC", 22.2357, 75.0892, 105000, 30),
    ("CHC-IDR-01", "CHC Mhow", "Indore", "CHC", 22.5589, 75.7654, 160000, 50),
    ("CHC-IDR-02", "CHC Sanwer", "Indore", "CHC", 22.9742, 75.8271, 110000, 30),
    ("CHC-IDR-03", "CHC Depalpur", "Indore", "CHC", 22.8510, 75.5422, 120000, 30),
]

HEAT_MEDS = {"MED-002", "MED-003", "MED-005"}  # ORS, dexamethasone, IV paracetamol
CRITICAL = {"CHC-JBA-05", "CHC-ARJ-02", "CHC-BWN-03", "CHC-DHR-02", "CHC-IDR-03"}
DONORS = {"DH-JBA-01", "DH-ARJ-01", "DH-BWN-01", "DH-DHR-01", "CHC-IDR-01"}


def build(today: datetime):
    facilities = [
        {"id": i, "name": n, "district": d, "type": t, "lat": la, "lng": lo, "population_served": p, "beds": b,
         "cold_storage": t == "DH" or b >= 50, "doctor": SAMPLE_DOCTOR}
        for i, n, d, t, la, lo, p, b in FACILITIES
    ]
    with open(DATA_DIR / "medicines.json", "r", encoding="utf-8") as f:
        medicines = json.load(f)

    rng = random.Random(2036)
    inventory = []
    for fac in facilities:
        big = fac["type"] in ("CHC", "DH")
        for med in medicines:
            base_rate = med["base_consumption_chc"] if big else med["base_consumption_phc"]
            if fac["type"] == "DH":
                base_rate = round(base_rate * 1.5, 1)
            if fac["id"] in CRITICAL and med["id"] in HEAT_MEDS:
                qty, expiry_days = int(base_rate * rng.uniform(1.8, 3.2)), rng.randint(180, 365)
            elif fac["id"] in DONORS and med["id"] in HEAT_MEDS:
                qty, expiry_days = int(base_rate * rng.uniform(28.0, 40.0)), rng.randint(55, 85)
            else:
                qty, expiry_days = int(base_rate * rng.uniform(12.0, 24.0)), rng.randint(120, 450)
            inventory.append({
                "facility_id": fac["id"], "facility_name": fac["name"],
                "medicine_id": med["id"], "medicine_name": med["name"],
                "current_stock": qty, "on_hand": qty, "reserved": 0, "quarantined": 0, "available": qty,
                "raw_available": qty, "reconciliation_deficit": 0, "is_reconciliation_required": False,
                "is_frozen": False, "version": 1, "pack_size": 10, "daily_consumption_base": base_rate,
                "batch_number": f"BAT-MP-{rng.randint(100, 999)}-{today.year % 100}",
                "expiry_date": (today + timedelta(days=expiry_days)).strftime("%Y-%m-%d"),
                "days_to_expiry": expiry_days,
                "last_updated": (today - timedelta(hours=rng.randint(1, 14))).strftime("%Y-%m-%d %H:%M:%S"),
            })
    return facilities, inventory


def main():
    ref = os.environ.get("MOCK_REFERENCE_DATE")
    today = datetime.fromisoformat(ref) if ref else datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    facilities, inventory = build(today)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "facilities_indore.json").write_text(json.dumps(facilities, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT_DIR / "inventory_indore.json").write_text(json.dumps(inventory, indent=2, ensure_ascii=False), encoding="utf-8")
    for name, empty in (("consignments_indore.json", {}), ("idempotency_indore.json", {}), ("audit_log_indore.json", [])):
        path = OUT_DIR / name
        if not path.exists():
            path.write_text(json.dumps(empty), encoding="utf-8")
    print(f"Generated {len(facilities)} Indore-division facilities and {len(inventory)} inventory records into {OUT_DIR}")


if __name__ == "__main__":
    main()
