# -*- coding: utf-8 -*-
"""Pruebas de zones.py — el nombre de video llega por HTTP y toca el disco.

    python -m pytest test_zones.py -q

Las zonas se guardan en un archivo cuyo nombre sale de la petición. Eso es
exactamente la forma que tiene un salto de directorio, así que aquí se fija que
`_safe` lo impide, y de paso que la conversión normalizado→píxeles sobrevive a
un cambio de resolución (que es toda la razón de guardarlas en 0..1).
"""
from __future__ import annotations

import numpy as np
import pytest

from backend import zones


# ── el nombre viene de fuera ────────────────────────────────────────────────

@pytest.mark.parametrize("entrada", [
    "../../../etc/passwd",
    "..\\..\\windows\\system32\\config",
    "video/../../secreto.json",
    "a/b/c.mp4",
])
def test_el_nombre_no_puede_salir_de_la_carpeta(entrada):
    destino = zones.zones_path(entrada).resolve()
    assert destino.parent == zones.zones_dir().resolve()


def test_se_conservan_los_caracteres_normales():
    assert zones._safe("market_01.mp4") == "market_01.mp4"


def test_un_json_roto_no_tumba_la_carga(tmp_path, monkeypatch):
    monkeypatch.setattr(zones.config, "data_dir", str(tmp_path))
    zones.zones_path("roto.mp4").write_text("{esto no es json", encoding="utf-8")
    # Devolver la configuración vacía deja al usuario redibujar; propagar la
    # excepción dejaría el video inservible hasta borrar el archivo a mano.
    cfg = zones.load_config("roto.mp4")
    assert cfg == {"video": "roto.mp4", "line": None, "zones": []}


# ── ida y vuelta ────────────────────────────────────────────────────────────

def test_guardar_rellena_lo_que_falta(tmp_path, monkeypatch):
    monkeypatch.setattr(zones.config, "data_dir", str(tmp_path))
    guardado = zones.save_config("m.mp4", {"zones": [{"points": [[0, 0], [1, 1]]}]})
    z = guardado["zones"][0]
    assert z["id"] == "z1"
    assert z["type"] == "permanencia"
    assert z["name"] == "Zona 1"
    assert z["color"].startswith("#")
    assert zones.load_config("m.mp4") == guardado


def test_un_tipo_inventado_cae_al_de_por_defecto(tmp_path, monkeypatch):
    monkeypatch.setattr(zones.config, "data_dir", str(tmp_path))
    guardado = zones.save_config(
        "m.mp4", {"zones": [{"type": "loquesea", "points": [[0, 0]]}]})
    assert guardado["zones"][0]["type"] == "permanencia"


# ── normalizado → píxeles ───────────────────────────────────────────────────

def test_la_zona_escala_con_la_resolucion():
    zona = {"points": [[0.0, 0.0], [0.5, 0.5], [1.0, 1.0]]}
    px = zones.zone_to_px(zona, 1920, 1080)
    assert px.dtype == np.int32
    assert px.tolist() == [[0, 0], [960, 540], [1920, 1080]]
    # La misma zona sobre un frame reescalado ocupa la misma parte de la imagen:
    # eso es lo que se gana guardando en 0..1 en vez de en píxeles.
    mitad = zones.zone_to_px(zona, 960, 540)
    assert mitad.tolist() == [[0, 0], [480, 270], [960, 540]]


def test_sin_linea_no_hay_linea():
    assert zones.line_to_px(None, 100, 100) is None
    assert zones.line_to_px({}, 100, 100) is None
    assert zones.line_to_px({"a": [0, 0]}, 100, 100) is None


def test_la_linea_escala_igual():
    a, b = zones.line_to_px({"a": [0.25, 0.5], "b": [0.75, 0.5]}, 800, 600)
    assert a == (200.0, 300.0)
    assert b == (600.0, 300.0)
