from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from .config import DashboardConfig

DASHBOARD_FILENAME = "dashboards/ws90lp-weather.yaml"
MARKER_BEGIN = "# BEGIN WS90LP BRIDGE DASHBOARD"
MARKER_END = "# END WS90LP BRIDGE DASHBOARD"


@dataclass
class DashboardInstallResult:
    ok: bool
    message: str
    dashboard_path: str | None = None
    backup_path: str | None = None
    restart_required: bool = True


def install_dashboard(
    dashboard: DashboardConfig | None = None,
    supervisor_token: str | None = None,
) -> DashboardInstallResult:
    dashboard = dashboard or DashboardConfig()
    root = Path(dashboard.config_dir)
    configuration = root / "configuration.yaml"
    if not configuration.exists():
        return DashboardInstallResult(False, f"configuration.yaml not found in {root}")

    dashboard_file = root / DASHBOARD_FILENAME
    dashboard_file.parent.mkdir(parents=True, exist_ok=True)
    dashboard_file.write_text(_dashboard_yaml(dashboard), encoding="utf-8")

    config_text = configuration.read_text(encoding="utf-8")
    try:
        updated_config, backup_needed = _ensure_lovelace_dashboard(config_text, dashboard)
    except ValueError as exc:
        return DashboardInstallResult(
            False,
            f"Dashboard YAML written, but configuration.yaml needs manual Lovelace merge: {exc}",
            dashboard_path=str(dashboard_file),
        )
    if updated_config == config_text:
        backup_needed = False

    backup_path = None
    if backup_needed:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        backup = configuration.with_name(f"configuration.yaml.ws90lp-backup-{stamp}")
        backup.write_text(config_text, encoding="utf-8")
        configuration.write_text(updated_config, encoding="utf-8")
        backup_path = str(backup)

    reload_message = _reload_homeassistant(supervisor_token)
    message = (
        f"Dashboard '{dashboard.title}' installed using built-in cards; "
        "no external Lovelace resources are required."
    )
    if reload_message:
        message = f"{message} {reload_message}"
    return DashboardInstallResult(
        True,
        message,
        dashboard_path=str(dashboard_file),
        backup_path=backup_path,
        restart_required=True,
    )


def _reload_homeassistant(supervisor_token: str | None) -> str:
    if not supervisor_token:
        return "Restart Home Assistant if the dashboard does not appear."
    headers = {"Authorization": f"Bearer {supervisor_token}", "Content-Type": "application/json"}
    try:
        requests.post(
            "http://supervisor/core/api/services/homeassistant/reload_core_config",
            headers=headers,
            json={},
            timeout=10,
        ).raise_for_status()
    except requests.RequestException:
        return "Restart Home Assistant if the dashboard does not appear."
    return "Core config reload requested; restart Home Assistant if the dashboard does not appear."


def _ensure_lovelace_dashboard(config_text: str, dashboard: DashboardConfig) -> tuple[str, bool]:
    managed = _managed_block(dashboard)
    if MARKER_BEGIN in config_text and MARKER_END in config_text:
        before, rest = config_text.split(MARKER_BEGIN, 1)
        _old, after = rest.split(MARKER_END, 1)
        return before.rstrip() + "\n\n" + managed + "\n" + after.lstrip("\n"), True

    lines = config_text.splitlines()
    lovelace_idx = _top_level_key(lines, "lovelace")
    if lovelace_idx is None:
        separator = "\n" if config_text.endswith("\n") else "\n\n"
        return config_text + separator + managed + "\n", True
    if lines[lovelace_idx].strip() != "lovelace:":
        raise ValueError("existing lovelace uses an include or inline value")

    lovelace_end = _section_end(lines, lovelace_idx)
    lovelace_lines = lines[lovelace_idx + 1 : lovelace_end]
    dashboards_rel = _nested_key(lovelace_lines, "dashboards", indent=2)
    if dashboards_rel is None:
        insert = _dashboard_entry_block(dashboard, indent=2, include_dashboards_key=True).splitlines()
        updated = lines[:lovelace_end] + insert + lines[lovelace_end:]
        return "\n".join(updated) + ("\n" if config_text.endswith("\n") else ""), True

    dashboards_idx = lovelace_idx + 1 + dashboards_rel
    dashboards_line = lines[dashboards_idx]
    if dashboards_line.strip() != "dashboards:":
        raise ValueError("existing lovelace.dashboards uses an include or inline value")

    dashboards_end = _section_end(lines, dashboards_idx)
    existing_rel = _nested_key(lines[dashboards_idx + 1 : dashboards_end], dashboard.url_path, indent=4)
    entry = _dashboard_entry_block(dashboard, indent=4, include_dashboards_key=False).splitlines()
    if existing_rel is None:
        updated = lines[:dashboards_end] + entry + lines[dashboards_end:]
        return "\n".join(updated) + ("\n" if config_text.endswith("\n") else ""), True

    existing_idx = dashboards_idx + 1 + existing_rel
    existing_end = _section_end(lines, existing_idx)
    updated = lines[:existing_idx] + entry + lines[existing_end:]
    return "\n".join(updated) + ("\n" if config_text.endswith("\n") else ""), True


def _top_level_key(lines: list[str], key: str) -> int | None:
    needle = f"{key}:"
    for idx, line in enumerate(lines):
        if line.startswith(needle):
            return idx
    return None


def _nested_key(lines: list[str], key: str, indent: int) -> int | None:
    needle = " " * indent + f"{key}:"
    for idx, line in enumerate(lines):
        if line.startswith(needle):
            return idx
    return None


def _section_end(lines: list[str], start_idx: int) -> int:
    start_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip(" "))
    for idx in range(start_idx + 1, len(lines)):
        line = lines[idx]
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent <= start_indent:
            return idx
    return len(lines)


def _managed_block(dashboard: DashboardConfig) -> str:
    return (
        f"{MARKER_BEGIN}\n"
        "lovelace:\n"
        f"{_dashboard_entry_block(dashboard, indent=2, include_dashboards_key=True)}\n"
        f"{MARKER_END}"
    )


def _dashboard_entry_block(dashboard: DashboardConfig, indent: int, include_dashboards_key: bool) -> str:
    base = " " * indent
    child = " " * (indent + 2)
    grandchild = " " * (indent + 4)
    lines = []
    if include_dashboards_key:
        lines.append(f"{base}dashboards:")
        lines.append(f"{child}{dashboard.url_path}:")
        lines.extend(_dashboard_entry_lines(dashboard, grandchild))
    else:
        lines.append(f"{base}{dashboard.url_path}:")
        lines.extend(_dashboard_entry_lines(dashboard, child))
    return "\n".join(lines)


def _dashboard_entry_lines(dashboard: DashboardConfig, indent: str) -> list[str]:
    return [
        f"{indent}mode: yaml",
        f"{indent}filename: {DASHBOARD_FILENAME}",
        f"{indent}title: {_yaml_scalar(dashboard.title)}",
        f"{indent}icon: {_yaml_scalar(dashboard.icon)}",
        f"{indent}show_in_sidebar: {str(dashboard.show_in_sidebar).lower()}",
    ]


def _yaml_scalar(value: str) -> str:
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _dashboard_yaml(dashboard: DashboardConfig) -> str:
    return f"""title: {_yaml_scalar(dashboard.title)}
views:
  - title: Weather Station
    path: ws90lp-weather
    icon: {_yaml_scalar(dashboard.icon)}
    cards:
      - type: glance
        title: Live Conditions
        columns: 4
        entities:
          - entity: sensor.ws90lp_temperature
            name: Temperature
          - entity: sensor.ws90lp_humidity
            name: Humidity
          - entity: sensor.ws90lp_pressure
            name: Pressure
          - entity: sensor.ws90lp_sea_level_pressure
            name: Sea Pressure
          - entity: sensor.ws90lp_wind_speed
            name: Wind
          - entity: sensor.ws90lp_wind_gust
            name: Gust
          - entity: sensor.ws90lp_wind_direction
            name: Direction
          - entity: sensor.ws90lp_rain_rate
            name: Rain Rate

      - type: grid
        title: Environment
        columns: 3
        square: false
        cards:
          - type: sensor
            entity: sensor.ws90lp_temperature
            name: Temperature
            graph: line
            hours_to_show: 48
          - type: sensor
            entity: sensor.ws90lp_humidity
            name: Humidity
            graph: line
            hours_to_show: 48
          - type: sensor
            entity: sensor.ws90lp_sea_level_pressure
            name: Sea Level Pressure
            graph: line
            hours_to_show: 48

      - type: grid
        title: Wind
        columns: 3
        square: false
        cards:
          - type: gauge
            entity: sensor.ws90lp_wind_direction
            name: Direction
            min: 0
            max: 360
            needle: true
          - type: entity
            entity: sensor.ws90lp_wind_direction_compass
            name: Compass
          - type: gauge
            entity: sensor.ws90lp_wind_speed
            name: Wind Speed
            min: 0
            max: 30
            needle: true
            severity:
              green: 0
              yellow: 8
              red: 17
          - type: gauge
            entity: sensor.ws90lp_wind_gust
            name: Wind Gust
            min: 0
            max: 40
            needle: true
            severity:
              green: 0
              yellow: 10
              red: 22

      - type: grid
        title: Sun and UV
        columns: 3
        square: false
        cards:
          - type: gauge
            entity: sensor.ws90lp_uv_index
            name: UV Index
            min: 0
            max: 12
            needle: true
            severity:
              green: 0
              yellow: 3
              red: 8
          - type: sensor
            entity: sensor.ws90lp_illuminance
            name: Illuminance
            graph: line
            hours_to_show: 24
          - type: sensor
            entity: sensor.ws90lp_solar_radiation
            name: Solar Radiation
            graph: line
            hours_to_show: 24

      - type: grid
        title: Rain
        columns: 3
        square: false
        cards:
          - type: entity
            entity: binary_sensor.ws90lp_rain_state
            name: Rain State
          - type: sensor
            entity: sensor.ws90lp_rain_rate
            name: Rain Rate
            graph: line
            hours_to_show: 24
          - type: entity
            entity: sensor.ws90lp_rain_level
            name: Rain Level
          - type: entity
            entity: sensor.ws90lp_rain_day
            name: Rain Day
          - type: entity
            entity: sensor.ws90lp_rain_month
            name: Rain Month
          - type: entity
            entity: sensor.ws90lp_rain_total
            name: Rain Total

      - type: history-graph
        title: Weather Trends
        hours_to_show: 72
        entities:
          - entity: sensor.ws90lp_temperature
            name: Temperature
          - entity: sensor.ws90lp_feels_like
            name: Feels Like
          - entity: sensor.ws90lp_humidity
            name: Humidity
          - entity: sensor.ws90lp_sea_level_pressure
            name: Sea Pressure
          - entity: sensor.ws90lp_wind_speed
            name: Wind
          - entity: sensor.ws90lp_rain_rate
            name: Rain Rate
"""


def result_state(result: DashboardInstallResult) -> dict[str, Any]:
    return {
        "ok": result.ok,
        "message": result.message,
        "dashboard_path": result.dashboard_path,
        "backup_path": result.backup_path,
        "restart_required": result.restart_required,
    }
