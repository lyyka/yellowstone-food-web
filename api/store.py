from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from api.graph_model import FoodWeb

GRAPH_PATH = Path(
    os.environ.get(
        "GRAPH_PATH",
        Path(__file__).resolve().parents[1] / "data" / "graphs" / "yellowstone-mammals.json",
    )
)

_lock = threading.Lock()
_web: FoodWeb | None = None


def reset_web() -> None:
    global _web
    with _lock:
        _web = None


def get_web() -> FoodWeb:
    global _web
    with _lock:
        if _web is None:
            _web = FoodWeb.from_dict(json.loads(GRAPH_PATH.read_text()))
        return _web


def persist_web() -> None:
    web = get_web()
    payload = json.dumps(web.to_dict(), indent=2) + "\n"
    tmp = GRAPH_PATH.with_suffix(".json.tmp")
    tmp.write_text(payload)
    tmp.replace(GRAPH_PATH)
