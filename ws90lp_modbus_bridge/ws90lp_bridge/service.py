from __future__ import annotations

import json
import logging
import signal
import time
from typing import Any, Protocol

from .config import BridgeConfig, ExternalMqttConfig, MqttConfig, ScheduledOutputConfig, ScheduledReadConfig
from .ecowitt import ecowitt_form_body
from .decode import decode_registers, with_rain_delta
from .modbus import Ws90ModbusClient
from .mqtt import MqttPublisher
from .payloads import external_mqtt_payload
from .rain import RainAccumulator
from .web_ui import WeatherDashboardServer, WeatherUiStore
from .webhooks import form_payload, post_payload, post_webhook

LOG = logging.getLogger(__name__)


class RegisterReader(Protocol):
    def read_registers(self) -> list[int]:
        ...


def poll_once(config: BridgeConfig, reader: RegisterReader | None = None) -> dict[str, Any]:
    if not config.host and reader is None:
        raise ValueError("host is required")
    client = reader or Ws90ModbusClient(
        host=config.host,
        port=config.port,
        unit_id=config.unit_id,
        protocol_mode=config.protocol_mode,
        timeout_seconds=config.timeout_seconds,
    )
    if config.live_read_mode == "single" and hasattr(client, "read_registers_single"):
        registers = client.read_registers_single()
    else:
        registers = client.read_registers()
    return decode_registers(registers, station_elevation_m=config.station_elevation_m)


class BridgeService:
    def __init__(self, config: BridgeConfig, reader: RegisterReader | None = None) -> None:
        self.config = config
        self.reader = reader
        self.mqtt = MqttPublisher(config.mqtt)
        self.external_mqtt = _external_mqtt_publisher(config.external_mqtt) if config.external_mqtt.enabled else None
        self.external_mqtt_connected = False
        self.rain = RainAccumulator()
        self.failure_count = 0
        self.previous_state: dict[str, Any] | None = None
        self.next_scheduled_publish = {schedule.name: 0.0 for schedule in config.scheduled_reads}
        self.next_external_mqtt_publish = 0.0
        self.ui_store = WeatherUiStore(config.web_ui.title, config.web_ui.history_limit)
        self.web_ui = WeatherDashboardServer(config.web_ui, self.ui_store) if config.web_ui.enabled else None
        self.running = True

    def stop(self, *_args: object) -> None:
        self.running = False

    def run(self) -> None:
        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGINT, self.stop)
        self.start_web_ui()
        self.mqtt.connect()
        self.mqtt.publish_discovery()
        self.mqtt.publish_availability(True)
        self.connect_external_mqtt()
        try:
            while self.running:
                started = time.monotonic()
                try:
                    state = self.rain.update(with_rain_delta(poll_once(self.config, self.reader), self.previous_state))
                except Exception as exc:
                    self.handle_poll_failure(exc)
                else:
                    self.previous_state = state
                    self.failure_count = 0
                    self.ui_store.update_state(state)
                    self.mqtt.publish_availability(True)
                    self.mqtt.publish_state(state)
                    self.publish_optional_outputs(state)
                elapsed = time.monotonic() - started
                time.sleep(max(0.1, self.config.poll_interval_seconds - elapsed))
        finally:
            self.mqtt.publish_availability(False)
            self.ui_store.set_online(False)
            self.close_external_mqtt()
            self.stop_web_ui()
            self.mqtt.close()

    def handle_poll_failure(self, exc: Exception) -> None:
        self.failure_count += 1
        LOG.exception("Polling failed")
        self.ui_store.record_failure(str(exc))
        self.mqtt.publish_error(str(exc))
        if self.failure_count >= self.config.failure_threshold:
            self.mqtt.publish_availability(False)
            self.mqtt.publish_state({"modbus_ok": False, "error": str(exc)})

    def start_web_ui(self) -> None:
        if self.web_ui is None:
            return
        try:
            self.web_ui.start()
        except Exception as exc:
            self.report_optional_output_failure("web_ui.start", exc)

    def stop_web_ui(self) -> None:
        if self.web_ui is None:
            return
        try:
            self.web_ui.stop()
        except Exception:
            LOG.exception("Could not stop web UI")

    def publish_optional_outputs(self, state: dict[str, Any]) -> None:
        now = time.monotonic()
        self.publish_external_mqtt(state, now)
        self.publish_scheduled_reads(state, now)
        for webhook in self.config.webhooks:
            try:
                post_webhook(webhook, state, self.config.ecowitt)
            except Exception as exc:
                self.report_optional_output_failure("webhook", exc)

    def connect_external_mqtt(self) -> None:
        if getattr(self, "external_mqtt", None) is None:
            return
        try:
            self.external_mqtt.connect()
        except Exception as exc:
            self.external_mqtt_connected = False
            self.report_optional_output_failure("external_mqtt.connect", exc)
            return
        self.external_mqtt_connected = True

    def close_external_mqtt(self) -> None:
        if getattr(self, "external_mqtt", None) is None:
            return
        try:
            self.external_mqtt.close()
        except Exception:
            LOG.exception("Could not close external MQTT client")
        self.external_mqtt_connected = False

    def publish_external_mqtt(self, state: dict[str, Any], now: float) -> None:
        config = self.config.external_mqtt
        if getattr(self, "external_mqtt", None) is None or not config.enabled:
            return
        if now < getattr(self, "next_external_mqtt_publish", 0.0):
            return
        if not self.external_mqtt_connected:
            self.connect_external_mqtt()
            if not self.external_mqtt_connected:
                self.next_external_mqtt_publish = now + config.interval_seconds
                return
        payload = external_mqtt_payload(state, config.payload_format, self.config.ecowitt)
        try:
            self.external_mqtt.publish_text(config.topic, payload, retain=config.retain)
        except Exception as exc:
            self.external_mqtt_connected = False
            self.report_optional_output_failure("external_mqtt.publish", exc)
        self.next_external_mqtt_publish = now + config.interval_seconds

    def publish_scheduled_reads(self, state: dict[str, Any], now: float) -> None:
        for schedule in self.config.scheduled_reads:
            if now < self.next_scheduled_publish.get(schedule.name, 0.0):
                continue
            payload = scheduled_payload(state, schedule)
            for output in schedule.outputs:
                try:
                    self.publish_scheduled_output(state, payload, output)
                except Exception as exc:
                    self.report_optional_output_failure(f"scheduled_read.{schedule.name}.{output.type}", exc)
            self.next_scheduled_publish[schedule.name] = now + schedule.interval_seconds

    def publish_scheduled_output(
        self,
        full_state: dict[str, Any],
        payload: dict[str, Any],
        output: ScheduledOutputConfig,
    ) -> None:
        if output.type == "mqtt":
            self.mqtt.publish_json(output.mqtt_topic or self.config.mqtt.base_topic, payload, retain=output.retain)
            return
        if output.format == "json":
            post_payload(output.url or "", payload, "application/json", output.timeout_seconds, output.retries)
            return
        if output.format == "form":
            post_payload(output.url or "", form_payload(payload), "application/x-www-form-urlencoded", output.timeout_seconds, output.retries)
            return
        if output.format == "ecowitt":
            post_payload(output.url or "", ecowitt_form_body(full_state, self.config.ecowitt), "application/x-www-form-urlencoded", output.timeout_seconds, output.retries)
            return
        raise ValueError(f"Unsupported scheduled webhook format: {output.format}")

    def report_optional_output_failure(self, output_name: str, exc: Exception) -> None:
        message = f"Optional output {output_name} failed: {exc}"
        LOG.warning(message)
        try:
            self.mqtt.publish_error(message)
        except Exception:
            LOG.exception("Could not publish optional output failure to MQTT")


def scheduled_payload(state: dict[str, Any], schedule: ScheduledReadConfig) -> dict[str, Any]:
    payload = {
        "schedule": schedule.name,
        "observed_at": state.get("observed_at"),
    }
    for field in schedule.fields:
        payload[field] = state.get(field)
    return payload


def state_json(state: dict[str, Any]) -> str:
    return json.dumps(state, indent=2, sort_keys=True)


def _external_mqtt_publisher(config: ExternalMqttConfig) -> MqttPublisher:
    return MqttPublisher(
        MqttConfig(
            host=config.host,
            port=config.port,
            username=config.username,
            password=config.password,
            discovery_prefix="",
            base_topic=config.topic,
            client_id=config.client_id,
        )
    )
