"""Persistencia y geometría de zonas + línea de conteo por video.

Las coordenadas se guardan NORMALIZADAS (0..1) para ser independientes de la
resolución: el editor del frontend dibuja sobre el primer frame y el backend las
convierte a píxeles según el tamaño real del frame de procesamiento.

Archivo: data/zones/<video>.json
{
  "video": "market.mp4",
  "line":  {"a": [0.1, 0.3], "b": [0.5, 0.3]}  | null,
  "zones": [
    {"id":"z1","name":"Caja 1","type":"permanencia","color":"#3B82F6",
     "points": [[x,y],[x,y],...]}   # normalizado
  ]
}
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np

from .config import config

ZONE_TYPES = ("permanencia", "anaquel")


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


def zones_dir() -> Path:
    d = config.data_abs / "zones"
    d.mkdir(parents=True, exist_ok=True)
    return d


def zones_path(video: str) -> Path:
    return zones_dir() / f"{_safe(video)}.json"


def load_config(video: str) -> dict:
    p = zones_path(video)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"video": video, "line": None, "zones": []}


def save_config(video: str, data: dict) -> dict:
    data = dict(data)
    data["video"] = video
    # normaliza estructura mínima
    data.setdefault("line", None)
    data.setdefault("zones", [])
    for i, z in enumerate(data["zones"]):
        z.setdefault("id", f"z{i+1}")
        z.setdefault("type", "permanencia")
        if z["type"] not in ZONE_TYPES:
            z["type"] = "permanencia"
        z.setdefault("color", "#3B82F6")
        z.setdefault("name", f"Zona {i+1}")
    zones_path(video).write_text(json.dumps(data, indent=2, ensure_ascii=False),
                                 encoding="utf-8")
    return data


# ── conversión normalizado → píxeles ────────────────────────────────────────

def line_to_px(line: dict | None, w: int, h: int):
    if not line or "a" not in line or "b" not in line:
        return None
    a = (float(line["a"][0]) * w, float(line["a"][1]) * h)
    b = (float(line["b"][0]) * w, float(line["b"][1]) * h)
    return a, b


def zone_to_px(zone: dict, w: int, h: int) -> np.ndarray:
    pts = [(float(x) * w, float(y) * h) for x, y in zone["points"]]
    return np.array(pts, dtype=np.int32)
