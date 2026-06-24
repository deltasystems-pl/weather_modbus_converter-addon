# WS90LP Modbus Bridge Add-on

[![Open your Home Assistant instance and show the add-on store with this repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_store.svg)](https://my.home-assistant.io/redirect/supervisor_store/?repository_url=https%3A%2F%2Fgithub.com%2Fdeltasystems-pl%2Fweather_modbus_converter-addon)

Home Assistant add-on repository URL:

```text
https://github.com/deltasystems-pl/weather_modbus_converter-addon
```

This repository contains the **WS90LP Modbus Bridge** Home Assistant add-on.

The add-on runs one supervised service that owns the full path:

```text
WS90LP RS485 Modbus -> bridge add-on -> Home Assistant MQTT entities
                                  -> optional external MQTT payload
```

It polls a WS90LP/WN90LP weather station through an RS485-to-Ethernet adapter, decodes live Modbus registers, calculates derived weather/rain values, publishes Home Assistant MQTT discovery/state, and can also send an ESPHome-compatible `data_string` payload to an external MQTT broker.

## Install

1. Open Home Assistant.
2. Go to **Settings -> Add-ons -> Add-on Store**.
3. Open the three-dot menu and choose **Repositories**.
4. Add:

```text
https://github.com/deltasystems-pl/weather_modbus_converter-addon
```

5. Install **WS90LP Modbus Bridge**.

## Example Configuration

```yaml
protocol_mode: modbus_tcp_gateway
live_read_mode: block
host: 192.168.88.201
port: 502
unit_id: 144
poll_interval_seconds: 10
timeout_seconds: 3
failure_threshold: 3
log_level: INFO
station_elevation_m: 188.0

mqtt:
  host: core-mosquitto
  port: 1883
  username: ""
  password: ""
  discovery_prefix: homeassistant
  base_topic: ws90lp_bridge/ws90lp
  client_id: ws90lp_bridge

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

For the Waveshare RS485 TO ETH (B), use `protocol_mode: modbus_tcp_gateway`.
