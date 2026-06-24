from __future__ import annotations

import html
import json
import logging
import threading
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from .config import WebUiConfig

LOG = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = ("en", "pl")

TEXT: dict[str, dict[str, str]] = {
    "en": {
        "html_lang": "en",
        "observed_waiting": "Waiting for the first WS90LP reading",
        "status_starting": "Starting",
        "status_loading": "Bridge service is loading",
        "tab_overview": "Overview",
        "tab_wind": "Wind",
        "tab_rain": "Rain",
        "tab_sun": "Sun",
        "tab_raw": "Raw Data",
        "weather_analysis": "Weather Analysis",
        "comfort": "Comfort",
        "wind_direction": "Wind Direction",
        "wind_trend": "Wind Trend",
        "rain_periods": "Rain Periods",
        "rain_rate_trend": "Rain Rate Trend",
        "sun_uv": "Sun And UV",
        "radiation_trend": "Radiation Trend",
        "raw_state": "Raw Bridge State",
        "temperature_trend": "Temperature Trend",
        "pressure_trend": "Pressure Trend",
        "speed_and_gust": "Speed and gust",
        "intensity": "Intensity",
        "solar_radiation": "Solar radiation",
        "temperature_and_feels": "Temperature and feels like",
        "sea_level_pressure": "Sea level pressure",
        "field": "Field",
        "value": "Value",
        "status_online": "Online",
        "status_offline": "Offline",
        "samples_in_memory": "samples in memory",
        "last_reading": "Last reading",
        "current_microclimate": "Current microclimate",
        "temperature": "Temperature",
        "feels_like": "feels like",
        "humidity": "humidity",
        "pressure": "Pressure",
        "unknown": "Unknown",
        "gust": "gust",
        "from": "from",
        "no_reading": "No reading",
        "active": "active",
        "not_active": "not active",
        "collecting_trend": "Collecting trend",
        "stable": "Stable",
        "rising": "Rising",
        "falling": "Falling",
        "to": "to",
        "waiting_more_samples": "Waiting for more samples",
        "ui_error": "UI error",
        "sun_adjusted": "Sun adjusted",
        "metric_temperature": "Temperature",
        "metric_feels_like": "Feels Like",
        "metric_humidity": "Humidity",
        "metric_sea_pressure": "Sea Pressure",
        "metric_wind": "Wind",
        "metric_rain_rate": "Rain Rate",
        "station_pressure": "Station pressure",
        "uv_level": "UV level",
        "rain_level": "Rain level",
        "modbus_state": "Modbus state",
        "problem": "Problem",
        "ok": "OK",
        "temperature_level": "Temperature level",
        "humidity_level": "Humidity level",
        "dew_point": "Dew point",
        "wind_chill": "Wind chill",
        "direction": "Direction",
        "degrees": "Degrees",
        "speed": "Speed",
        "level": "Level",
        "raining": "Raining",
        "yes": "Yes",
        "no": "No",
        "rate": "Rate",
        "event": "Event",
        "hour": "Hour",
        "last_24h": "Last 24h",
        "day": "Day",
        "week": "Week",
        "month": "Month",
        "year": "Year",
        "total": "Total",
        "uv_index": "UV index",
        "illuminance": "Illuminance",
        "radiation_level": "Radiation level",
        "sun_feels_like": "Sun feels like",
        "wind_speed_trend": "Wind speed trend",
        "rain_rate_trend_label": "Rain rate trend",
        "solar_radiation_trend": "Solar radiation trend",
        "temperature_trend_label": "Temperature trend",
        "pressure_trend_label": "Pressure trend",
    },
    "pl": {
        "html_lang": "pl",
        "observed_waiting": "Oczekiwanie na pierwszy odczyt WS90LP",
        "status_starting": "Uruchamianie",
        "status_loading": "Usługa mostka się uruchamia",
        "tab_overview": "Przegląd",
        "tab_wind": "Wiatr",
        "tab_rain": "Deszcz",
        "tab_sun": "Słońce",
        "tab_raw": "Dane surowe",
        "weather_analysis": "Analiza pogody",
        "comfort": "Komfort",
        "wind_direction": "Kierunek wiatru",
        "wind_trend": "Trend wiatru",
        "rain_periods": "Okresy opadu",
        "rain_rate_trend": "Trend intensywności opadu",
        "sun_uv": "Słońce i UV",
        "radiation_trend": "Trend promieniowania",
        "raw_state": "Surowy stan mostka",
        "temperature_trend": "Trend temperatury",
        "pressure_trend": "Trend ciśnienia",
        "speed_and_gust": "Prędkość i porywy",
        "intensity": "Intensywność",
        "solar_radiation": "Promieniowanie słoneczne",
        "temperature_and_feels": "Temperatura i odczuwalna",
        "sea_level_pressure": "Ciśnienie n.p.m.",
        "field": "Pole",
        "value": "Wartość",
        "status_online": "Online",
        "status_offline": "Offline",
        "samples_in_memory": "próbek w pamięci",
        "last_reading": "Ostatni odczyt",
        "current_microclimate": "Aktualny mikroklimat",
        "temperature": "Temperatura",
        "feels_like": "odczuwalna",
        "humidity": "wilgotność",
        "pressure": "Ciśnienie",
        "unknown": "Brak danych",
        "gust": "poryw",
        "from": "z kierunku",
        "no_reading": "Brak odczytu",
        "active": "aktywny",
        "not_active": "nieaktywny",
        "collecting_trend": "Zbieranie trendu",
        "stable": "Stabilnie",
        "rising": "Rośnie",
        "falling": "Spada",
        "to": "do",
        "waiting_more_samples": "Oczekiwanie na więcej próbek",
        "ui_error": "Błąd interfejsu",
        "sun_adjusted": "W słońcu",
        "metric_temperature": "Temperatura",
        "metric_feels_like": "Odczuwalna",
        "metric_humidity": "Wilgotność",
        "metric_sea_pressure": "Ciśnienie n.p.m.",
        "metric_wind": "Wiatr",
        "metric_rain_rate": "Opad",
        "station_pressure": "Ciśnienie lokalne",
        "uv_level": "Poziom UV",
        "rain_level": "Poziom opadu",
        "modbus_state": "Stan Modbus",
        "problem": "Problem",
        "ok": "OK",
        "temperature_level": "Poziom temperatury",
        "humidity_level": "Poziom wilgotności",
        "dew_point": "Punkt rosy",
        "wind_chill": "Chłód wiatru",
        "direction": "Kierunek",
        "degrees": "Stopnie",
        "speed": "Prędkość",
        "level": "Poziom",
        "raining": "Pada",
        "yes": "Tak",
        "no": "Nie",
        "rate": "Intensywność",
        "event": "Zdarzenie",
        "hour": "Godzina",
        "last_24h": "Ostatnie 24 h",
        "day": "Dzień",
        "week": "Tydzień",
        "month": "Miesiąc",
        "year": "Rok",
        "total": "Suma",
        "uv_index": "Indeks UV",
        "illuminance": "Natężenie światła",
        "radiation_level": "Poziom promieniowania",
        "sun_feels_like": "Odczuwalna w słońcu",
        "wind_speed_trend": "Trend prędkości wiatru",
        "rain_rate_trend_label": "Trend intensywności opadu",
        "solar_radiation_trend": "Trend promieniowania słonecznego",
        "temperature_trend_label": "Trend temperatury",
        "pressure_trend_label": "Trend ciśnienia",
    },
}

VALUE_LABELS: dict[str, dict[str, str]] = {
    "pl": {
        "Moderate": "Umiarkowany",
        "Low": "Niski",
        "High": "Wysoki",
        "Very High": "Bardzo wysoki",
        "Extreme": "Ekstremalny",
        "Overcast": "Pochmurno",
        "Dim": "Słabo",
        "Bright": "Jasno",
        "Very Bright": "Bardzo jasno",
        "Freezing": "Mróz",
        "Cold": "Zimno",
        "Cool": "Chłodno",
        "Comfortable": "Komfortowo",
        "Warm": "Ciepło",
        "Hot": "Gorąco",
        "Very Hot": "Bardzo gorąco",
        "Dry": "Sucho",
        "Humid": "Wilgotno",
        "Very Humid": "Bardzo wilgotno",
        "Calm": "Cisza",
        "Light": "Słaby",
        "Breezy": "Wietrznie",
        "Windy": "Silny wiatr",
        "Gale": "Wichura",
        "No Rain | IMGW None": "Bez deszczu | IMGW brak",
        "Light Rain | IMGW None": "Lekki deszcz | IMGW brak",
        "Moderate Rain | IMGW None": "Umiarkowany deszcz | IMGW brak",
        "Heavy Rain | IMGW None": "Silny deszcz | IMGW brak",
        "Violent Rain | IMGW None": "Gwałtowny deszcz | IMGW brak",
    }
}


class WeatherUiStore:
    def __init__(self, title: str = "Pogoda", history_limit: int = 720) -> None:
        self.title = title
        self._lock = threading.Lock()
        self._state: dict[str, Any] | None = None
        self._history: deque[dict[str, Any]] = deque(maxlen=history_limit)
        self._last_error: str | None = None
        self._online = False

    def update_state(self, state: dict[str, Any]) -> None:
        snapshot = dict(state)
        with self._lock:
            self._state = snapshot
            self._history.append(snapshot)
            self._last_error = None
            self._online = bool(snapshot.get("modbus_ok", True))

    def record_failure(self, message: str) -> None:
        with self._lock:
            self._last_error = message
            self._online = False

    def set_online(self, online: bool) -> None:
        with self._lock:
            self._online = online

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "title": self.title,
                "online": self._online,
                "last_error": self._last_error,
                "state": dict(self._state or {}),
                "history": list(self._history),
            }


class WeatherDashboardServer:
    def __init__(self, config: WebUiConfig, store: WeatherUiStore) -> None:
        self.config = config
        self.store = store
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._server is not None:
            return
        handler = _handler(self.store, self.config.title, self.config.language)
        self._server = ThreadingHTTPServer((self.config.host, self.config.port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, name="ws90lp-web-ui", daemon=True)
        self._thread.start()
        LOG.info("Weather dashboard UI listening on %s:%s", self.config.host, self.config.port)

    def stop(self) -> None:
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._server = None
        self._thread = None


def _handler(store: WeatherUiStore, title: str, language: str) -> type[BaseHTTPRequestHandler]:
    default_language = normalize_language(language)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path.endswith("/api/state"):
                self._json(store.snapshot())
                return
            if parsed.path.endswith("/api/health"):
                self._json({"ok": True})
                return
            if "/api/" in parsed.path:
                self.send_error(404)
                return
            self._html(render_dashboard_html(title, request_language(parsed.path, default_language)))

        def log_message(self, fmt: str, *args: object) -> None:
            LOG.debug("Web UI request: " + fmt, *args)

        def _json(self, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _html(self, body: str) -> None:
            encoded = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    return Handler


def normalize_language(language: str) -> str:
    normalized = str(language or "pl").strip().lower()
    return normalized if normalized in SUPPORTED_LANGUAGES else "pl"


def request_language(path: str, default_language: str) -> str:
    parts = [part for part in path.split("/") if part]
    for part in reversed(parts):
        if part in SUPPORTED_LANGUAGES:
            return part
    return normalize_language(default_language)


def render_dashboard_html(title: str = "Pogoda", language: str = "pl") -> str:
    language = normalize_language(language)
    texts = TEXT[language]
    labels = json.dumps(texts, ensure_ascii=False, separators=(",", ":"))
    value_labels = json.dumps(VALUE_LABELS.get(language, {}), ensure_ascii=False, separators=(",", ":"))
    safe_title = html.escape(title)
    return f"""<!doctype html>
<html lang="{texts["html_lang"]}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>{safe_title}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: oklch(94% 0.025 150);
      --ink: oklch(18% 0.035 165);
      --muted: oklch(45% 0.030 165);
      --line: oklch(83% 0.025 155);
      --panel: oklch(97% 0.018 145);
      --panel-strong: oklch(99% 0.010 145);
      --green: oklch(44% 0.120 155);
      --blue: oklch(45% 0.125 240);
      --amber: oklch(53% 0.130 65);
      --red: oklch(47% 0.135 30);
      --shadow: 0 14px 34px color-mix(in oklch, var(--ink) 12%, transparent);
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      min-height: 100vh;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.70), rgba(255,255,255,0) 280px),
        var(--bg);
      color: var(--ink);
      font-family: "Aptos", "Segoe UI", system-ui, sans-serif;
      letter-spacing: 0;
    }}

    button, input, select {{ font: inherit; }}

    .shell {{
      width: min(1280px, 100%);
      margin: 0 auto;
      padding: max(18px, env(safe-area-inset-top)) max(14px, env(safe-area-inset-right)) max(18px, env(safe-area-inset-bottom)) max(14px, env(safe-area-inset-left));
    }}

    header {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      align-items: end;
      gap: 18px;
      margin-bottom: 18px;
    }}

    h1 {{
      margin: 0;
      font-size: 30px;
      line-height: 1.05;
      font-weight: 800;
    }}

    .subtitle {{
      color: var(--muted);
      margin-top: 7px;
      font-size: 14px;
    }}

    .status {{
      min-width: 160px;
      padding: 10px 12px;
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 8px;
      text-align: right;
    }}

    .status strong {{
      display: block;
      font-size: 13px;
    }}

    .status span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-top: 3px;
    }}

    .tabs {{
      display: flex;
      gap: 8px;
      overflow-x: auto;
      padding: 0 0 14px;
      margin-bottom: 10px;
    }}

    .tab {{
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.68);
      color: var(--ink);
      min-height: 38px;
      padding: 0 14px;
      border-radius: 8px;
      cursor: pointer;
      white-space: nowrap;
    }}

    .tab[aria-selected="true"] {{
      background: var(--ink);
      color: white;
      border-color: var(--ink);
    }}

    .view {{ display: none; }}
    .view.active {{ display: block; }}

    .grid {{
      display: grid;
      gap: 12px;
    }}

    .metrics {{
      grid-template-columns: repeat(6, minmax(0, 1fr));
      margin-bottom: 12px;
    }}

    .metric {{
      min-height: 118px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel-strong);
      padding: 14px;
      box-shadow: var(--shadow);
      overflow: hidden;
    }}

    .metric label {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0;
    }}

    .metric .value {{
      margin-top: 12px;
      font-size: 30px;
      line-height: 1;
      font-weight: 800;
      word-break: break-word;
    }}

    .metric small {{
      display: block;
      color: var(--muted);
      margin-top: 10px;
      font-size: 12px;
      line-height: 1.35;
    }}

    .columns {{
      grid-template-columns: 1.1fr 0.9fr;
      align-items: start;
    }}

    .panel {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      padding: 16px;
      box-shadow: var(--shadow);
      overflow: hidden;
    }}

    .panel h2 {{
      margin: 0 0 14px;
      font-size: 17px;
      line-height: 1.2;
    }}

    .focus {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(260px, 0.5fr);
      gap: 12px;
      margin-bottom: 12px;
    }}

    .focus-main {{
      min-height: 170px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background:
        linear-gradient(125deg, color-mix(in oklch, var(--green) 16%, transparent), transparent 55%),
        var(--panel-strong);
      padding: 18px;
      box-shadow: var(--shadow);
      display: grid;
      align-content: end;
    }}

    .focus-main label {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0;
    }}

    .focus-main strong {{
      display: block;
      margin-top: 8px;
      font-size: 44px;
      line-height: 1;
    }}

    .focus-main span {{
      color: var(--muted);
      margin-top: 10px;
      display: block;
    }}

    .signal-strip {{
      display: grid;
      gap: 8px;
    }}

    .signal {{
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 8px;
      min-height: 50px;
      padding: 10px 12px;
      display: grid;
      grid-template-columns: 84px minmax(0, 1fr);
      gap: 10px;
      align-items: center;
    }}

    .signal label {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0;
    }}

    .signal strong {{
      font-size: 15px;
      line-height: 1.25;
      word-break: break-word;
    }}

    .facts {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }}

    .fact {{
      border-top: 1px solid var(--line);
      padding-top: 10px;
      min-height: 58px;
    }}

    .fact label {{
      color: var(--muted);
      display: block;
      font-size: 12px;
      margin-bottom: 5px;
    }}

    .fact strong {{
      font-size: 18px;
      line-height: 1.2;
      word-break: break-word;
    }}

    .compass-wrap {{
      display: grid;
      grid-template-columns: 170px minmax(0, 1fr);
      gap: 16px;
      align-items: center;
    }}

    .compass {{
      width: 170px;
      aspect-ratio: 1;
      border: 1px solid var(--line);
      border-radius: 50%;
      background:
        radial-gradient(circle, #ffffff 0 34%, transparent 35%),
        conic-gradient(from 0deg, #d8e7ee, #f5f7ed, #f0dfc4, #d8e7ee);
      position: relative;
    }}

    .needle {{
      position: absolute;
      inset: 18px 78px;
      transform-origin: 50% 67px;
      background: var(--blue);
      clip-path: polygon(50% 0, 100% 72%, 50% 100%, 0 72%);
    }}

    .compass::after {{
      content: attr(data-label);
      position: absolute;
      inset: 58px 36px auto;
      text-align: center;
      font-weight: 800;
      font-size: 26px;
    }}

    .chart {{
      width: 100%;
      height: 190px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #ffffff;
      display: block;
    }}

    .chart-grid {{
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}

    .chart-title {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: baseline;
      margin-bottom: 8px;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0;
    }}

    .raw {{
      width: 100%;
      overflow-x: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #ffffff;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}

    th, td {{
      text-align: left;
      padding: 9px 10px;
      border-bottom: 1px solid #e5ece7;
      white-space: nowrap;
    }}

    th {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0;
    }}

    .empty {{
      border: 1px dashed var(--line);
      border-radius: 8px;
      padding: 18px;
      color: var(--muted);
      background: rgba(255,255,255,0.58);
    }}

    .accent-green {{ color: var(--green); }}
    .accent-blue {{ color: var(--blue); }}
    .accent-amber {{ color: var(--amber); }}
    .accent-red {{ color: var(--red); }}

    @media (max-width: 1020px) {{
      .metrics {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
      .focus {{ grid-template-columns: 1fr; }}
      .columns, .chart-grid {{ grid-template-columns: 1fr; }}
    }}

    @media (max-width: 680px) {{
      .shell {{ padding: 14px; }}
      header {{ grid-template-columns: 1fr; align-items: start; }}
      .status {{ text-align: left; width: 100%; }}
      .metrics {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .focus-main strong {{ font-size: 34px; }}
      .signal {{ grid-template-columns: 1fr; }}
      .metric .value {{ font-size: 24px; }}
      .facts {{ grid-template-columns: 1fr; }}
      .compass-wrap {{ grid-template-columns: 1fr; }}
      .compass {{ margin: 0 auto; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <header>
      <div>
        <h1>{safe_title}</h1>
        <div class="subtitle" id="observed">{texts["observed_waiting"]}</div>
      </div>
      <div class="status">
        <strong id="statusText">{texts["status_starting"]}</strong>
        <span id="statusDetail">{texts["status_loading"]}</span>
      </div>
    </header>

    <nav class="tabs" aria-label="Weather views">
      <button class="tab" data-view="overview" aria-selected="true">{texts["tab_overview"]}</button>
      <button class="tab" data-view="wind">{texts["tab_wind"]}</button>
      <button class="tab" data-view="rain">{texts["tab_rain"]}</button>
      <button class="tab" data-view="sun">{texts["tab_sun"]}</button>
      <button class="tab" data-view="raw">{texts["tab_raw"]}</button>
    </nav>

    <section class="focus" id="focus"></section>

    <section id="overview" class="view active">
      <div class="grid metrics" id="metrics"></div>
      <div class="grid columns">
        <section class="panel">
          <h2>{texts["weather_analysis"]}</h2>
          <div class="facts" id="analysisFacts"></div>
        </section>
        <section class="panel">
          <h2>{texts["comfort"]}</h2>
          <div class="facts" id="comfortFacts"></div>
        </section>
      </div>
    </section>

    <section id="wind" class="view">
      <div class="grid columns">
        <section class="panel">
          <h2>{texts["wind_direction"]}</h2>
          <div class="compass-wrap">
            <div class="compass" id="compass" data-label="--">
              <div class="needle" id="needle"></div>
            </div>
            <div class="facts" id="windFacts"></div>
          </div>
        </section>
        <section class="panel">
          <h2>{texts["wind_trend"]}</h2>
          <div class="chart-title"><span>{texts["speed_and_gust"]}</span><span id="windRange">--</span></div>
          <svg class="chart" id="windChart" role="img" aria-label="{texts["wind_speed_trend"]}"></svg>
        </section>
      </div>
    </section>

    <section id="rain" class="view">
      <div class="grid columns">
        <section class="panel">
          <h2>{texts["rain_periods"]}</h2>
          <div class="facts" id="rainFacts"></div>
        </section>
        <section class="panel">
          <h2>{texts["rain_rate_trend"]}</h2>
          <div class="chart-title"><span>{texts["intensity"]}</span><span id="rainRange">--</span></div>
          <svg class="chart" id="rainChart" role="img" aria-label="{texts["rain_rate_trend_label"]}"></svg>
        </section>
      </div>
    </section>

    <section id="sun" class="view">
      <div class="grid columns">
        <section class="panel">
          <h2>{texts["sun_uv"]}</h2>
          <div class="facts" id="sunFacts"></div>
        </section>
        <section class="panel">
          <h2>{texts["radiation_trend"]}</h2>
          <div class="chart-title"><span>{texts["solar_radiation"]}</span><span id="sunRange">--</span></div>
          <svg class="chart" id="sunChart" role="img" aria-label="{texts["solar_radiation_trend"]}"></svg>
        </section>
      </div>
    </section>

    <section id="raw" class="view">
      <section class="panel">
        <h2>{texts["raw_state"]}</h2>
        <div class="raw">
          <table>
            <thead><tr><th>{texts["field"]}</th><th>{texts["value"]}</th></tr></thead>
            <tbody id="rawRows"></tbody>
          </table>
        </div>
      </section>
    </section>

    <section class="grid chart-grid" style="margin-top:12px">
      <section class="panel">
        <h2>{texts["temperature_trend"]}</h2>
        <div class="chart-title"><span>{texts["temperature_and_feels"]}</span><span id="tempRange">--</span></div>
        <svg class="chart" id="tempChart" role="img" aria-label="{texts["temperature_trend_label"]}"></svg>
      </section>
      <section class="panel">
        <h2>{texts["pressure_trend"]}</h2>
        <div class="chart-title"><span>{texts["sea_level_pressure"]}</span><span id="pressureRange">--</span></div>
        <svg class="chart" id="pressureChart" role="img" aria-label="{texts["pressure_trend_label"]}"></svg>
      </section>
    </section>
  </main>

  <script>
    const i18n = {labels};
    const valueLabels = {value_labels};
    const state = {{ latest: null, history: [] }};
    const units = {{
      temperature_c: "°C",
      feels_like_c: "°C",
      sun_feels_like_c: "°C",
      dew_point_c: "°C",
      humidity_pct: "%",
      pressure_hpa: "hPa",
      pressure_sea_level_hpa: "hPa",
      wind_speed_ms: "m/s",
      wind_gust_ms: "m/s",
      wind_direction_deg: "°",
      rain_rate_mm_h: "mm/h",
      rain_day_mm: "mm",
      rain_week_mm: "mm",
      rain_month_mm: "mm",
      rain_year_mm: "mm",
      rain_total_mm: "mm",
      uv_index: "",
      illuminance_lx: "lx",
      solar_radiation_wm2: "W/m²"
    }};

    document.querySelectorAll(".tab").forEach((button) => {{
      button.addEventListener("click", () => {{
        document.querySelectorAll(".tab").forEach((item) => item.setAttribute("aria-selected", "false"));
        document.querySelectorAll(".view").forEach((item) => item.classList.remove("active"));
        button.setAttribute("aria-selected", "true");
        document.getElementById(button.dataset.view).classList.add("active");
      }});
    }});

    function formatValue(value, digits = 1) {{
      if (value === null || value === undefined || value === "") return "--";
      if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(digits);
      if (typeof value === "boolean") return value ? i18n.yes : i18n.no;
      return String(value);
    }}

    function translateValue(value) {{
      if (value === null || value === undefined || value === "") return value;
      return valueLabels[String(value)] || value;
    }}

    function metric(label, field, hint, accent = "") {{
      const value = state.latest ? state.latest[field] : null;
      const unit = units[field] ? " " + units[field] : "";
      return `<article class="metric ${{accent}}"><label>${{label}}</label><div class="value">${{formatValue(value)}}${{value == null ? "" : unit}}</div><small>${{translateValue(hint) || ""}}</small></article>`;
    }}

    function trend(field) {{
      const points = state.history.filter((row) => typeof row[field] === "number");
      if (points.length < 2) return null;
      return points[points.length - 1][field] - points[0][field];
    }}

    function describeTrend(field, unit, deadband = 0.1) {{
      const change = trend(field);
      if (change === null) return i18n.collecting_trend;
      if (Math.abs(change) <= deadband) return i18n.stable;
      return `${{change > 0 ? i18n.rising : i18n.falling}} ${{Math.abs(change).toFixed(1)}} ${{unit}}`;
    }}

    function fact(label, value, unit = "") {{
      const suffix = value == null || unit === "" ? "" : " " + unit;
      return `<div class="fact"><label>${{label}}</label><strong>${{formatValue(translateValue(value))}}${{suffix}}</strong></div>`;
    }}

    function setFacts(id, rows) {{
      document.getElementById(id).innerHTML = rows.join("");
    }}

    function updateText(payload) {{
      const latest = payload.state || {{}};
      state.latest = latest;
      state.history = payload.history || [];
      document.getElementById("statusText").textContent = payload.online ? i18n.status_online : i18n.status_offline;
      document.getElementById("statusDetail").textContent = payload.last_error || `${{state.history.length}} ${{i18n.samples_in_memory}}`;
      document.getElementById("observed").textContent = latest.observed_at ? `${{i18n.last_reading}}: ${{latest.observed_at}}` : i18n.observed_waiting;
      document.getElementById("focus").innerHTML = `
        <div class="focus-main">
          <label>${{i18n.current_microclimate}}</label>
          <strong>${{formatValue(latest.temperature_c)}}${{latest.temperature_c == null ? "" : " °C"}}</strong>
          <span>${{translateValue(latest.temperature_level) || i18n.temperature}} · ${{i18n.feels_like}} ${{formatValue(latest.feels_like_c)}} °C · ${{i18n.humidity}} ${{formatValue(latest.humidity_pct)}}%</span>
        </div>
        <div class="signal-strip">
          <div class="signal"><label>${{i18n.pressure}}</label><strong>${{translateValue(latest.pressure_level) || i18n.unknown}} · ${{describeTrend("pressure_sea_level_hpa", "hPa", 0.2)}}</strong></div>
          <div class="signal"><label>${{i18n.metric_wind}}</label><strong>${{translateValue(latest.wind_level) || i18n.unknown}} · ${{i18n.gust}} ${{formatValue(latest.wind_gust_ms)}} m/s ${{i18n.from}} ${{latest.wind_direction_compass || "--"}}</strong></div>
          <div class="signal"><label>${{i18n.tab_rain}}</label><strong>${{translateValue(latest.rain_level) || i18n.no_reading}} · ${{latest.rain_state ? i18n.active : i18n.not_active}}</strong></div>
        </div>
      `;

      document.getElementById("metrics").innerHTML = [
        metric(i18n.metric_temperature, "temperature_c", latest.temperature_level, "accent-green"),
        metric(i18n.metric_feels_like, "feels_like_c", i18n.sun_adjusted + ": " + formatValue(latest.sun_feels_like_c) + " °C", "accent-amber"),
        metric(i18n.metric_humidity, "humidity_pct", latest.humidity_level, "accent-blue"),
        metric(i18n.metric_sea_pressure, "pressure_sea_level_hpa", latest.pressure_level),
        metric(i18n.metric_wind, "wind_speed_ms", latest.wind_level),
        metric(i18n.metric_rain_rate, "rain_rate_mm_h", latest.rain_level, latest.rain_state ? "accent-red" : "")
      ].join("");

      setFacts("analysisFacts", [
        fact(i18n.station_pressure, latest.pressure_hpa, "hPa"),
        fact(i18n.sea_level_pressure, latest.pressure_sea_level_hpa, "hPa"),
        fact(i18n.solar_radiation, latest.solar_radiation_wm2, "W/m²"),
        fact(i18n.uv_level, latest.uv_level),
        fact(i18n.rain_level, latest.rain_level),
        fact(i18n.modbus_state, latest.modbus_ok === false ? i18n.problem : i18n.ok)
      ]);

      setFacts("comfortFacts", [
        fact(i18n.temperature_level, latest.temperature_level),
        fact(i18n.humidity_level, latest.humidity_level),
        fact(i18n.dew_point, latest.dew_point_c, "°C"),
        fact(i18n.wind_chill, latest.wind_chill_c, "°C")
      ]);

      setFacts("windFacts", [
        fact(i18n.direction, latest.wind_direction_compass),
        fact(i18n.degrees, latest.wind_direction_deg, "°"),
        fact(i18n.speed, latest.wind_speed_ms, "m/s"),
        fact(i18n.gust, latest.wind_gust_ms, "m/s"),
        fact(i18n.level, latest.wind_level)
      ]);
      document.getElementById("needle").style.transform = `rotate(${{Number(latest.wind_direction_deg || 0)}}deg)`;
      document.getElementById("compass").dataset.label = latest.wind_direction_compass || "--";

      setFacts("rainFacts", [
        fact(i18n.raining, latest.rain_state ? i18n.yes : i18n.no),
        fact(i18n.rate, latest.rain_rate_mm_h, "mm/h"),
        fact(i18n.event, latest.rain_event_mm, "mm"),
        fact(i18n.hour, latest.rain_hour_mm, "mm"),
        fact(i18n.last_24h, latest.rain_last24h_mm, "mm"),
        fact(i18n.day, latest.rain_day_mm, "mm"),
        fact(i18n.week, latest.rain_week_mm, "mm"),
        fact(i18n.month, latest.rain_month_mm, "mm"),
        fact(i18n.year, latest.rain_year_mm, "mm"),
        fact(i18n.total, latest.rain_total_mm, "mm")
      ]);

      setFacts("sunFacts", [
        fact(i18n.uv_index, latest.uv_index),
        fact(i18n.uv_level, latest.uv_level),
        fact(i18n.illuminance, latest.illuminance_lx, "lx"),
        fact(i18n.solar_radiation, latest.solar_radiation_wm2, "W/m²"),
        fact(i18n.radiation_level, latest.solar_radiation_level),
        fact(i18n.sun_feels_like, latest.sun_feels_like_c, "°C")
      ]);

      document.getElementById("rawRows").innerHTML = Object.keys(latest).sort().map((key) => (
        `<tr><td>${{key}}</td><td>${{formatValue(latest[key])}}</td></tr>`
      )).join("");
    }}

    function drawChart(svgId, rangeId, series) {{
      const svg = document.getElementById(svgId);
      svg.innerHTML = "";
      const width = svg.clientWidth || 600;
      const height = svg.clientHeight || 190;
      const pad = 18;
      const points = state.history || [];
      const values = [];
      series.forEach((item) => points.forEach((row) => {{
        const value = Number(row[item.field]);
        if (!Number.isNaN(value)) values.push(value);
      }}));
      if (points.length < 2 || values.length < 2) {{
        svg.innerHTML = `<text x="18" y="96" fill="#586760">${{i18n.waiting_more_samples}}</text>`;
        document.getElementById(rangeId).textContent = "--";
        return;
      }}
      const min = Math.min(...values);
      const max = Math.max(...values);
      const spread = max - min || 1;
      document.getElementById(rangeId).textContent = `${{formatValue(min)}} ${{i18n.to}} ${{formatValue(max)}}`;
      const grid = document.createElementNS("http://www.w3.org/2000/svg", "path");
      grid.setAttribute("d", `M ${{pad}} ${{height - pad}} H ${{width - pad}} M ${{pad}} ${{pad}} H ${{width - pad}}`);
      grid.setAttribute("stroke", "#dce5df");
      grid.setAttribute("stroke-width", "1");
      svg.appendChild(grid);
      series.forEach((item) => {{
        const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        const usable = points.map((row, index) => [index, Number(row[item.field])]).filter((pair) => !Number.isNaN(pair[1]));
        const d = usable.map((pair, index) => {{
          const x = pad + (pair[0] / Math.max(points.length - 1, 1)) * (width - pad * 2);
          const y = height - pad - ((pair[1] - min) / spread) * (height - pad * 2);
          return `${{index === 0 ? "M" : "L"}} ${{x.toFixed(1)}} ${{y.toFixed(1)}}`;
        }}).join(" ");
        path.setAttribute("d", d);
        path.setAttribute("fill", "none");
        path.setAttribute("stroke", item.color);
        path.setAttribute("stroke-width", "2.5");
        path.setAttribute("stroke-linecap", "round");
        svg.appendChild(path);
      }});
    }}

    function renderCharts() {{
      drawChart("tempChart", "tempRange", [
        {{ field: "temperature_c", color: "#1f7a4f" }},
        {{ field: "feels_like_c", color: "#a96516" }}
      ]);
      drawChart("pressureChart", "pressureRange", [
        {{ field: "pressure_sea_level_hpa", color: "#2366a8" }}
      ]);
      drawChart("windChart", "windRange", [
        {{ field: "wind_speed_ms", color: "#2366a8" }},
        {{ field: "wind_gust_ms", color: "#a96516" }}
      ]);
      drawChart("rainChart", "rainRange", [
        {{ field: "rain_rate_mm_h", color: "#a33d32" }}
      ]);
      drawChart("sunChart", "sunRange", [
        {{ field: "solar_radiation_wm2", color: "#a96516" }}
      ]);
    }}

    function ingressUrl(path) {{
      const base = window.location.pathname.endsWith("/") ? window.location.pathname : window.location.pathname + "/";
      return base + path;
    }}

    async function refresh() {{
      try {{
        const response = await fetch(ingressUrl("api/state"), {{ cache: "no-store" }});
        const payload = await response.json();
        updateText(payload);
        renderCharts();
      }} catch (error) {{
        document.getElementById("statusText").textContent = i18n.ui_error;
        document.getElementById("statusDetail").textContent = String(error);
      }}
    }}

    refresh();
    setInterval(refresh, 5000);
    window.addEventListener("resize", renderCharts);
  </script>
</body>
</html>
"""
