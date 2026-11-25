"""India's National AQI (CPCB) from PM2.5 / PM10: the scale the surge bands are written for."""
import pytest

from app.naqi import naqi_category, naqi_from_pm


@pytest.mark.parametrize("pm25,expected", [(0, 0), (30, 50), (60, 100), (90, 200), (120, 300), (250, 400), (380, 500)])
def test_band_edges(pm25, expected):
    assert naqi_from_pm(pm25, None) == expected


def test_mid_band():
    assert naqi_from_pm(200, None) == 362


def test_pm10_dominates():
    assert naqi_from_pm(20, 300) == 250


def test_missing_and_extreme():
    assert naqi_from_pm(None, None) == 0
    assert naqi_from_pm(900, None) == 500
    assert naqi_from_pm(-5, None) == 0
    assert naqi_from_pm(None, 80) == 80


@pytest.mark.parametrize("aqi,cat", [(0, "Good"), (50, "Good"), (51, "Satisfactory"), (150, "Moderate"),
                                     (250, "Poor"), (362, "Very Poor"), (401, "Severe"), (500, "Severe")])
def test_categories(aqi, cat):
    assert naqi_category(aqi) == cat


def test_presets_are_consistent_pairs():
    import app.main as main_module
    from app.regions import REGIONS
    readings = [p for presets in main_module.SCENARIO_PRESETS.values() for p in presets.values()]
    readings += [main_module.EnvironmentalReading(**cfg.initial_env) for cfg in REGIONS.values()]
    for r in readings:
        assert r.aqi == naqi_from_pm(r.pm25, r.pm10), (r.corridor, r.aqi, r.pm25)
