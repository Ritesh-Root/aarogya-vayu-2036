"""India's National Air Quality Index (CPCB) from PM2.5 and PM10.

Sub-index = linear interpolation inside the CPCB concentration bands (continuous form, µg/m³);
the AQI is the larger sub-index. CPCB averages over 24 h; we apply it to the current or forecast hour,
so the result is an hourly estimate on the NAQI scale, labelled as such in the UI.
"""
import math
from typing import Optional, Sequence, Tuple

Band = Tuple[float, float, int, int]  # concentration low, high, index low, high

PM25_BANDS: Sequence[Band] = (
    (0, 30, 0, 50), (30, 60, 50, 100), (60, 90, 100, 200),
    (90, 120, 200, 300), (120, 250, 300, 400), (250, 380, 400, 500),
)
PM10_BANDS: Sequence[Band] = (
    (0, 50, 0, 50), (50, 100, 50, 100), (100, 250, 100, 200),
    (250, 350, 200, 300), (350, 430, 300, 400), (430, 510, 400, 500),
)
CATEGORIES = ((50, "Good"), (100, "Satisfactory"), (200, "Moderate"), (300, "Poor"), (400, "Very Poor"), (500, "Severe"))


def _sub_index(conc: Optional[float], bands: Sequence[Band]) -> int:
    if conc is None or conc <= 0:
        return 0
    for c_lo, c_hi, i_lo, i_hi in bands:
        if conc <= c_hi:
            value = i_lo + (conc - c_lo) * (i_hi - i_lo) / (c_hi - c_lo)
            return min(500, int(math.floor(value + 0.5)))
    return 500


def naqi_from_pm(pm25: Optional[float], pm10: Optional[float]) -> int:
    return max(_sub_index(pm25, PM25_BANDS), _sub_index(pm10, PM10_BANDS))


def naqi_category(aqi: int) -> str:
    for upper, name in CATEGORIES:
        if aqi <= upper:
            return name
    return "Severe"
