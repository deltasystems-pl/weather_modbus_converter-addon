from __future__ import annotations

import json
import logging
import time
from typing import Any
from urllib.parse import urlencode

from .config import EcowittConfig, WebhookConfig
from .ecowitt import ecowitt_form_body

LOG = logging.getLogger(__name__)


def post_webhook(config: WebhookConfig, state: dict[str, Any], ecowitt: EcowittConfig) -> None:
    headers: dict[str, str]
    data: str
    if config.format == "json":
        headers = {"Content-Type": "application/json"}
        data = json.dumps(state)
    elif config.format in {"form", "ecowitt"}:
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = ecowitt_form_body(state, ecowitt)
    else:
        raise ValueError(f"Unsupported webhook format: {config.format}")

    attempts = max(1, config.retries + 1)
    for attempt in range(1, attempts + 1):
        try:
            import requests

            response = requests.post(config.url, data=data, headers=headers, timeout=config.timeout_seconds)
            if 200 <= response.status_code < 300:
                return
            raise RuntimeError(f"HTTP {response.status_code}: {response.text[:200]}")
        except Exception as exc:
            if attempt == attempts:
                raise
            LOG.warning("Webhook delivery failed on attempt %s/%s: %s", attempt, attempts, exc)
            time.sleep(min(2**attempt, 10))


def post_payload(url: str, payload: dict[str, Any] | str, content_type: str, timeout_seconds: float, retries: int) -> None:
    headers = {"Content-Type": content_type}
    data = payload if isinstance(payload, str) else json.dumps(payload)
    attempts = max(1, retries + 1)
    for attempt in range(1, attempts + 1):
        try:
            import requests

            response = requests.post(url, data=data, headers=headers, timeout=timeout_seconds)
            if 200 <= response.status_code < 300:
                return
            raise RuntimeError(f"HTTP {response.status_code}: {response.text[:200]}")
        except Exception as exc:
            if attempt == attempts:
                raise
            LOG.warning("Scheduled webhook delivery failed on attempt %s/%s: %s", attempt, attempts, exc)
            time.sleep(min(2**attempt, 10))


def form_payload(payload: dict[str, Any]) -> str:
    return urlencode({key: "" if value is None else str(value) for key, value in payload.items()})
