# Changelog

## 0.1.5

- Added `web_ui.language` with `pl` and `en` choices.
- Added a fully Polish ingress page for the weather analysis app.
- Added explicit `/pl` and `/en` language routes.
- Translated dynamic condition labels for comfort, wind, rain, UV, radiation, and pressure levels.

## 0.1.4

- Removed the automatic dashboard installer button from MQTT discovery.
- Removed dashboard setup status reporting and generated dashboard configuration.
- Removed Home Assistant Core API and configuration-directory write permissions from the add-on.
- Added a Home Assistant ingress app with `panel_title: Pogoda` and `panel_icon: mdi:weather-partly-cloudy`.
- Added a built-in weather analysis page for current conditions, wind, rain, sun/UV, pressure, trend charts, and raw diagnostics.

## 0.1.2

- Added Home Assistant add-on `icon.png` and `logo.png`.
- Added full add-on documentation in `DOCS.md`.
- Improved the repository and add-on README pages.
- Documented the recommended Waveshare RS485 TO ETH (B) configuration.

## 0.1.1

- Defaulted the add-on to `modbus_tcp_gateway` for the Waveshare RS485 TO ETH (B).
- Exposed `live_read_mode` in the Home Assistant add-on options.
- Added `block` and `single` live-read modes to the add-on schema.

## 0.1.0

- Initial public Home Assistant add-on repository.
- Added Modbus polling, Home Assistant MQTT discovery/state, derived weather values, rain accumulation, and external MQTT output.
