from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from math import ceil
from typing import Any


RAIN_DEFAULTS: dict[str, Any] = {
    "rain_rate_mm_h": 0.0,
    "rain_event_mm": 0.0,
    "rain_hour_mm": 0.0,
    "rain_last24h_mm": 0.0,
    "rain_day_mm": 0.0,
    "rain_week_mm": 0.0,
    "rain_month_mm": 0.0,
    "rain_year_mm": 0.0,
    "rain_state": False,
    "rain_level": "No Rain | IMGW None",
}


def rain_level(rain_rate_mm_h: float | None, rain_last24h_mm: float | None) -> str:
    rate = rain_rate_mm_h or 0.0
    last24 = rain_last24h_mm or 0.0
    intensity = "No Rain"
    if rate >= 60:
        intensity = "Cloudburst Signal"
    elif rate > 50:
        intensity = "Violent Rain"
    elif rate > 7.6:
        intensity = "Heavy Rain"
    elif rate > 2.5:
        intensity = "Moderate Rain"
    elif rate > 0.1:
        intensity = "Light Rain"
    elif rate > 0:
        intensity = "Trace"

    warning = "IMGW None"
    if last24 > 70:
        warning = "IMGW Level 3"
    elif last24 >= 50:
        warning = "IMGW Level 2"
    elif last24 >= 30:
        warning = "IMGW Level 1"
    return f"{intensity} | {warning}"


def with_rain_defaults(state: dict[str, Any]) -> dict[str, Any]:
    for key, value in RAIN_DEFAULTS.items():
        state.setdefault(key, value)
    return state


@dataclass
class RainAccumulator:
    event_idle_seconds: int = 3600
    counter_rollover_mm: float = 655.35
    max_delta_mm: float = 50.0
    rate_min_window_seconds: int = 600
    last_source_mm: float | None = None
    last_source_type: str | None = None
    last_update_ts: float | None = None
    last_rain_ts: float | None = None
    event_active: bool = False
    rate_mm_h: float = 0.0
    rate_last_update_ts: float | None = None
    rate_window_mm: float = 0.0
    rate_window_start_ts: float | None = None
    rate_buckets: dict[int, float] = field(default_factory=dict)
    hour_mm: float = 0.0
    day_mm: float = 0.0
    week_mm: float = 0.0
    month_mm: float = 0.0
    year_mm: float = 0.0
    event_mm: float = 0.0
    hour_key: int | None = None
    day_key: tuple[int, int] | None = None
    week_key: tuple[int, int] | None = None
    month_key: tuple[int, int] | None = None
    year_key: int | None = None
    buckets: dict[int, float] = field(default_factory=lambda: {hour: 0.0 for hour in range(24)})

    def update(self, state: dict[str, Any]) -> dict[str, Any]:
        source_mm, source_type = self._source(state)
        observed = _observed_at(state.get("observed_at"))
        now_ts = observed.timestamp() if observed else None
        if source_mm is None or now_ts is None:
            return self._publish(state)

        hour_key = int(now_ts // 3600)
        hour_of_day = observed.hour
        day_key = (observed.year, observed.timetuple().tm_yday)
        week_key = observed.isocalendar()[:2]
        month_key = (observed.year, observed.month)
        year_key = observed.year

        if self.last_source_mm is None:
            self._baseline(source_mm, source_type, now_ts, hour_key, day_key, week_key, month_key, year_key, hour_of_day)
            return self._publish(state)

        if source_type != self.last_source_type:
            self._baseline(source_mm, source_type, now_ts, hour_key, day_key, week_key, month_key, year_key, hour_of_day)
            return self._publish(state)

        self._roll_periods(hour_key, day_key, week_key, month_key, year_key)
        delta_mm = self._delta(source_mm)
        if delta_mm is None:
            self._baseline(source_mm, source_type, now_ts, hour_key, day_key, week_key, month_key, year_key, hour_of_day)
            return self._publish(state)
        if delta_mm > self.max_delta_mm:
            self.last_source_mm = source_mm
            self.last_update_ts = now_ts
            return self._publish(state)

        state["rain_delta_mm"] = round(delta_mm, 3)
        elapsed_s = now_ts - self.last_update_ts if self.last_update_ts is not None and now_ts > self.last_update_ts else 0.0
        if delta_mm > 0:
            self._add_rain(delta_mm, now_ts, hour_of_day)
            self._update_rate_after_delta(delta_mm, now_ts)
            self.last_source_mm = source_mm
            self.last_update_ts = now_ts
        else:
            self._update_rate_without_delta(now_ts, elapsed_s)

        return self._publish(state)

    def _source(self, state: dict[str, Any]) -> tuple[float | None, str | None]:
        if state.get("rain_counter_mm") is not None:
            return float(state["rain_counter_mm"]), "counter"
        if state.get("rain_total_mm") is not None:
            return float(state["rain_total_mm"]), "total"
        return None, None

    def _baseline(
        self,
        source_mm: float,
        source_type: str | None,
        now_ts: float,
        hour_key: int,
        day_key: tuple[int, int],
        week_key: tuple[int, int],
        month_key: tuple[int, int],
        year_key: int,
        hour_of_day: int,
    ) -> None:
        self.last_source_mm = source_mm
        self.last_source_type = source_type
        self.last_update_ts = now_ts
        self.rate_mm_h = 0.0
        self.rate_last_update_ts = None
        self.rate_window_mm = 0.0
        self.rate_window_start_ts = now_ts
        self.rate_buckets.clear()
        self.hour_key = hour_key
        self.day_key = day_key
        self.week_key = week_key
        self.month_key = month_key
        self.year_key = year_key
        self.buckets[hour_of_day] = 0.0

    def _roll_periods(
        self,
        hour_key: int,
        day_key: tuple[int, int],
        week_key: tuple[int, int],
        month_key: tuple[int, int],
        year_key: int,
    ) -> None:
        if self.hour_key is None:
            self.hour_key = hour_key
        elif hour_key != self.hour_key:
            crossed = hour_key - self.hour_key
            if crossed < 0 or crossed > 24:
                crossed = 24
            for offset in range(1, crossed + 1):
                self.buckets[(self.hour_key + offset) % 24] = 0.0
            self.hour_mm = 0.0
            self.hour_key = hour_key
        if day_key != self.day_key:
            self.day_mm = 0.0
            self.day_key = day_key
        if week_key != self.week_key:
            self.week_mm = 0.0
            self.week_key = week_key
        if month_key != self.month_key:
            self.month_mm = 0.0
            self.month_key = month_key
        if year_key != self.year_key:
            self.year_mm = 0.0
            self.year_key = year_key

    def _delta(self, source_mm: float) -> float | None:
        if self.last_source_mm is None:
            return 0.0
        delta_mm = source_mm - self.last_source_mm
        if delta_mm < -0.001:
            if self.counter_rollover_mm > self.last_source_mm >= self.counter_rollover_mm - self.max_delta_mm:
                delta_mm = (self.counter_rollover_mm - self.last_source_mm) + source_mm
            else:
                return None
        return 0.0 if delta_mm < 0.001 else delta_mm

    def _add_rain(self, delta_mm: float, now_ts: float, hour_of_day: int) -> None:
        self.hour_mm += delta_mm
        self.day_mm += delta_mm
        self.week_mm += delta_mm
        self.month_mm += delta_mm
        self.year_mm += delta_mm
        self.buckets[hour_of_day] = self.buckets.get(hour_of_day, 0.0) + delta_mm
        if not self.event_active or (self.last_rain_ts is not None and now_ts > self.last_rain_ts + self.event_idle_seconds):
            self.event_mm = 0.0
            self.event_active = True
        self.event_mm += delta_mm
        self.last_rain_ts = now_ts

    def _update_rate_after_delta(self, delta_mm: float, now_ts: float) -> None:
        minute_key = int(now_ts // 60)
        self.rate_buckets[minute_key] = self.rate_buckets.get(minute_key, 0.0) + delta_mm
        self._recalculate_rate(now_ts)

    def _update_rate_without_delta(self, now_ts: float, elapsed_s: float) -> None:
        self._recalculate_rate(now_ts)
        if self.last_rain_ts is not None and now_ts > self.last_rain_ts + self.event_idle_seconds:
            self.event_active = False
            self.event_mm = 0.0
        if elapsed_s > self.rate_min_window_seconds and self.rate_window_mm <= 0.0:
            self.rate_mm_h = 0.0

    def _recalculate_rate(self, now_ts: float) -> None:
        window_s = max(60, int(self.rate_min_window_seconds))
        window_minutes = max(1, ceil(window_s / 60))
        current_minute = int(now_ts // 60)
        oldest_minute = current_minute - window_minutes + 1
        self.rate_buckets = {
            key: value
            for key, value in self.rate_buckets.items()
            if key >= oldest_minute and value > 0.0
        }
        self.rate_window_mm = sum(self.rate_buckets.values())
        self.rate_window_start_ts = float(oldest_minute * 60)
        if self.rate_window_mm > 0.0:
            self.rate_mm_h = self.rate_window_mm * 3600.0 / float(window_s)
            self.rate_last_update_ts = now_ts
        else:
            self.rate_mm_h = 0.0
            self.rate_last_update_ts = None

    def _publish(self, state: dict[str, Any]) -> dict[str, Any]:
        last24 = max(sum(self.buckets.values()), self.day_mm)
        state.update(
            {
                "rain_rate_mm_h": round(self.rate_mm_h, 2),
                "rain_event_mm": round(self.event_mm, 2),
                "rain_hour_mm": round(self.hour_mm, 2),
                "rain_last24h_mm": round(last24, 2),
                "rain_day_mm": round(self.day_mm, 2),
                "rain_week_mm": round(self.week_mm, 2),
                "rain_month_mm": round(self.month_mm, 2),
                "rain_year_mm": round(self.year_mm, 2),
                "rain_state": self.rate_mm_h > 0.0 or self.rate_window_mm > 0.0,
                "rain_level": rain_level(self.rate_mm_h, last24),
            }
        )
        return with_rain_defaults(state)


def _observed_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
