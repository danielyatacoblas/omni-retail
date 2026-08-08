# -*- coding: utf-8 -*-
"""Dibuja `docs/flujo.svg`: qué pasa desde el video hasta la decisión.

    python scripts/medir_modelos.py     # primero, deja docs/modelos.json
    python scripts/diagrama.py

El diagrama **lee las cifras medidas** de `docs/modelos.json` y las escribe en
las tarjetas de los modelos. Así no puede quedarse contando una versión del
sistema que ya no existe: si cambia el modelo o la máquina, se vuelve a correr
y el dibujo cambia solo.

Se genera en SVG y no en Mermaid porque hace falta controlar el tamaño de cada
tarjeta para meter cuatro cifras dentro, y porque un SVG se abre a pantalla
completa sin depender de que GitHub decida renderizar.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape

RAIZ = Path(__file__).resolve().parents[1]
DOCS = RAIZ / "docs"

W, H = 2000, 1180
COL = ["#e2e8f0", "#dbeafe", "#ede9fe", "#dcfce7", "#fef3c7"]

TITULO = "OMNI Retail · del video a la decisión"
BAJADA = ("Cada etapa dice qué aporta y con qué modelo. Las cifras de "
          "velocidad están medidas en esta máquina; las de acierto vienen de "
          "la validación con la que se entrenó cada modelo.")
PIE = ("Sin el seguimiento, una persona vista en 200 fotogramas serían 200 "
       "personas. Ese es el paso que convierte detecciones en una cifra de "
       "negocio.")

CARRILES = [
    ("Entrada", "Lo que ya existe en la tienda"),
    ("Detección", "Qué hay en cada fotograma"),
    ("Identidad", "Quién es quién entre fotogramas"),
    ("Analítica", "Qué significa para el negocio"),
    ("Decisión", "Qué se hace con eso"),
]


def _t(x, y, txt, size=12, peso="400", color="#0f172a", anchor="start"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{peso}" '
            f'fill="{color}" text-anchor="{anchor}">{escape(txt)}</text>')


def tarjeta(x, y, w, h, titulo, lineas, etiqueta, color, cifras=None):
    """La etiqueta va ARRIBA del título, no a su derecha.

    A la derecha se solapaban en cuanto el título pasaba de tres palabras, y
    eso no se ve hasta que se renderiza — pasó con «Cuánta gente entró y no
    compró».
    """
    p = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" '
         f'fill="#ffffff" stroke="#94a3b8" stroke-width="2" '
         f'filter="url(#shadow)"/>']
    yy = y + 26
    if etiqueta:
        ew = 12 + len(etiqueta) * 6.4
        p.append(f'<rect x="{x + 16}" y="{y + 12}" width="{ew}" '
                 f'height="20" rx="10" fill="{color}"/>')
        p.append(_t(x + 16 + ew / 2, y + 26, etiqueta, 9.5, "700",
                    "#0f172a", "middle"))
        yy = y + 54
    for ln in _partir(titulo, int((w - 32) / 8.1)):
        p.append(_t(x + 16, yy, ln, 14.5, "700"))
        yy += 19
    yy += 6
    for ln in lineas:
        p.append(_t(x + 16, yy, ln, 11, "400", "#475569"))
        yy += 16
    if cifras:
        yy += 4
        p.append(f'<line x1="{x + 16}" y1="{yy - 12}" x2="{x + w - 16}" '
                 f'y2="{yy - 12}" stroke="#e2e8f0" stroke-width="1.5"/>')
        for et, val, tono in cifras:
            p.append(_t(x + 16, yy + 4, et, 9.5, "600", "#64748b"))
            p.append(_t(x + w - 16, yy + 4, val, 12, "700", tono, "end"))
            yy += 19
    return "".join(p)


def flecha(x1, y1, x2, y2, texto="", punteada=False):
    mx = (x1 + x2) / 2
    d = f"M {x1} {y1} H {mx} V {y2} H {x2}"
    guion = ' stroke-dasharray="8 7"' if punteada else ""
    s = (f'<path d="{d}" fill="none" stroke="#334155" stroke-width="2.2"'
         f'{guion} marker-end="url(#arrow)"/>')
    if texto:
        s += (f'<text x="{mx}" y="{min(y1, y2) - 10}" font-size="11" '
              f'font-weight="600" fill="#334155" text-anchor="middle" '
              f'stroke="#ffffff" stroke-width="5" paint-order="stroke">'
              f'{escape(texto)}</text>')
    return s


def medidas() -> dict:
    f = DOCS / "modelos.json"
    if not f.exists():
        return {}
    return {m["archivo"]: m for m in json.loads(f.read_text(encoding="utf-8"))}


def pct(m, k):
    v = (m.get("metricas") or {}).get(k)
    return f"{v * 100:.1f} %" if isinstance(v, (int, float)) else "—"


def main() -> int:
    med = medidas()
    y11 = med.get("yolo11n.pt", {})
    world = med.get("yolov8s-world.pt", {})

    cx = [60, 460, 860, 1240, 1620]
    cw = [360, 360, 340, 340, 320]

    piezas = ['<rect width="100%" height="100%" fill="#f8fafc"/>']
    piezas.append(_t(48, 52, TITULO, 30, "700"))
    for i, ln in enumerate(_partir(BAJADA, 118)):
        piezas.append(_t(48, 82 + i * 20, ln, 14, "400", "#475569"))

    top, alto = 150, 900
    for i, (nombre, sub) in enumerate(CARRILES):
        piezas.append(f'<rect x="{cx[i]}" y="{top}" width="{cw[i]}" '
                      f'height="{alto}" rx="18" fill="{COL[i]}" '
                      f'fill-opacity="0.5" stroke="#94a3b8" '
                      f'stroke-width="1.5"/>')
        piezas.append(_t(cx[i] + 16, top + 28, nombre.upper(), 13, "700",
                         "#334155"))
        piezas.append(_t(cx[i] + 16, top + 46, sub, 10.5, "400", "#64748b"))

    # ── flechas primero, para que las tarjetas queden encima ──────────────
    piezas.append(flecha(cx[0] + cw[0] - 20, 330, cx[1] + 20, 330, "fotogramas"))
    # Esta va de la primera columna a la cuarta: si se traza recto atraviesa
    # dos tarjetas. Se baja por debajo de todo y se sube al llegar.
    piezas.append(
        f'<path d="M {cx[0] + cw[0] - 20} 700 V 1010 H {cx[3] + 150} V 960" '
        f'fill="none" stroke="#334155" stroke-width="2.2" '
        f'marker-end="url(#arrow)"/>'
        + _t((cx[0] + cw[0] + cx[3]) / 2, 1002,
             "las zonas entran en la analítica, no en el detector", 11.5,
             "600", "#334155", "middle"))
    piezas.append(flecha(cx[1] + cw[1] - 20, 330, cx[2] + 20, 400, "cajas"))
    piezas.append(flecha(cx[1] + cw[1] - 20, 660, cx[3] + 20, 880, "densidad",
                         punteada=True))
    piezas.append(flecha(cx[2] + cw[2] - 20, 400, cx[3] + 20, 400, "ID estable"))
    piezas.append(flecha(cx[3] + cw[3] - 20, 400, cx[4] + 20, 330, ""))
    piezas.append(flecha(cx[3] + cw[3] - 20, 700, cx[4] + 20, 560, ""))
    piezas.append(flecha(cx[3] + cw[3] - 20, 880, cx[4] + 20, 790, ""))

    # ── entrada ───────────────────────────────────────────────────────────
    piezas.append(tarjeta(
        cx[0] + 20, 250, cw[0] - 40, 160,
        "Cámara que ya está puesta",
        ["Un .mp4 de la cámara de siempre.",
         "Sin sensores nuevos, sin obra,",
         "sin tocar el punto de venta."],
        "EXISTENTE", "#e2e8f0"))
    piezas.append(tarjeta(
        cx[0] + 20, 560, cw[0] - 40, 170,
        "Zonas dibujadas a mano",
        ["Una línea sobre la puerta y un",
         "polígono por área. Se guardan",
         "de 0 a 1: valen aunque cambie",
         "la resolución del fotograma."],
        "UNA VEZ", "#dbeafe"))

    # ── detección ─────────────────────────────────────────────────────────
    piezas.append(tarjeta(
        cx[1] + 20, 240, cw[1] - 40, 245,
        "YOLO11n · personas",
        ["Dice dónde hay una persona en",
         "cada fotograma, por separado.",
         "Entrenado sobre COCO."],
        "DETECTOR", "#dcfce7",
        [("mAP@50 (COCO)", pct(y11, "mAP50"), "#166534"),
         ("mAP@50-95", pct(y11, "mAP50-95"), "#166534"),
         ("velocidad medida",
          f"{y11.get('fps', '—')} fps", "#1e40af"),
         ("latencia", f"{y11.get('ms', '—')} ms", "#1e40af")]))
    piezas.append(tarjeta(
        cx[1] + 20, 570, cw[1] - 40, 225,
        "YOLO-World · anaquel",
        ["Vocabulario abierto: se le pide",
         "«bottle, box, can» sin reentrenar.",
         "Umbral bajo a propósito — importa",
         "cuánto hay, no qué producto es."],
        "OPCIONAL", "#fef3c7",
        [("clases pedidas", "9 términos", "#92400e"),
         ("velocidad medida",
          f"{world.get('fps', '—')} fps", "#1e40af"),
         ("umbral", "0.05", "#92400e")]))

    # ── identidad ─────────────────────────────────────────────────────────
    piezas.append(tarjeta(
        cx[2] + 20, 300, cw[2] - 40, 250,
        "ByteTrack",
        ["Le pone el mismo ID a la misma",
         "persona entre fotogramas.",
         "",
         "Sin esto, alguien visto en 200",
         "fotogramas serían 200 personas",
         "y el número no valdría nada."],
        "SEGUIMIENTO", "#ede9fe",
        [("no necesita todos los", "fotogramas", "#5b21b6"),
         ("margen que deja", "CPU para el resto", "#5b21b6")]))

    # ── analítica ─────────────────────────────────────────────────────────
    for y, tit, ls, cif in (
        (300, "Cruces con dirección",
         ["Entró o salió según por dónde", "atravesó la línea."],
         [("aforo ahora", "entradas − salidas", "#166534")]),
        (610, "Permanencia por zona",
         ["Segundos acumulados por persona", "dentro de cada polígono."],
         [("tiempo", "del video, no del reloj", "#166534")]),
        (790, "Nivel de anaquel",
         ["Densidad de bordes contra la del", "primer fotograma."],
         [("es", "heurística, no detector", "#92400e")]),
    ):
        piezas.append(tarjeta(cx[3] + 20, y, cw[3] - 40, 165, tit, ls,
                              "", "", cif))

    # ── decisión ──────────────────────────────────────────────────────────
    for y, tit, ls in (
        (250, "Cuánta gente entró y no compró",
         ["Se cruza con la venta del día.", "Es la conversión real de la", "tienda."]),
        (480, "Cuánto se espera en caja",
         ["Cuándo abrir otra. El dato que", "hoy se estima a ojo."]),
        (710, "Qué estante reponer",
         ["Y antes de que un cliente se", "vaya sin el producto."]),
    ):
        piezas.append(tarjeta(cx[4] + 20, y, cw[4] - 40, 175, tit, ls,
                              "VALOR", "#dcfce7"))

    piezas.append(f'<rect x="48" y="1090" width="{W - 96}" height="52" '
                  f'rx="12" fill="#e2e8f0"/>')
    piezas.append(_t(70, 1122, PIE, 13.5, "700"))

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d" '
           f'font-family="Segoe UI, Arial, sans-serif">'
           f'<title id="t">{escape(TITULO)}</title>'
           f'<desc id="d">{escape(BAJADA)}</desc>'
           '<defs>'
           '<filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">'
           '<feDropShadow dx="0" dy="3" stdDeviation="4" flood-color="#0f172a" '
           'flood-opacity="0.14"/></filter>'
           '<marker id="arrow" markerWidth="9" markerHeight="9" refX="7" '
           'refY="4.5" orient="auto"><path d="M0,0 L0,9 L8,4.5 z" '
           'fill="#334155"/></marker>'
           '</defs>' + "".join(piezas) + '</svg>')

    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "flujo.svg").write_text(svg, encoding="utf-8", newline="\n")
    print(f"  docs/flujo.svg  {len(svg) // 1024} KB · "
          f"{'con' if med else 'SIN'} cifras medidas")
    return 0


def _partir(texto: str, ancho: int) -> list:
    palabras, lineas, actual = texto.split(), [], ""
    for p in palabras:
        if len(actual) + len(p) + 1 > ancho:
            lineas.append(actual)
            actual = p
        else:
            actual = f"{actual} {p}".strip()
    if actual:
        lineas.append(actual)
    return lineas


if __name__ == "__main__":
    sys.exit(main())
