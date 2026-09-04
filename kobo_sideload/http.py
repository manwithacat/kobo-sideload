"""Tiny stdlib HTTP helper with a GitHub-friendly User-Agent."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from .config import USER_AGENT


def urlopen(url: str, timeout: int = 60):
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github+json, application/octet-stream, */*",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(request, timeout=timeout)


def get_json(url: str) -> Any:
    try:
        with urlopen(url) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GET {url} failed: HTTP {exc.code} {body[:300]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GET {url} failed: {exc.reason}") from exc
