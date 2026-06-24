# Changelog

## 0.1.3

- Added a Home Assistant MQTT button entity named **Install Dashboard**.
- Added automatic YAML dashboard generation using built-in Home Assistant cards.
- Added configurable dashboard options: title, icon, URL path, and sidebar visibility.
- Defaults the generated sidebar dashboard title to **Pogoda**.
- Added a diagnostic setup-status sensor for dashboard installation feedback.

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
