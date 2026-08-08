# -*- coding: utf-8 -*-
"""Dibuja `docs/portada.svg`: el proyecto entero de un vistazo.

    python scripts/medir_modelos.py    # deja docs/modelos.json
    python scripts/portada.py

Es la imagen de cabecera. `docs/flujo.svg` sigue existiendo y sigue teniendo el
detalle; esta es la que se ve de lejos, en una rejilla de portafolio o en una
pantalla compartida, donde el flujograma completo no se lee.

Por eso aquí manda una regla: **cuatro pasos, una idea por paso, y ninguna
línea de texto menor de 17 px**. Si algo no cabe en cinco palabras, va en el
flujograma, no aquí. Los iconos son trazos SVG en línea, sin depender de
ninguna fuente ni CDN.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape

RAIZ = Path(__file__).resolve().parents[1]
DOCS = RAIZ / "docs"

W, H = 1800, 1000

# Trazos estilo Lucide, en un lienzo de 24×24 que luego se escala.
ICONOS = {
    "video": '<path d="m22 8-6 4 6 4V8Z"/><rect width="14" height="12" x="2" y="6" rx="2"/>',
    "cpu": '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M15 2v2M15 20v2M2 15h2M2 9h2M20 15h2M20 9h2M9 2v2M9 20v2"/>',
    "ruta": '<circle cx="6" cy="19" r="3"/><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/><circle cx="18" cy="5" r="3"/>',
    "grafico": '<path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/>',
    "personas": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "reloj": '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    "caja": '<path d="M11 21.73a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73Z"/><path d="M3.3 7 12 12l8.7-5"/><path d="M12 22V12"/>',
    "planta": '<path d="M7 20h10"/><path d="M10 20c5.5-2.5.8-6.4 3-10"/><path d="M9.5 9.4c1.1.8 1.8 2.2 2.3 3.7-2 .4-3.5.4-4.8-.3-1.2-.6-2.3-1.9-3-4.2 2.8-.5 4.4 0 5.5.8z"/><path d="M14.1 6a7 7 0 0 0-1.1 4c1.9-.1 3.3-.6 4.3-1.4 1-1 1.6-2.3 1.7-4.6-2.7.1-4 1-4.9 2z"/>',
    "escudo": '<path d="M20 13c0 5-3.5 7.5-7.7 8.9a1 1 0 0 1-.6 0C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.2-2.7a1 1 0 0 1 1.6 0C14.6 3.8 17 5 19 5a1 1 0 0 1 1 1z"/>',
    "casco": '<path d="M2 18h20"/><path d="M4 18v-4a8 8 0 0 1 16 0v4"/><path d="M10 6V4a2 2 0 0 1 4 0v2"/>',
    "fuego": '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>',
    "alerta": '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4M12 17h.01"/>',
    "correo": '<rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>',
    "documento": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8M16 13H8M16 17H8"/>',
    "visto": '<path d="M20 6 9 17l-5-5"/>',
    "compartir": '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="m8.59 13.51 6.83 3.98M15.41 6.51l-6.82 3.98"/>',
    "dron": '<path d="M10 10 7 7M14 10l3-3M10 14l-3 3M14 14l3 3"/><rect x="10" y="10" width="4" height="4" rx="1"/><circle cx="5" cy="5" r="2.5"/><circle cx="19" cy="5" r="2.5"/><circle cx="5" cy="19" r="2.5"/><circle cx="19" cy="19" r="2.5"/>',
}

TITULO = "OMNI Retail"
LEMA = "Del video de la cámara a la decisión del día"
FRASE = ("Sin seguimiento, una persona vista en 200 fotogramas serían 200 "
         "personas. Ese paso convierte detecciones en una cifra de negocio.")
CATEGORIA = "VISIÓN COMPUTACIONAL"
ACENTO = "#2D6CDF"


def icono(x, y, tamano, nombre, color):
    """Un icono centrado en (x, y), escalado desde su lienzo de 24×24."""
    k = tamano / 24
    return (f'<g transform="translate({x - tamano / 2},{y - tamano / 2}) '
            f'scale({k})" fill="none" stroke="{color}" stroke-width="1.9" '
            f'stroke-linecap="round" stroke-linejoin="round">'
            f'{ICONOS.get(nombre, "")}</g>')


def _t(x, y, txt, size, peso="400", color="#0f172a", anchor="start",
       espaciado=None):
    esp = f' letter-spacing="{espaciado}"' if espaciado else ""
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{peso}" '
            f'fill="{color}" text-anchor="{anchor}"{esp}>'
            f'{escape(str(txt))}</text>')


def paso(x, y, w, n, nom_icono, rotulo, titulo, dato, pie, color):
    """Un paso: número, icono grande, dos líneas y un dato que se lee de lejos."""
    p = [f'<rect x="{x}" y="{y}" width="{w}" height="440" rx="24" '
         f'fill="#ffffff" stroke="#cbd5e1" stroke-width="2.5" '
         f'filter="url(#sombra)"/>']
    cx = x + w / 2
    p.append(f'<circle cx="{cx}" cy="{y + 108}" r="54" fill="{color}" '
             f'fill-opacity="0.12"/>')
    p.append(icono(cx, y + 108, 52, nom_icono, color))
    p.append(_t(x + 26, y + 44, n, 30, "800", "#cbd5e1"))
    p.append(_t(cx, y + 200, rotulo.upper(), 17, "800", color, "middle", "2.5"))
    p.append(_t(cx, y + 246, titulo, 27, "700", "#0f172a", "middle"))
    p.append(f'<line x1="{x + 40}" y1="{y + 286}" x2="{x + w - 40}" '
             f'y2="{y + 286}" stroke="#e2e8f0" stroke-width="2"/>')
    p.append(_t(cx, y + 350, dato, 44, "800", color, "middle"))
    p.append(_t(cx, y + 390, pie, 19, "500", "#64748b", "middle"))
    return "".join(p)


def medidas() -> dict:
    f = DOCS / "modelos.json"
    if not f.exists():
        return {}
    return {m["archivo"]: m for m in json.loads(f.read_text(encoding="utf-8"))}


def main() -> int:
    med = medidas()
    y11 = med.get("yolo11n.pt", {})
    fps = (f"{1000 / y11['mejor_ms']:.0f} fps"
           if y11.get("mejor_ms") else "—")
    mapa = ((y11.get("metricas") or {}).get("mAP50"))
    acierto = f"{mapa * 100:.0f} %" if mapa else "—"

    PASOS = [
        ("01", "video", "Entra", "El video de siempre",
         "0 €", "en hardware nuevo"),
        ("02", "cpu", "Detecta", "YOLO11n en la GPU",
         fps, f"mAP@50 de {acierto}"),
        ("03", "ruta", "Sigue", "ByteTrack pone el ID",
         "1", "ID por persona"),
        ("04", "grafico", "Decide", "Entradas, colas y anaqueles",
         "3", "cifras que hoy no existen"),
    ]

    m, hueco = 70, 28
    ancho = (W - 2 * m - hueco * 3) / 4
    piezas = [f'<rect width="100%" height="100%" fill="#f8fafc"/>',
              f'<rect x="0" y="0" width="{W}" height="10" fill="{ACENTO}"/>']

    piezas.append(_t(m, 92, TITULO, 58, "800"))
    piezas.append(_t(m, 138, LEMA, 26, "500", "#475569"))
    piezas.append(f'<rect x="{W - m - 250}" y="58" width="250" height="46" '
                  f'rx="23" fill="{ACENTO}" fill-opacity="0.12"/>')
    piezas.append(_t(W - m - 125, 89, CATEGORIA, 16, "800",
                     ACENTO, "middle", "1.5"))

    for i, (n, ico, rot, tit, dato, pie) in enumerate(PASOS):
        x = m + i * (ancho + hueco)
        piezas.append(paso(x, 200, ancho, n, ico, rot, tit, dato, pie, ACENTO))
        if i < 3:
            fx = x + ancho + hueco / 2
            piezas.append(f'<path d="M {fx - 9} 410 l 11 10 l -11 10" '
                          f'fill="none" stroke="#94a3b8" stroke-width="3.5" '
                          f'stroke-linecap="round" stroke-linejoin="round"/>')

    piezas.append(f'<rect x="{m}" y="700" width="{W - 2 * m}" height="106" '
                  f'rx="20" fill="#0f172a"/>')
    piezas.append(icono(m + 62, 753, 40, "personas", "#ffffff"))
    for i, ln in enumerate(_partir(FRASE, 78)):
        piezas.append(_t(m + 110, 741 + i * 34, ln, 25, "600", "#ffffff"))

    for i, (et, val) in enumerate((("Pruebas", "19 pasando"),
                                   ("Modelos medidos", str(len(med))),
                                   ("Corre en", "CPU o GPU"),
                                   ("Datos simulados", "ninguno"))):
        x = m + i * ((W - 2 * m) / 4)
        piezas.append(_t(x, 880, et.upper(), 16, "700", "#94a3b8", "start",
                         "1.5"))
        piezas.append(_t(x, 924, val, 30, "800", "#0f172a"))

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d" '
           f'font-family="Segoe UI, Arial, sans-serif">'
           f'<title id="t">{escape(TITULO)} — {escape(LEMA)}</title>'
           f'<desc id="d">{escape(FRASE)}</desc>'
           '<defs><filter id="sombra" x="-20%" y="-20%" width="140%" '
           'height="140%"><feDropShadow dx="0" dy="4" stdDeviation="6" '
           'flood-color="#0f172a" flood-opacity="0.10"/></filter></defs>'
           + "".join(piezas) + '</svg>')

    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "portada.svg").write_text(svg, encoding="utf-8", newline="\n")
    print(f"  docs/portada.svg  {len(svg) // 1024} KB · {fps} · {acierto}")
    return 0


def _partir(texto: str, ancho: int) -> list:
    lineas, actual = [], ""
    for p in texto.split():
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
