from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .decode import STATE_FIELDS

ALLOWED_PROTOCOL_MODES = ("rtu_over_tcp", "modbus_tcp_gateway")
ALLOWED_LIVE_READ_MODES = ("block", "single")
ALLOWED_EXTERNAL_MQTT_FORMATS = ("json", "data_string", "ecowitt")


@dataclass
class MqttConfig:
    host: str = "core-mosquitto"
    port: int = 1883
    username: str | None = None
    password: str | None = None
    discovery_prefix: str = "homeassistant"
    base_topic: str = "ws90lp_bridge/ws90lp"
    client_id: str = "ws90lp_bridge"


@dataclass
class ExternalMqttConfig:
    enabled: bool = False
    host: str = ""
    port: int = 1883
    username: str | None = None
    password: str | None = None
    client_id: str = "ws90lp_bridge_external"
    topic: str = ""
    payload_format: str = "data_string"
    interval_seconds: float = 60.0
    retain: bool = False


@dataclass
class DashboardConfig:
    config_dir: str = "/config"
    title: str = "Pogoda"
    icon: str = "mdi:weather-partly-cloudy"
    url_path: str = "pogoda-ws90lp"
    show_in_sidebar: bool = True


@dataclass
class WebhookConfig:
    url: str
    format: str = "json"
    timeout_seconds: float = 5.0
    retries: int = 2


@dataclass
class EcowittConfig:
    PASSKEY: str = "RS485_WS90LP"
    stationtype: str = "WS90LP_Modbus_Bridge"
    model: str = "WS90LP"


@dataclass
class ScheduledReadConfig:
    name: str
    interval_seconds: float
    fields: list[str]
    outputs: list["ScheduledOutputConfig"] = field(default_factory=list)


@dataclass
class ScheduledOutputConfig:
    type: str
    mqtt_topic: str | None = None
    retain: bool = False
    url: str | None = None
    format: str = "json"
    timeout_seconds: float = 5.0
    retries: int = 2


@dataclass
class BridgeConfig:
    protocol_mode: str = "rtu_over_tcp"
    live_read_mode: str = "block"
    host: str = ""
    port: int = 502
    unit_id: int = 144
    poll_interval_seconds: float = 10.0
    timeout_seconds: float = 3.0
    failure_threshold: int = 3
    log_level: str = "INFO"
    station_elevation_m: float = 188.0
    mqtt: MqttConfig = field(default_factory=MqttConfig)
    external_mqtt: ExternalMqttConfig = field(default_factory=ExternalMqttConfig)
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)
    webhooks: list[WebhookConfig] = field(default_factory=list)
    ecowitt: EcowittConfig = field(default_factory=EcowittConfig)
    scheduled_reads: list[ScheduledReadConfig] = field(default_factory=list)


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _defaults() -> dict[str, Any]:
    cfg = BridgeConfig()
    return {
        "protocol_mode": cfg.protocol_mode,
        "live_read_mode": cfg.live_read_mode,
        "host": cfg.host,
        "port": cfg.port,
        "unit_id": cfg.unit_id,
        "poll_interval_seconds": cfg.poll_interval_seconds,
        "timeout_seconds": cfg.timeout_seconds,
        "failure_threshold": cfg.failure_threshold,
        "log_level": cfg.log_level,
        "station_elevation_m": cfg.station_elevation_m,
        "mqtt": MqttConfig().__dict__,
        "external_mqtt": ExternalMqttConfig().__dict__,
        "dashboard": DashboardConfig().__dict__,
        "webhooks": [],
        "ecowitt": EcowittConfig().__dict__,
        "scheduled_reads": [],
    }


def load_config(path: str | Path | None = None, overrides: dict[str, Any] | None = None) -> BridgeConfig:
    data = _defaults()
    if path:
        loaded = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            raise ValueError(f"Config file {path} must contain a mapping")
        data = deep_merge(data, loaded)
    if overrides:
        data = deep_merge(data, {k: v for k, v in overrides.items() if v is not None})
    return parse_config(data)


def parse_config(data: dict[str, Any]) -> BridgeConfig:
    mqtt = MqttConfig(**(data.get("mqtt") or {}))
    external_mqtt = _parse_external_mqtt(data.get("external_mqtt") or {})
    dashboard = _parse_dashboard(data.get("dashboard") or {})
    webhooks = [WebhookConfig(**item) for item in (data.get("webhooks") or []) if item.get("url")]
    ecowitt = EcowittConfig(**(data.get("ecowitt") or {}))
    scheduled_reads = [_parse_scheduled_read(item, mqtt) for item in (data.get("scheduled_reads") or [])]
    protocol_mode = str(data.get("protocol_mode", "rtu_over_tcp"))
    if protocol_mode not in ALLOWED_PROTOCOL_MODES:
        allowed = ", ".join(ALLOWED_PROTOCOL_MODES)
        raise ValueError(f"Unsupported protocol_mode {protocol_mode!r}. Valid values: {allowed}")
    live_read_mode = str(data.get("live_read_mode", "block"))
    if live_read_mode not in ALLOWED_LIVE_READ_MODES:
        allowed = ", ".join(ALLOWED_LIVE_READ_MODES)
        raise ValueError(f"Unsupported live_read_mode {live_read_mode!r}. Valid values: {allowed}")
    return BridgeConfig(
        protocol_mode=protocol_mode,
        live_read_mode=live_read_mode,
        host=data.get("host", ""),
        port=int(data.get("port", 502)),
        unit_id=int(data.get("unit_id", 144)),
        poll_interval_seconds=float(data.get("poll_interval_seconds", 10)),
        timeout_seconds=float(data.get("timeout_seconds", 3)),
        failure_threshold=int(data.get("failure_threshold", 3)),
        log_level=str(data.get("log_level", "INFO")).upper(),
        station_elevation_m=float(data.get("station_elevation_m", 188.0)),
        mqtt=mqtt,
        external_mqtt=external_mqtt,
        dashboard=dashboard,
        webhooks=webhooks,
        ecowitt=ecowitt,
        scheduled_reads=scheduled_reads,
    )


def _parse_external_mqtt(data: dict[str, Any]) -> ExternalMqttConfig:
    if not isinstance(data, dict):
        raise ValueError("external_mqtt must be a mapping")
    config = ExternalMqttConfig(**data)
    config.payload_format = str(config.payload_format).strip()
    if config.payload_format not in ALLOWED_EXTERNAL_MQTT_FORMATS:
        allowed = ", ".join(ALLOWED_EXTERNAL_MQTT_FORMATS)
        raise ValueError(f"Unsupported external_mqtt.payload_format {config.payload_format!r}. Valid values: {allowed}")
    config.host = str(config.host or "").strip()
    config.topic = str(config.topic or "").strip()
    config.port = int(config.port)
    config.interval_seconds = float(config.interval_seconds)
    config.retain = bool(config.retain)
    if config.enabled:
        if not config.host:
            raise ValueError("external_mqtt.host is required when external_mqtt.enabled is true")
        if not config.topic:
            raise ValueError("external_mqtt.topic is required when external_mqtt.enabled is true")
        if config.interval_seconds <= 0:
            raise ValueError("external_mqtt.interval_seconds must be greater than 0")
    return config


def _parse_dashboard(data: dict[str, Any]) -> DashboardConfig:
    if not isinstance(data, dict):
        raise ValueError("dashboard must be a mapping")
    config = DashboardConfig(**data)
    config.config_dir = str(config.config_dir or "/config").strip() or "/config"
    config.title = str(config.title or "Pogoda").strip() or "Pogoda"
    config.icon = str(config.icon or "mdi:weather-partly-cloudy").strip() or "mdi:weather-partly-cloudy"
    config.url_path = _dashboard_url_path(config.url_path)
    config.show_in_sidebar = bool(config.show_in_sidebar)
    return config


def _dashboard_url_path(value: str) -> str:
    cleaned = "".join(
        char.lower() if char.isalnum() else "-"
        for char in str(value or "pogoda-ws90lp").strip()
    )
    cleaned = "-".join(part for part in cleaned.split("-") if part)
    if not cleaned:
        cleaned = "pogoda-ws90lp"
    if cleaned != "lovelace" and "-" not in cleaned:
        cleaned = f"{cleaned}-ws90lp"
    return cleaned


def _parse_scheduled_read(data: dict[str, Any], mqtt: MqttConfig) -> ScheduledReadConfig:
    if not isinstance(data, dict):
        raise ValueError("Each scheduled_reads item must be a mapping")
    name = str(data.get("name") or "").strip()
    if not name:
        raise ValueError("Each scheduled_reads item needs a name")
    fields = data.get("fields") or []
    if not isinstance(fields, list) or not fields:
        raise ValueError(f"scheduled_reads.{name}.fields must be a non-empty list")
    invalid = [field for field in fields if field not in STATE_FIELDS]
    if invalid:
        valid = ", ".join(STATE_FIELDS)
        raise ValueError(f"scheduled_reads.{name} has invalid fields {invalid}. Valid fields: {valid}")
    interval = float(data.get("interval_seconds", 60))
    if interval <= 0:
        raise ValueError(f"scheduled_reads.{name}.interval_seconds must be greater than 0")
    outputs = _parse_scheduled_outputs(data, mqtt, name)
    return ScheduledReadConfig(
        name=name,
        interval_seconds=interval,
        fields=list(fields),
        outputs=outputs,
    )


def _parse_scheduled_outputs(data: dict[str, Any], mqtt: MqttConfig, schedule_name: str) -> list[ScheduledOutputConfig]:
    raw_outputs = data.get("outputs")
    if raw_outputs is None:
        raw_outputs = [
            {
                "type": "mqtt",
                "mqtt_topic": data.get("mqtt_topic") or f"{mqtt.base_topic}/scheduled/{schedule_name}",
                "retain": data.get("retain", False),
            }
        ]
    if not isinstance(raw_outputs, list) or not raw_outputs:
        raise ValueError(f"scheduled_reads.{schedule_name}.outputs must be a non-empty list")

    outputs: list[ScheduledOutputConfig] = []
    for item in raw_outputs:
        if not isinstance(item, dict):
            raise ValueError(f"scheduled_reads.{schedule_name}.outputs entries must be mappings")
        output_type = str(item.get("type") or "").strip()
        if output_type not in {"mqtt", "webhook"}:
            raise ValueError(f"scheduled_reads.{schedule_name}.outputs type must be mqtt or webhook")
        if output_type == "mqtt":
            outputs.append(
                ScheduledOutputConfig(
                    type="mqtt",
                    mqtt_topic=str(item.get("mqtt_topic") or f"{mqtt.base_topic}/scheduled/{schedule_name}"),
                    retain=bool(item.get("retain", False)),
                )
            )
        else:
            url = str(item.get("url") or "").strip()
            if not url:
                continue
            outputs.append(
                ScheduledOutputConfig(
                    type="webhook",
                    url=url,
                    format=str(item.get("format", "json")),
                    timeout_seconds=float(item.get("timeout_seconds", 5)),
                    retries=int(item.get("retries", 2)),
                )
            )
    if not outputs:
        raise ValueError(f"scheduled_reads.{schedule_name}.outputs must contain at least one enabled output")
    return outputs


def redact_config(config: BridgeConfig) -> dict[str, Any]:
    data = {
        "protocol_mode": config.protocol_mode,
        "live_read_mode": config.live_read_mode,
        "host": config.host,
        "port": config.port,
        "unit_id": config.unit_id,
        "poll_interval_seconds": config.poll_interval_seconds,
        "timeout_seconds": config.timeout_seconds,
        "failure_threshold": config.failure_threshold,
        "log_level": config.log_level,
        "station_elevation_m": config.station_elevation_m,
        "mqtt": dict(config.mqtt.__dict__),
        "external_mqtt": dict(config.external_mqtt.__dict__),
        "webhooks": [dict(item.__dict__) for item in config.webhooks],
        "ecowitt": dict(config.ecowitt.__dict__),
        "scheduled_reads": [
            {
                "name": item.name,
                "interval_seconds": item.interval_seconds,
                "fields": item.fields,
                "outputs": [dict(output.__dict__) for output in item.outputs],
            }
            for item in config.scheduled_reads
        ],
    }
    for key in ("password",):
        if data["mqtt"].get(key):
            data["mqtt"][key] = "***"
        if data["external_mqtt"].get(key):
            data["external_mqtt"][key] = "***"
    if data["ecowitt"].get("PASSKEY"):
        data["ecowitt"]["PASSKEY"] = "***"
    return data
