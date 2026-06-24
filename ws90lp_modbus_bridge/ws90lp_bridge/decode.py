from __future__ import annotations

from datetime import UTC, datetime
from math import exp, floor, log, pow
from typing import Any

from .rain import with_rain_defaults

START_REGISTER = 0x0165
END_REGISTER = 0x016E
REGISTER_COUNT = END_REGISTER - START_REGISTER + 1
INVALID_RAW = 0xFFFF
DEFAULT_STATION_ELEVATION_M = 188.0
SUNLIGHT_LUX_PER_WM2 = 126.7
DATA_RATE_CODES = {
    1: 4800,
    2: 9600,
    3: 19200,
    4: 115200,
}
HISTORY_SAMPLES = 30
HISTORY_BLOCKS = {
    "max_illuminance_lx": (0x9B14, 10),
    "max_uv_index": (0x9B32, 0.1),
    "avg_temperature_c": (0x9B50, "temperature"),
    "avg_humidity_pct": (0x9B6E, 1),
    "avg_wind_speed_ms": (0x9B8C, 0.1),
    "max_gust_ms": (0x9BAA, 0.1),
    "avg_wind_direction_deg": (0x9BC8, 1),
    "rainfall_mm": (0x9BE6, 0.1),
    "avg_pressure_hpa": (0x9C04, 0.1),
    "avg_battery_voltage_v": (0x9C22, 0.01),
    "avg_capacitance_voltage_v": (0x9C40, 0.1),
}
ON_DEMAND_REGISTERS = {
    "illuminance_lx": (0x9C92, 10),
    "uv_index": (0x9C93, 0.1),
    "temperature_c": (0x9C94, "temperature"),
    "humidity_pct": (0x9C95, 1),
    "wind_speed_ms": (0x9C96, 0.1),
    "wind_gust_ms": (0x9C97, 0.1),
    "wind_direction_deg": (0x9C98, 1),
    "pressure_hpa": (0x9C9A, 0.1),
}
STATE_FIELDS = (
    "observed_at",
    "temperature_c",
    "humidity_pct",
    "pressure_hpa",
    "pressure_sea_level_hpa",
    "illuminance_lx",
    "uv_index",
    "wind_speed_ms",
    "wind_gust_ms",
    "wind_direction_deg",
    "wind_direction_compass",
    "solar_radiation_wm2",
    "dew_point_c",
    "wind_chill_c",
    "feels_like_c",
    "sun_feels_like_c",
    "uv_level",
    "solar_radiation_level",
    "temperature_level",
    "pressure_level",
    "humidity_level",
    "wind_level",
    "rain_total_mm",
    "rain_counter_mm",
    "rain_delta_mm",
    "rain_rate_mm_h",
    "rain_event_mm",
    "rain_hour_mm",
    "rain_last24h_mm",
    "rain_day_mm",
    "rain_week_mm",
    "rain_month_mm",
    "rain_year_mm",
    "rain_state",
    "rain_level",
    "modbus_ok",
)


def _valid(raw: int) -> int | None:
    return None if raw == INVALID_RAW else raw


def _scale(raw: int, factor: float) -> float | None:
    value = _valid(raw)
    return None if value is None else round(value * factor, 3)


def _temperature(raw: int) -> float | None:
    value = _valid(raw)
    return None if value is None else round((value - 400) / 10, 1)


def _decode_value(raw: int, scale: float | str) -> float | None:
    if scale == "temperature":
        return _temperature(raw)
    return _scale(raw, scale)


def pressure_to_sea_level_hpa(
    pressure_hpa: float | None,
    temperature_c: float | None,
    station_elevation_m: float = DEFAULT_STATION_ELEVATION_M,
) -> float | None:
    if pressure_hpa is None or temperature_c is None:
        return None
    station_temp_k = temperature_c + 273.15
    if station_temp_k <= 0:
        return None
    lapse_rate_k_per_m = 0.0065
    gravity_m_s2 = 9.80665
    dry_air_gas_constant = 287.053
    exponent = gravity_m_s2 / (dry_air_gas_constant * lapse_rate_k_per_m)
    sea_level_temp_ratio = (station_temp_k + (lapse_rate_k_per_m * station_elevation_m)) / station_temp_k
    return round(pressure_hpa * pow(sea_level_temp_ratio, exponent), 1)


def wind_direction_compass(degrees: float | None) -> str | None:
    if degrees is None:
        return None
    directions = (
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
    )
    return directions[int(floor((degrees + 11.25) / 22.5)) % 16]


def solar_radiation_wm2(illuminance_lx: float | None) -> float | None:
    return None if illuminance_lx is None else round(illuminance_lx / SUNLIGHT_LUX_PER_WM2, 2)


def uv_level(uv_index: float | None) -> str | None:
    if uv_index is None:
        return None
    if uv_index <= 2:
        return "Low"
    if uv_index <= 5:
        return "Moderate"
    if uv_index <= 7:
        return "High"
    if uv_index <= 10:
        return "Very High"
    return "Extreme"


def solar_radiation_level(radiation_wm2: float | None) -> str | None:
    if radiation_wm2 is None:
        return None
    if radiation_wm2 <= 50:
        return "Overcast"
    if radiation_wm2 <= 200:
        return "Partly Cloudy"
    if radiation_wm2 <= 400:
        return "Mostly Clear"
    if radiation_wm2 <= 700:
        return "Clear Sky"
    return "Bright Sunshine"


def temperature_level(temperature_c: float | None) -> str | None:
    if temperature_c is None:
        return None
    if temperature_c <= 0:
        return "Freezing"
    if temperature_c <= 10:
        return "Cold"
    if temperature_c <= 18:
        return "Cool"
    if temperature_c <= 26:
        return "Comfortable"
    if temperature_c <= 30:
        return "Warm"
    return "Hot"


def pressure_level(pressure_hpa: float | None) -> str | None:
    if pressure_hpa is None:
        return None
    if pressure_hpa <= 980:
        return "Stormy"
    if pressure_hpa <= 1000:
        return "Low"
    if pressure_hpa <= 1020:
        return "Normal"
    if pressure_hpa <= 1040:
        return "High"
    return "Very High"


def humidity_level(humidity_pct: float | None) -> str | None:
    if humidity_pct is None:
        return None
    if humidity_pct <= 25:
        return "Very Dry"
    if humidity_pct <= 40:
        return "Dry"
    if humidity_pct <= 60:
        return "Comfortable"
    if humidity_pct <= 80:
        return "Humid"
    return "Very Humid"


def wind_level(wind_speed_ms: float | None, wind_gust_ms: float | None = None) -> str | None:
    values = [value for value in (wind_speed_ms, wind_gust_ms) if value is not None]
    if not values:
        return None
    wind_kmh = max(values) * 3.6
    if wind_kmh <= 5:
        return "Calm"
    if wind_kmh <= 20:
        return "Light"
    if wind_kmh <= 39:
        return "Moderate"
    if wind_kmh <= 65:
        return "Strong"
    if wind_kmh <= 90:
        return "Very Strong"
    return "Storm"


def dew_point_c(temperature_c: float | None, humidity_pct: float | None) -> float | None:
    if temperature_c is None or humidity_pct is None or humidity_pct <= 0:
        return None
    a = 17.27
    b = 237.7
    alpha = ((a * temperature_c) / (b + temperature_c)) + log(humidity_pct / 100)
    return round((b * alpha) / (a - alpha), 1)


def wind_chill_c(temperature_c: float | None, wind_speed_ms: float | None) -> float | None:
    if temperature_c is None or wind_speed_ms is None:
        return None
    wind_kmh = wind_speed_ms * 3.6
    if temperature_c > 10 or wind_kmh < 4.8:
        return None
    return round(
        13.12
        + (0.6215 * temperature_c)
        - (11.37 * pow(wind_kmh, 0.16))
        + (0.3965 * temperature_c * pow(wind_kmh, 0.16)),
        1,
    )


def _vapour_pressure_hpa(temperature_c: float, humidity_pct: float) -> float:
    return (humidity_pct / 100) * 6.105 * exp((17.27 * temperature_c) / (237.7 + temperature_c))


def feels_like_c(
    temperature_c: float | None,
    humidity_pct: float | None,
    wind_speed_ms: float | None,
) -> float | None:
    if temperature_c is None or humidity_pct is None or wind_speed_ms is None:
        return None
    if humidity_pct <= 0 or humidity_pct > 100:
        return None
    vapour_pressure = _vapour_pressure_hpa(temperature_c, humidity_pct)
    return round(temperature_c + (0.33 * vapour_pressure) - (0.70 * wind_speed_ms) - 4.00, 1)


def sun_feels_like_c(
    temperature_c: float | None,
    humidity_pct: float | None,
    wind_speed_ms: float | None,
    radiation_wm2: float | None,
) -> float | None:
    if temperature_c is None or humidity_pct is None or wind_speed_ms is None or radiation_wm2 is None:
        return None
    if humidity_pct <= 0 or humidity_pct > 100:
        return None
    vapour_pressure = _vapour_pressure_hpa(temperature_c, humidity_pct)
    radiation = max(radiation_wm2, 0)
    return round(
        temperature_c
        + (0.348 * vapour_pressure)
        - (0.70 * wind_speed_ms)
        + ((0.70 * radiation) / (wind_speed_ms + 10))
        - 4.25,
        1,
    )


def decode_registers(
    registers: list[int],
    observed_at: datetime | None = None,
    station_elevation_m: float = DEFAULT_STATION_ELEVATION_M,
) -> dict[str, Any]:
    if len(registers) != REGISTER_COUNT:
        raise ValueError(f"Expected {REGISTER_COUNT} registers, got {len(registers)}")

    observed = observed_at or datetime.now(UTC)
    rain_total = _scale(registers[7], 0.1)
    rain_counter = _scale(registers[9], 0.01)
    temperature = _temperature(registers[2])
    humidity = _scale(registers[3], 1)
    pressure = _scale(registers[8], 0.1)
    illuminance = _scale(registers[0], 10)
    uv = _scale(registers[1], 0.1)
    wind_speed = _scale(registers[4], 0.1)
    wind_gust = _scale(registers[5], 0.1)
    wind_direction = _scale(registers[6], 1)
    radiation = solar_radiation_wm2(illuminance)
    sea_level_pressure = pressure_to_sea_level_hpa(pressure, temperature, station_elevation_m)
    return with_rain_defaults({
        "observed_at": observed.isoformat().replace("+00:00", "Z"),
        "temperature_c": temperature,
        "humidity_pct": humidity,
        "pressure_hpa": pressure,
        "pressure_sea_level_hpa": sea_level_pressure,
        "illuminance_lx": illuminance,
        "uv_index": uv,
        "wind_speed_ms": wind_speed,
        "wind_gust_ms": wind_gust,
        "wind_direction_deg": wind_direction,
        "wind_direction_compass": wind_direction_compass(wind_direction),
        "solar_radiation_wm2": radiation,
        "dew_point_c": dew_point_c(temperature, humidity),
        "wind_chill_c": wind_chill_c(temperature, wind_speed),
        "feels_like_c": feels_like_c(temperature, humidity, wind_speed),
        "sun_feels_like_c": sun_feels_like_c(temperature, humidity, wind_speed, radiation),
        "uv_level": uv_level(uv),
        "solar_radiation_level": solar_radiation_level(radiation),
        "temperature_level": temperature_level(temperature),
        "pressure_level": pressure_level(sea_level_pressure),
        "humidity_level": humidity_level(humidity),
        "wind_level": wind_level(wind_speed, wind_gust),
        "rain_total_mm": rain_total,
        "rain_counter_mm": rain_counter,
        "rain_delta_mm": None,
        "modbus_ok": True,
    })


def decode_identity(registers: list[int]) -> dict[str, Any]:
    if len(registers) != 5:
        raise ValueError(f"Expected 5 identity registers, got {len(registers)}")
    data_rate_code = registers[1]
    return {
        "device_code": registers[0],
        "device_code_hex": f"0x{registers[0]:02X}",
        "data_rate_code": data_rate_code,
        "baud_rate": DATA_RATE_CODES.get(data_rate_code),
        "device_address": registers[2],
        "device_id": (registers[3] << 16) | registers[4],
        "device_id_msb": registers[3],
        "device_id_lsb": registers[4],
    }


def decode_on_demand(raw_values: dict[str, int]) -> dict[str, Any]:
    state: dict[str, Any] = {}
    for name, raw in raw_values.items():
        spec = ON_DEMAND_REGISTERS.get(name)
        if spec is None:
            continue
        state[name] = _decode_value(raw, spec[1])
    if "illuminance_lx" in state:
        state["solar_radiation_wm2"] = solar_radiation_wm2(state["illuminance_lx"])
    if "wind_direction_deg" in state:
        state["wind_direction_compass"] = wind_direction_compass(state["wind_direction_deg"])
    state["uv_level"] = uv_level(state.get("uv_index"))
    state["solar_radiation_level"] = solar_radiation_level(state.get("solar_radiation_wm2"))
    state["temperature_level"] = temperature_level(state.get("temperature_c"))
    state["pressure_level"] = pressure_level(state.get("pressure_hpa"))
    state["humidity_level"] = humidity_level(state.get("humidity_pct"))
    state["wind_level"] = wind_level(state.get("wind_speed_ms"), state.get("wind_gust_ms"))
    return state


def decode_history_blocks(raw_blocks: dict[str, list[int]]) -> dict[str, list[dict[str, Any]]]:
    history: dict[str, list[dict[str, Any]]] = {}
    for name, raw_values in raw_blocks.items():
        spec = HISTORY_BLOCKS.get(name)
        if spec is None:
            continue
        scale = spec[1]
        history[name] = [
            {
                "minutes_ago": index + 1,
                "value": _decode_value(raw, scale),
            }
            for index, raw in enumerate(raw_values)
        ]
    return history


def with_rain_delta(current: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
    if not previous:
        return current
    cur = current.get("rain_counter_mm")
    prev = previous.get("rain_counter_mm")
    if cur is None or prev is None:
        return current
    delta = cur - prev
    if delta < 0:
        delta = cur
    current["rain_delta_mm"] = round(delta, 3)
    return current
