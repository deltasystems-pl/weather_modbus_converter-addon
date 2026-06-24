# WS90LP Modbus Bridge Documentation

## Overview

WS90LP Modbus Bridge is a Home Assistant add-on for WS90LP/WN90LP wired weather stations. It reads live Modbus registers from the weather station, decodes the raw values, calculates derived weather metrics, and publishes Home Assistant MQTT discovery/state from one supervised add-on.

It can also publish the same weather snapshot to an external MQTT broker in `json`, `data_string`, or `ecowitt` format.

The add-on also exposes a Home Assistant MQTT button named **Install Dashboard**. Pressing it creates a YAML dashboard with built-in Home Assistant cards and can show it in the Home Assistant sidebar as **Pogoda** by default.

## Data Flow

```text
WS90LP station
  -> RS485-to-Ethernet adapter
  -> WS90LP Modbus Bridge add-on
  -> Home Assistant MQTT discovery/state
  -> optional external MQTT broker
```

Use only one Modbus master for the station. If this add-on is running, disable any native Home Assistant `modbus:` config or other bridge that polls the same station.

## Hardware Settings

Known working Waveshare RS485 TO ETH (B) setup:

```yaml
protocol_mode: modbus_tcp_gateway
live_read_mode: block
host: 192.168.88.201
port: 502
unit_id: 144
```

Use `live_read_mode: single` only if the adapter cannot reliably return the full live register block.

## Home Assistant MQTT Output

The add-on publishes Home Assistant MQTT discovery so entities are created automatically.

Default topics:

```text
homeassistant/device/ws90lp_bridge/config
ws90lp_bridge/ws90lp/state
ws90lp_bridge/ws90lp/status
ws90lp_bridge/ws90lp/error
```

Expected entities include:

- Temperature
- Humidity
- Pressure
- Sea Level Pressure
- Illuminance
- UV Index
- Wind Speed
- Wind Gust
- Wind Direction
- Wind Direction Compass
- Solar Radiation
- Dew Point
- Wind Chill
- Feels Like
- Sun Feels Like
- Rain Total
- Rain Counter
- Rain Delta
- Rain Rate
- Rain Event
- Rain Hour
- Rain Last 24 Hours
- Rain Day
- Rain Week
- Rain Month
- Rain Year
- Rain State
- Rain Level
- Install Dashboard
- Dashboard Setup Status

## Automatic Dashboard

The add-on can create a Home Assistant YAML dashboard for the weather station. It uses only built-in cards, so there are no HACS cards or frontend resources to install.

Default dashboard behavior:

- Sidebar title: `Pogoda`
- Dashboard URL path: `pogoda-ws90lp`
- Icon: `mdi:weather-partly-cloudy`
- Dashboard YAML file: `/homeassistant/dashboards/ws90lp-weather.yaml`

To install or refresh the dashboard:

1. Start the add-on and wait for the WS90LP MQTT device to appear.
2. Open the WS90LP Weather Station device in Home Assistant.
3. Press **Install Dashboard**.
4. Check **Dashboard Setup Status** for the result.
5. Restart Home Assistant if the sidebar entry does not appear immediately.

The installer writes a backup before changing `configuration.yaml`:

```text
/homeassistant/configuration.yaml.ws90lp-backup-YYYYMMDD-HHMMSS
```

Dashboard options:

```yaml
dashboard:
  config_dir: /homeassistant
  title: Pogoda
  icon: mdi:weather-partly-cloudy
  url_path: pogoda-ws90lp
  show_in_sidebar: true
```

`title` controls the Home Assistant sidebar label. `url_path` is the internal dashboard key and should contain a hyphen, for example `pogoda-ws90lp` or `weather-station`.

If your existing `lovelace:` YAML uses `!include` for the dashboard map, the add-on writes the dashboard file but reports that `configuration.yaml` needs a manual Lovelace merge. This avoids corrupting a custom Lovelace setup.

## External MQTT Output

Enable `external_mqtt` when another system should receive a custom payload while Home Assistant still receives normal MQTT discovery/state.

```yaml
external_mqtt:
  enabled: true
  host: example-broker.local
  port: 1883
  username: ""
  password: ""
  client_id: ws90lp_bridge_external
  topic: okrweather/ws90-gw2000a-02
  payload_format: data_string
  interval_seconds: 60
  retain: false
```

Supported `payload_format` values:

- `data_string`: ESPHome-compatible comma-separated `key=value` payload.
- `json`: compact JSON state payload.
- `ecowitt`: Ecowitt/GW2000-style URL-form payload.

`data_string` example:

```text
temperature_c=10.5,humidity_pct=55,pressure_hpa=1013.2,pressure_sea_level_hpa=1036.4,illuminance_lx=1230,uv_index=3.7,wind_speed_ms=2.5,wind_gust_ms=4.8,wind_direction_deg=270,rain_total_mm=123.4,rain_counter_mm=123.45,rain_rate_mm_h=0.00,rain_event_mm=0.00,rain_hour_mm=0.00,rain_last24h_mm=0.00,rain_day_mm=0.00,rain_week_mm=0.00,rain_month_mm=0.00,rain_year_mm=0.00,rain_state=false,rain_level=No Rain | IMGW None
```

## Configuration Reference

`protocol_mode`

- `modbus_tcp_gateway`: use for the Waveshare RS485 TO ETH (B).
- `rtu_over_tcp`: use only for transparent RTU-over-TCP adapters.

`live_read_mode`

- `block`: one efficient read of the live register block.
- `single`: read each live register separately.

`host`

- IP address or DNS name of the RS485-to-Ethernet adapter.

`unit_id`

- Default WS90LP unit id is `144`.

`station_elevation_m`

- Used to calculate sea-level pressure from station pressure.

`mqtt`

- Home Assistant MQTT broker settings.
- For Mosquitto add-on inside Home Assistant, `host: core-mosquitto` is normally correct.

`external_mqtt`

- Optional second MQTT output for another system.
- Uses its own broker host, credentials, topic, payload format, and interval.

`dashboard`

- Controls the generated Home Assistant dashboard.
- `title` is the sidebar/menu label.
- `icon` is the sidebar icon.
- `url_path` is the internal Lovelace dashboard key.
- `show_in_sidebar` controls whether Home Assistant shows the dashboard in the sidebar.

## Troubleshooting

### No response received after 0 retries

For the Waveshare RS485 TO ETH (B), verify:

```yaml
protocol_mode: modbus_tcp_gateway
host: 192.168.88.201
port: 502
unit_id: 144
```

Also disable any other Modbus master polling the same adapter.

### Values appear in add-on logs but entities do not appear

Check:

- Mosquitto broker is running.
- MQTT integration is configured in Home Assistant.
- `mqtt.discovery_prefix` is `homeassistant`.
- The add-on log does not show MQTT authentication errors.

### External MQTT does not receive data

Check:

- `external_mqtt.enabled` is `true`.
- Broker host, port, username, and password are correct.
- Topic matches the consumer expectation.
- `payload_format` matches the consumer parser.

### Install Dashboard button does not create a sidebar entry

Check:

- The add-on is updated to version `0.1.3` or newer.
- `Dashboard Setup Status` says the dashboard was installed.
- Home Assistant was restarted after the button was pressed.
- Your `configuration.yaml` does not use an included `lovelace.dashboards` map that needs manual merging.

### Rain values reset after first start

The bridge has to baseline the hardware rain counter on first successful read. Period totals start from that baseline and then accumulate local deltas.

## Security

Do not publish real MQTT passwords, Home Assistant tokens, or SSH passwords in issues or screenshots. The add-on stores credentials in Home Assistant add-on options.
