ARG BUILD_VERSION
ARG BUILD_ARCH

FROM ghcr.io/home-assistant/base:3.23

WORKDIR /app

RUN apk add --no-cache py3-pip python3

COPY requirements.txt pyproject.toml README.md /app/
COPY ws90lp_bridge /app/ws90lp_bridge
RUN pip install --break-system-packages --no-cache-dir .

COPY run.sh /run.sh
RUN chmod a+x /run.sh

LABEL \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="app" \
  io.hass.arch="${BUILD_ARCH}" \
  org.opencontainers.image.title="Home Assistant App: WS90LP Modbus Bridge" \
  org.opencontainers.image.description="Poll a WS90LP weather station over Modbus and publish Home Assistant MQTT plus external MQTT payloads." \
  org.opencontainers.image.source="https://github.com/deltasystems-pl/weather_modbus_converter-addon"

CMD ["/run.sh"]
