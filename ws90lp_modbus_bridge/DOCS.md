# WS90LP Modbus Bridge Documentation

## Overview

WS90LP Modbus Bridge is a Home Assistant add-on for WS90LP/WN90LP wired weather stations. It reads live Modbus registers from the weather station, decodes the raw values, calculates derived weather metrics, and publishes Home Assistant MQTT discovery/state from one supervised add-on.

It can also publish the same weather snapshot to an external MQTT broker in `json`, `data_string`, or `ecowitt` format.

The add-on includes a Home Assistant ingress page titled **Pogoda**. Enable **Show in sidebar** on the add-on info page to open a dedicated weather analysis app without installing Lovelace resources.

## Data Flow

```text
WS90LP station
  -> RS485-to-Ethernet adapter
  -> WS90LP Modbus Bridge add-on
  -> Home Assistant MQTT discovery/state
  -> Home Assistant sidebar app
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

## Sidebar Weather App

The add-on supports Home Assistant ingress, similar to Node-RED.

To enable it:

1. Open **Settings -> Add-ons**.
2. Open **WS90LP Modbus Bridge**.
3. Open the **Info** tab.
4. Enable **Show in sidebar**.
5. Open **Pogoda** from the Home Assistant sidebar.

The app is served by the same add-on process that polls Modbus and publishes MQTT. It does not write `configuration.yaml`, does not install dashboard YAML, and does not require HACS cards.

The page visualizes:

- current station readings and derived comfort values
- wind direction, speed, gust, and wind level
- rain state, rain rate, event/hour/day/week/month/year totals
- sun, UV, illuminance, solar radiation, and sun-adjusted feels-like temperature
- station pressure, sea-level pressure, and pressure trend
- rolling in-memory charts from recent successful reads
- raw decoded bridge state for troubleshooting

Configuration:

```yaml
web_ui:
  enabled: true
  host: 0.0.0.0
  port: 8099
  title: Pogoda
  history_limit: 720
```

The Home Assistant add-on manifest uses `ingress_port: 8099`, so keep `web_ui.port` at `8099` unless you are running the bridge outside the add-on.

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

`web_ui`

- Built-in Home Assistant ingress weather analysis page.
- `title` controls the page title.
- `history_limit` controls how many successful readings are kept in memory for trend charts.

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

### Pogoda sidebar page does not appear

Check:

- The add-on is updated to version `0.1.4` or newer.
- The add-on is started.
- **Show in sidebar** is enabled on the add-on info page.
- `web_ui.enabled` is `true`.
- `web_ui.port` is still `8099`.

### Rain values reset after first start

The bridge has to baseline the hardware rain counter on first successful read. Period totals start from that baseline and then accumulate local deltas.

## Security

Do not publish real MQTT passwords, Home Assistant tokens, or SSH passwords in issues or screenshots. The add-on stores credentials in Home Assistant add-on options.
