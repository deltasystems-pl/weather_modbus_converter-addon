from __future__ import annotations

import json
from typing import Any

from .config import EcowittConfig
from .ecowitt import ecowitt_form_body


DATA_STRING_FIELDS: tuple[tuple[str, int | None], ...] = (
    ("temperature_c", 1),
    ("humidity_pct", 0),
    ("pressure_hpa", 1),
    ("pressure_sea_level_hpa", 1),
    ("illuminance_lx", 0),
    ("uv_index", 1),
    ("wind_speed_ms", 1),
    ("wind_gust_ms", 1),
    ("wind_direction_deg", 0),
    ("rain_total_mm", 1),
    ("rain_counter_mm", 2),
    ("rain_rate_mm_h", 2),
    ("rain_event_mm", 2),
    ("rain_hour_mm", 2),
    ("rain_last24h_mm", 2),
    ("rain_day_mm", 2),
    ("rain_week_mm", 2),
    ("rain_month_mm", 2),
    ("rain_year_mm", 2),
    ("rain_state", None),
    ("rain_level", None),
)


def data_string_payload(state: dict[str, Any]) -> str:
    return ",".join(
        f"{field}={_format_data_string_value(state.get(field), decimals)}"
        for field, decimals in DATA_STRING_FIELDS
    )


def external_mqtt_payload(state: dict[str, Any], payload_format: str, ecowitt: EcowittConfig) -> str:
    if payload_format == "json":
        return json.dumps(state, separators=(",", ":"))
    if payload_format == "data_string":
        return data_string_payload(state)
    if payload_format == "ecowitt":
        return ecowitt_form_body(state, ecowitt)
    raise ValueError(f"Unsupported external MQTT payload format: {payload_format}")


def _format_data_string_value(value: Any, decimals: int | None) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if decimals is None:
        return str(value)
    try:
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return "null"
