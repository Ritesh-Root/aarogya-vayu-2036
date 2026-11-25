import os
import time
import json
import logging
import statistics
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from app.naqi import naqi_from_pm
from app.regions import get_region
from app.models import EnvironmentalReading

logger = logging.getLogger("aarogya_vayu.telemetry")

def coordinates_for(region: str) -> dict:
    """Centroid and heatwave threshold for a region, from the registry (unknown regions raise)."""
    cfg = get_region(region)
    return {
        "lat": cfg.centroid[0],
        "lng": cfg.centroid[1],
        "name": cfg.label,
        "district": cfg.centroid_district,
        "heatwave_threshold_c": cfg.heatwave_threshold_c,
    }


IST = timezone(timedelta(hours=5, minutes=30))
USER_AGENT = {"User-Agent": "AarogyaVayu/2.0 (Health Logistics Resilience)"}
FIRMS_BBOX_DEG = 1.5  # ~165 km around the corridor centroid
FORECAST_HOURS = 72
LIVE_SOURCE_PREFIX = "Open-Meteo"
FAILURE_RETRY_S = 60  # after a failed fetch, serve the fallback for this long instead of re-waiting on timeouts
# IMD thresholds (SOP for Weather Forecasting and Warning): "very heavy rain" in 24 h, and the
# cold-wave minimum for the plains (actual minimum <= 4 °C)
FLOOD_RAIN_MM = 115.6
COLD_WAVE_MIN_C = 4.0
STALE_AFTER_S = 3600  # a cached reading older than this is no longer presented as live


def is_live_reading(reading: EnvironmentalReading) -> bool:
    return (reading.source or "").startswith(LIVE_SOURCE_PREFIX)


def _get_json(url: str, timeout: float = 5) -> dict:
    req = urllib.request.Request(url, headers=USER_AGENT)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _split_hourly(times: List[str], values: List[Optional[float]], now_local: datetime):
    """Split an hourly series into (past, next-72h) lists of (hours_from_now, value), skipping nulls."""
    past, future = [], []
    for t, v in zip(times, values):
        if v is None:
            continue
        delta_h = (datetime.fromisoformat(t).replace(tzinfo=IST) - now_local).total_seconds() / 3600
        if delta_h <= 0:
            past.append((delta_h, v))
        elif delta_h <= FORECAST_HOURS:
            future.append((delta_h, v))
    return past, future


class LiveTelemetryService:
    """
    Fetches real-time and forecast atmospheric telemetry:
      - Open-Meteo Weather (ECMWF/GFS): temperature, humidity, wind, boundary layer height, 72h forecast
      - Open-Meteo Air Quality (Copernicus CAMS): AQI, PM2.5/PM10, aerosol optical depth with
        30-day history (for the anomaly) and 72h forecast
      - NASA FIRMS VIIRS active fires, when FIRMS_MAP_KEY is configured
    Open-Meteo needs no API key.
    """
    def __init__(self, cache_ttl_seconds: int = 300):
        self.cache_ttl = cache_ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._failures: Dict[str, Dict[str, Any]] = {}

    def _fetch_fire_hotspots(self, lat: float, lng: float) -> Optional[int]:
        key = os.getenv("FIRMS_MAP_KEY")
        if not key:
            return None
        bbox = f"{lng - FIRMS_BBOX_DEG},{lat - FIRMS_BBOX_DEG},{lng + FIRMS_BBOX_DEG},{lat + FIRMS_BBOX_DEG}"
        url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/VIIRS_SNPP_NRT/{bbox}/2"
        try:
            req = urllib.request.Request(url, headers=USER_AGENT)
            with urllib.request.urlopen(req, timeout=5) as resp:
                body = resp.read().decode("utf-8").strip()
            lines = body.splitlines()
            if not lines or not lines[0].startswith("latitude"):
                logger.warning("Unexpected NASA FIRMS response: %s", body[:120])
                return None
            return len(lines) - 1
        except Exception as e:
            logger.warning("NASA FIRMS fetch failed: %s", e)
            return None

    def fetch_live_reading(self, region: str = "bhubaneswar") -> EnvironmentalReading:
        reg = region.lower()
        coords = coordinates_for(reg)

        # Check cache (successes for cache_ttl; failures for FAILURE_RETRY_S)
        now = time.time()
        cached = self._cache.get(reg)
        if cached and (now - cached["timestamp"] < self.cache_ttl):
            return cached["reading"]
        failed = self._failures.get(reg)
        if failed and now - failed["timestamp"] < FAILURE_RETRY_S:
            return failed["reading"]

        try:
            lat, lng = coords["lat"], coords["lng"]
            w_data = _get_json(
                f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}"
                f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
                f"&hourly=temperature_2m,boundary_layer_height&daily=precipitation_sum,temperature_2m_min"
                f"&past_days=1&forecast_days=4"
                f"&timezone=Asia%2FKolkata"
            )
            aq_data = _get_json(
                f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lng}"
                f"&current=pm10,pm2_5,us_aqi,aerosol_optical_depth"
                f"&hourly=pm2_5,pm10,aerosol_optical_depth&past_days=30&forecast_days=4"
                f"&timezone=Asia%2FKolkata"
            )

            curr_w = w_data.get("current", {})
            curr_aq = aq_data.get("current", {})

            temp_c = float(curr_w["temperature_2m"])
            humidity = float(curr_w["relative_humidity_2m"])
            wind_kmh = float(curr_w["wind_speed_10m"])
            pm25 = float(curr_aq["pm2_5"])
            pm10 = float(curr_aq["pm10"]) if curr_aq.get("pm10") is not None else None
            us_aqi = int(curr_aq["us_aqi"]) if curr_aq.get("us_aqi") is not None else None
            aqi = naqi_from_pm(pm25, pm10)  # India NAQI: the scale the surge bands are written for
            aod = curr_aq.get("aerosol_optical_depth")

            now_local = datetime.now(IST).replace(minute=0, second=0, microsecond=0)
            w_hourly = w_data.get("hourly", {})
            aq_hourly = aq_data.get("hourly", {})
            times_w = w_hourly.get("time", [])
            times_aq = aq_hourly.get("time", [])

            _, temp_fc = _split_hourly(times_w, w_hourly.get("temperature_2m", []), now_local)
            blh_past, _ = _split_hourly(times_w, w_hourly.get("boundary_layer_height", []), now_local)
            pm25_series = aq_hourly.get("pm2_5", [])
            pm10_series = aq_hourly.get("pm10", [])
            naqi_series = [
                None if (p25 is None and p10 is None) else naqi_from_pm(p25, p10)
                for p25, p10 in zip(pm25_series, list(pm10_series) + [None] * (len(pm25_series) - len(pm10_series)))
            ]
            _, aqi_fc = _split_hourly(times_aq, naqi_series, now_local)
            _, pm25_fc = _split_hourly(times_aq, aq_hourly.get("pm2_5", []), now_local)
            aod_past, _ = _split_hourly(times_aq, aq_hourly.get("aerosol_optical_depth", []), now_local)

            aod_sigma = None
            aod_hist = [v for _, v in aod_past]
            if aod is not None and len(aod_hist) >= 48:
                sd = statistics.pstdev(aod_hist)
                if sd > 0:
                    aod_sigma = round((float(aod) - statistics.fmean(aod_hist)) / sd, 2)

            peak_h, peak_aqi = max(aqi_fc, key=lambda x: x[1]) if aqi_fc else (None, None)
            max_temp_72h = max(v for _, v in temp_fc) if temp_fc else None
            boundary_layer = blh_past[-1][1] if blh_past else None
            fires = self._fetch_fire_hotspots(lat, lng)

            hottest = max(temp_c, max_temp_72h or temp_c)
            daily = w_data.get("daily", {})
            rain_days = [float(v) for v in daily.get("precipitation_sum", []) if v is not None]
            tmin_days = [float(v) for v in daily.get("temperature_2m_min", []) if v is not None]
            rain_24h = max(rain_days) if rain_days else None
            min_temp = min(tmin_days) if tmin_days else None
            reading = EnvironmentalReading(
                aqi=aqi,
                us_aqi=us_aqi,
                pm25=pm25,
                pm10=pm10,
                temperature_c=temp_c,
                humidity_pct=humidity,
                wind_speed_kmh=wind_kmh,
                heatwave_alert=hottest >= coords["heatwave_threshold_c"],
                smog_episode=(aqi >= 200 or pm25 >= 120.0 or (peak_aqi or 0) >= 200),
                flood_alert=rain_24h is not None and rain_24h >= FLOOD_RAIN_MM,
                cold_wave_alert=min_temp is not None and min_temp <= COLD_WAVE_MIN_C,
                rain_24h_mm=rain_24h,
                min_temp_c=min_temp,
                corridor=coords["name"],
                source=f"{LIVE_SOURCE_PREFIX} & Copernicus Atmospheric Monitoring Service (CAMS)"
                + (" + NASA FIRMS" if fires is not None else ""),
                recorded_at=curr_aq.get("time") or curr_w.get("time"),
                aod=float(aod) if aod is not None else None,
                aod_anomaly_sigma=aod_sigma,
                boundary_layer_m=boundary_layer,
                forecast_peak_aqi_72h=int(peak_aqi) if peak_aqi is not None else None,
                forecast_peak_pm25_72h=max(v for _, v in pm25_fc) if pm25_fc else None,
                forecast_peak_in_hours=round(peak_h) if peak_h is not None else None,
                forecast_max_temp_72h=max_temp_72h,
                fire_hotspots=fires,
            )

            self._cache[reg] = {
                "timestamp": now,
                "reading": reading
            }
            return reading

        except Exception as e:
            logger.warning("Could not fetch Open-Meteo telemetry for %s: %s", region, e)
            if cached and now - cached["timestamp"] < STALE_AFTER_S:
                reading = cached["reading"]
            elif cached:
                # Too old to present as live: same values, explicitly labelled stale (is_live_reading() is False)
                age_min = round((now - cached["timestamp"]) / 60)
                reading = cached["reading"].model_copy(update={
                    "source": f"Stale: last Open-Meteo/CAMS reading {age_min} min ago (live feed unavailable)",
                })
            else:
                # Clearly labelled offline baseline; never shows as live
                fb = get_region(reg).fallback_env
                reading = EnvironmentalReading(
                    aqi=fb["aqi"],
                    pm25=fb["pm25"],
                    temperature_c=fb["temperature_c"],
                    humidity_pct=fb["humidity_pct"],
                    wind_speed_kmh=fb["wind_speed_kmh"],
                    heatwave_alert=False,
                    smog_episode=False,
                    corridor=f"{coords['name']} (Offline Baseline)",
                    source="Offline baseline (live feed unavailable)"
                )
            self._failures[reg] = {"timestamp": now, "reading": reading}
            return reading

telemetry_service = LiveTelemetryService()
