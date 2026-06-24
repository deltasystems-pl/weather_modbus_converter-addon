from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

from .config import EcowittConfig

SUNLIGHT_LUX_PER_WM2 = 126.7


def c_to_f(value: float | None) -> float | None:
    return None if value is None else round((value * 9 / 5) + 32, 2)


def ms_to_mph(value: float | None) -> float | None:
    return None if value is None else round(value * 2.2369362921, 2)


def hpa_to_inhg(value: float | None) -> float | None:
    return None if value is None else round(value * 0.0295299830714, 3)


def mm_to_in(value: float | None) -> float | None:
    return None if value is None else round(value * 0.03937007874, 3)


def lx_to_wm2(value: float | None) -> float | None:
    return None if value is None else round(value / SUNLIGHT_LUX_PER_WM2, 2)


def solar_wm2(state: dict[str, Any]) -> float | None:
    return state.get("solar_radiation_wm2") if state.get("solar_radiation_wm2") is not None else lx_to_wm2(state.get("illuminance_lx"))


def _rain_value(state: dict[str, Any], field: str, fallback_field: str | None = None) -> float | None:
    value = state.get(field)
    if value is not None:
        return value
    return state.get(fallback_field) if fallback_field else None


def ecowitt_payload(state: dict[str, Any], config: EcowittConfig | None = None) -> dict[str, str]:
    cfg = config or EcowittConfig()
    rain_total_in = mm_to_in(state.get("rain_total_mm"))
    payload: dict[str, Any] = {
        "PASSKEY": cfg.PASSKEY,
        "stationtype": cfg.stationtype,
        "model": cfg.model,
        "dateutc": _dateutc(state.get("observed_at")),
        "tempf": c_to_f(state.get("temperature_c")),
        "humidity": state.get("humidity_pct"),
        "baromrelin": hpa_to_inhg(state.get("pressure_sea_level_hpa") or state.get("pressure_hpa")),
        "baromabsin": hpa_to_inhg(state.get("pressure_hpa")),
        "solarradiation": solar_wm2(state),
        "uv": state.get("uv_index"),
        "windspeedmph": ms_to_mph(state.get("wind_speed_ms")),
        "windgustmph": ms_to_mph(state.get("wind_gust_ms")),
        "maxdailygust": ms_to_mph(state.get("wind_gust_ms")),
        "winddir": state.get("wind_direction_deg"),
        "totalrainin": rain_total_in,
        "rainin": mm_to_in(state.get("rain_delta_mm")),
        "rrain_piezo": mm_to_in(_rain_value(state, "rain_rate_mm_h", "rain_delta_mm")),
        "erain_piezo": mm_to_in(_rain_value(state, "rain_event_mm")),
        "hrain_piezo": mm_to_in(_rain_value(state, "rain_hour_mm")),
        "last24hrain_piezo": mm_to_in(_rain_value(state, "rain_last24h_mm")),
        "drain_piezo": mm_to_in(_rain_value(state, "rain_day_mm")),
        "wrain_piezo": mm_to_in(_rain_value(state, "rain_week_mm", "rain_total_mm")),
        "mrain_piezo": mm_to_in(_rain_value(state, "rain_month_mm", "rain_total_mm")),
        "yrain_piezo": mm_to_in(_rain_value(state, "rain_year_mm", "rain_total_mm")),
        "srain_piezo": int(bool(state.get("rain_state"))),
    }
    return {key: str(value) for key, value in payload.items() if value is not None}


def ecowitt_form_body(state: dict[str, Any], config: EcowittConfig | None = None) -> str:
    return urlencode(ecowitt_payload(state, config))


def _dateutc(observed_at: str | None) -> str:
    if not observed_at:
        return "now"
    try:
        dt = datetime.fromisoformat(observed_at.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return "now"
    return dt.strftime("%Y-%m-%d %H:%M:%S")
