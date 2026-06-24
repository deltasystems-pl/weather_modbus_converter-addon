from __future__ import annotations

import json
from typing import Any

from .config import MqttConfig


DISCOVERY_FIELDS = {
    "temperature_c": ("temperature", "Temperature", "temperature", "C"),
    "humidity_pct": ("humidity", "Humidity", "humidity", "%"),
    "pressure_hpa": ("pressure", "Pressure", "pressure", "hPa"),
    "pressure_sea_level_hpa": ("pressure_sea_level", "Sea Level Pressure", "pressure", "hPa"),
    "illuminance_lx": ("illuminance", "Illuminance", "illuminance", "lx"),
    "uv_index": ("uv_index", "UV Index", None, None),
    "wind_speed_ms": ("wind_speed", "Wind Speed", "wind_speed", "m/s"),
    "wind_gust_ms": ("wind_gust", "Wind Gust", "wind_speed", "m/s"),
    "wind_direction_deg": ("wind_direction", "Wind Direction", None, "deg"),
    "wind_direction_compass": ("wind_direction_compass", "Wind Direction Compass", None, None),
    "solar_radiation_wm2": ("solar_radiation", "Solar Radiation", "irradiance", "W/m²"),
    "dew_point_c": ("dew_point", "Dew Point", "temperature", "C"),
    "wind_chill_c": ("wind_chill", "Wind Chill", "temperature", "C"),
    "feels_like_c": ("feels_like", "Feels Like", "temperature", "C"),
    "sun_feels_like_c": ("sun_feels_like", "Sun Feels Like", "temperature", "C"),
    "uv_level": ("uv_level", "UV Level", None, None),
    "solar_radiation_level": ("solar_radiation_level", "Solar Radiation Level", None, None),
    "temperature_level": ("temperature_level", "Temperature Level", None, None),
    "pressure_level": ("pressure_level", "Pressure Level", None, None),
    "humidity_level": ("humidity_level", "Humidity Level", None, None),
    "wind_level": ("wind_level", "Wind Level", None, None),
    "rain_total_mm": ("rain_total", "Rain Total", "precipitation", "mm"),
    "rain_counter_mm": ("rain_counter", "Rain Counter", "precipitation", "mm"),
    "rain_delta_mm": ("rain_delta", "Rain Delta", "precipitation", "mm"),
    "rain_rate_mm_h": ("rain_rate", "Rain Rate", "precipitation_intensity", "mm/h"),
    "rain_event_mm": ("rain_event", "Rain Event", "precipitation", "mm"),
    "rain_hour_mm": ("rain_hour", "Rain Hour", "precipitation", "mm"),
    "rain_last24h_mm": ("rain_last24h", "Rain Last 24 Hours", "precipitation", "mm"),
    "rain_day_mm": ("rain_day", "Rain Day", "precipitation", "mm"),
    "rain_week_mm": ("rain_week", "Rain Week", "precipitation", "mm"),
    "rain_month_mm": ("rain_month", "Rain Month", "precipitation", "mm"),
    "rain_year_mm": ("rain_year", "Rain Year", "precipitation", "mm"),
    "rain_level": ("rain_level", "Rain Level", None, None),
}

BINARY_DISCOVERY_FIELDS = {
    "rain_state": ("rain_state", "Rain State", "moisture"),
}


class MqttPublisher:
    def __init__(self, config: MqttConfig) -> None:
        self.config = config
        self.discovery_topic = f"{config.discovery_prefix}/device/ws90lp_bridge/config"
        self.state_topic = f"{config.base_topic}/state"
        self.availability_topic = f"{config.base_topic}/status"
        self.error_topic = f"{config.base_topic}/error"
        try:
            import paho.mqtt.client as mqtt
        except ModuleNotFoundError as exc:
            raise RuntimeError("paho-mqtt is required for MQTT publishing; install requirements.txt") from exc
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=config.client_id)
        if config.username is not None and config.username != "":
            self.client.username_pw_set(config.username, config.password)

    def connect(self) -> None:
        self.client.connect(self.config.host, self.config.port)
        self.client.loop_start()

    def close(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()

    def publish_discovery(self) -> None:
        payload = discovery_payload(self.config)
        self.client.publish(self.discovery_topic, json.dumps(payload), retain=True)

    def publish_state(self, state: dict[str, Any]) -> None:
        self.client.publish(self.state_topic, json.dumps(state, separators=(",", ":")), retain=False)

    def publish_json(self, topic: str, payload: dict[str, Any], retain: bool = False) -> None:
        self.client.publish(topic, json.dumps(payload, separators=(",", ":")), retain=retain)

    def publish_text(self, topic: str, payload: str, retain: bool = False) -> None:
        self.client.publish(topic, payload, retain=retain)

    def publish_availability(self, online: bool) -> None:
        self.client.publish(self.availability_topic, "online" if online else "offline", retain=True)

    def publish_error(self, message: str) -> None:
        self.client.publish(self.error_topic, message, retain=False)


def discovery_payload(config: MqttConfig) -> dict[str, Any]:
    availability_topic = f"{config.base_topic}/status"
    state_topic = f"{config.base_topic}/state"
    components: dict[str, Any] = {}
    for field, (object_suffix, name, device_class, unit) in DISCOVERY_FIELDS.items():
        sensor: dict[str, Any] = {
            "p": "sensor",
            "unique_id": f"ws90lp_bridge_{object_suffix}",
            "object_id": f"ws90lp_{object_suffix}",
            "name": name,
            "state_topic": state_topic,
            "availability_topic": availability_topic,
            "value_template": f"{{{{ value_json.{field} }}}}",
        }
        if device_class:
            sensor["device_class"] = device_class
        if unit:
            sensor["unit_of_measurement"] = unit
        components[object_suffix] = sensor
    for field, (object_suffix, name, device_class) in BINARY_DISCOVERY_FIELDS.items():
        binary_sensor: dict[str, Any] = {
            "p": "binary_sensor",
            "unique_id": f"ws90lp_bridge_{object_suffix}",
            "object_id": f"ws90lp_{object_suffix}",
            "name": name,
            "state_topic": state_topic,
            "availability_topic": availability_topic,
            "value_template": f"{{{{ value_json.{field} }}}}",
            "payload_on": "true",
            "payload_off": "false",
        }
        if device_class:
            binary_sensor["device_class"] = device_class
        components[object_suffix] = binary_sensor
    return {
        "dev": {
            "ids": ["ws90lp_bridge"],
            "name": "WS90LP Weather Station",
            "mf": "WS90LP",
            "mdl": "WS90LP Modbus Bridge",
        },
        "o": {"name": "ws90lp-bridge", "sw": "0.1.0"},
        "cmps": components,
        "state_topic": state_topic,
        "availability_topic": availability_topic,
        "qos": 0,
    }
