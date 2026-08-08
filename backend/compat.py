"""Parche para que el conteo de línea siga funcionando con NumPy 2.

NumPy 2.0 **eliminó** el producto vectorial de dos dimensiones: `np.cross`
sobre vectores 2-D estaba obsoleto desde la 1.x y ahora lanza ValueError.
`supervision.LineZone.trigger` lo usa por dentro, así que en cuanto la primera
persona aparecía en cuadro el hilo de procesamiento moría entero.

Lo peor no era el fallo, sino la forma: la interfaz se quedaba en «Procesando…»
para siempre, con el contador a cero y sin un solo mensaje. Parecía un video
lento. La excepción salía por la consola del servidor, donde no la ve nadie.

Se parchea aquí y no se fija la versión de NumPy porque el intérprete es el
mismo para los cinco MVPs y torch está compilado contra esta versión: bajar
NumPy arreglaría el conteo y rompería la inferencia.
"""
from __future__ import annotations

from typing import cast

import numpy as np
import numpy.typing as npt


def _cross_2d(anchors: npt.NDArray[np.number], vector) -> npt.NDArray[np.number]:
    """El producto vectorial en 2-D: un escalar, no un vector.

    Misma cuenta que hacía `np.cross` antes de la 2.0 — z = x1*y2 - y1*x2 —
    escrita a mano porque ahora hay que escribirla a mano.
    """
    vx = vector.end.x - vector.start.x
    vy = vector.end.y - vector.start.y
    rel = anchors - np.array([vector.start.x, vector.start.y])
    return cast(npt.NDArray[np.number], vx * rel[..., 1] - vy * rel[..., 0])


def aplicar() -> bool:
    """Devuelve True si hizo falta parchear."""
    if not hasattr(np, "cross"):
        return False
    try:
        np.cross(np.array([1.0, 0.0]), np.array([0.0, 1.0]))
        return False        # NumPy 1.x: no hay nada que arreglar
    except Exception:
        pass

    from supervision.detection.utils import internal
    internal.cross_product = _cross_2d
    # LineZone importó el nombre directamente, así que hay que sustituirlo
    # también ahí: parchear solo el módulo de origen no cambiaría nada.
    from supervision.detection import line_zone
    line_zone.cross_product = _cross_2d
    return True


PARCHEADO = aplicar()
