# -*- coding: utf-8 -*-
"""Pruebas del conteo de línea — el fallo que no se veía.

    python -m pytest test_conteo.py -q

NumPy 2.0 eliminó el producto vectorial de dos dimensiones, y
`supervision.LineZone.trigger` lo usaba por dentro. Resultado: en cuanto la
primera persona aparecía en cuadro, el hilo de procesamiento moría con una
excepción que solo salía por la consola del servidor.

Desde la interfaz no se veía nada de eso. Se quedaba en «Procesando…» para
siempre, con el contador a cero. Parecía un video lento.

Este archivo existe para que ese fallo no pueda volver callado: si el parche de
`backend/compat.py` deja de aplicarse, estas pruebas se ponen rojas antes de
que nadie abra el navegador.
"""
from __future__ import annotations

import numpy as np
import pytest
import supervision as sv

from backend import compat


def persona(y1: float, y2: float, tid: int = 1) -> sv.Detections:
    """Una caja alta y estrecha, como una persona vista de frente."""
    d = sv.Detections(xyxy=np.array([[100.0, y1, 160.0, y2]]),
                      class_id=np.array([0]), confidence=np.array([0.9]))
    d.tracker_id = np.array([tid])
    return d


@pytest.fixture
def linea():
    """Una línea horizontal a media altura, de lado a lado."""
    return sv.LineZone(start=sv.Point(0, 300), end=sv.Point(640, 300))


# ── lo que se rompía ────────────────────────────────────────────────────────

def test_el_parche_hizo_falta_o_no_hacia_falta():
    """En NumPy 2 tiene que haberse aplicado; en NumPy 1, no."""
    dos_o_mas = int(np.__version__.split(".")[0]) >= 2
    assert compat.PARCHEADO is dos_o_mas


def test_trigger_no_revienta(linea):
    """El fallo original, tal cual: una detección bastaba para tumbarlo."""
    dentro, fuera = linea.trigger(persona(100, 280))
    assert len(dentro) == 1 and len(fuera) == 1


def test_el_producto_vectorial_2d_da_lo_de_siempre():
    """x1*y2 - y1*x2, que es lo que hacía np.cross antes de la 2.0."""
    class V:
        class start: x, y = 0.0, 0.0
        class end: x, y = 4.0, 0.0
    r = compat._cross_2d(np.array([[0.0, 3.0], [0.0, -3.0]]), V)
    assert r.tolist() == [12.0, -12.0]   # signo opuesto a cada lado


# ── el conteo, que es para lo que está ──────────────────────────────────────

def test_cruzar_hacia_abajo_cuenta_una_vez(linea):
    linea.trigger(persona(100, 280))     # arriba de la línea
    linea.trigger(persona(320, 500))     # ya pasó al otro lado
    assert linea.in_count + linea.out_count == 1


def test_quedarse_al_mismo_lado_no_cuenta(linea):
    for y in (100, 120, 140, 110):
        linea.trigger(persona(y, y + 180))
    assert linea.in_count == 0
    assert linea.out_count == 0


def test_ir_y_volver_cuenta_en_los_dos_sentidos(linea):
    linea.trigger(persona(100, 280))
    linea.trigger(persona(320, 500))
    linea.trigger(persona(100, 280))
    assert linea.in_count == 1
    assert linea.out_count == 1


def test_dos_personas_se_cuentan_por_separado(linea):
    dos_arriba = sv.Detections(
        xyxy=np.array([[100.0, 100.0, 160.0, 280.0],
                       [300.0, 100.0, 360.0, 280.0]]),
        class_id=np.array([0, 0]), confidence=np.array([0.9, 0.9]))
    dos_arriba.tracker_id = np.array([1, 2])
    linea.trigger(dos_arriba)

    dos_abajo = sv.Detections(
        xyxy=np.array([[100.0, 320.0, 160.0, 500.0],
                       [300.0, 320.0, 360.0, 500.0]]),
        class_id=np.array([0, 0]), confidence=np.array([0.9, 0.9]))
    dos_abajo.tracker_id = np.array([1, 2])
    linea.trigger(dos_abajo)

    assert linea.in_count + linea.out_count == 2


def test_sin_detecciones_no_cuenta_ni_revienta(linea):
    vacio = sv.Detections.empty()
    vacio.tracker_id = np.array([], dtype=int)
    linea.trigger(vacio)
    assert linea.in_count == 0 and linea.out_count == 0
