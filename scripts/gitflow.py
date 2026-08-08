# -*- coding: utf-8 -*-
"""Escribe en el README el diagrama de ramas, leído del historial real.

    python scripts/gitflow.py

Sustituye el bloque marcado con `<!-- GITFLOW:inicio -->` … `<!-- GITFLOW:fin -->`.

Se genera en lugar de escribirse a mano por lo mismo que las capturas: dibujado
a mano, el día que se añada una rama el README enseñará un historial que ya no
existe. Y un diagrama de ramas que no corresponde con el repositorio dice de
quien lo escribió justo lo contrario de lo que pretende.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
README = RAIZ / "README.md"
INICIO, FIN = "<!-- GITFLOW:inicio -->", "<!-- GITFLOW:fin -->"

PARA_QUE = {
    "feature": "trabajo acotado, se integra en develop",
    "fix": "un fallo concreto",
    "docs": "documentación, diagramas y capturas",
    "develop": "rama de integración",
}


def _git(*args) -> str:
    return subprocess.run(["git", *args], cwd=RAIZ, capture_output=True,
                          text=True, encoding="utf-8", check=True).stdout


def ramas() -> list:
    """Las ramas fusionadas, de la más antigua a la más reciente."""
    salida = _git("log", "--merges", "--format=%s", "main")
    nombres = []
    for ln in salida.splitlines():
        m = re.search(r"Merge branch '([^']+)'", ln)
        if m:
            nombres.append(m.group(1))
    return list(reversed(nombres))


def diagrama(lista: list, etiquetas: list) -> str:
    """Un `gitGraph` de Mermaid, que GitHub dibuja sin plugins.

    Se dibuja el camino de verdad —feature a develop y develop a main— y no el
    atajo de feature a main: un gitflow sin `develop` sería otro dibujo.
    """
    filas = ["```mermaid", "gitGraph", '   commit id: "import"',
             "   branch develop"]
    pendientes = list(etiquetas)
    vistas = set()
    for r in lista:
        if r == "develop":
            # Una subida de develop a main: ahí es donde cae la etiqueta.
            tag = ' tag: "%s"' % pendientes.pop(0) if pendientes else ""
            filas += ["   checkout main", "   merge develop" + tag]
            continue
        if r not in vistas:
            vistas.add(r)
            filas += ["   checkout develop", "   branch " + r,
                      "   checkout " + r, "   commit"]
        filas += ["   checkout develop", "   merge " + r]
    filas.append("```")
    return "\n".join(filas)


def _orden(t: str):
    """v0.10.0 va DESPUÉS de v0.9.0, que ordenado como texto sería al revés."""
    return [int(x) for x in t.lstrip("v").split(".") if x.isdigit()]


def main() -> int:
    todas = ramas()
    if not todas:
        print("  No hay merges en el historial.")
        return 1

    conteo = {}
    for r in todas:
        conteo[r.split("/")[0]] = conteo.get(r.split("/")[0], 0) + 1
    commits = len(_git("log", "--format=%h", "main").splitlines())
    etiquetas = [t for t in _git("tag").splitlines() if t.strip()]

    partes = [
        "## Cómo se trabajó",
        "",
        f"**{commits} commits**, **{len(todas)} fusiones** y "
        f"**{len(etiquetas)} etiquetas** ({', '.join(f'`{t}`' for t in etiquetas)}). "
        "al generar este bloque. Cada rama entra con `--no-ff`: un merge "
        "aplastado ahorra una línea y "
        "borra la única prueba de que aquello fue una tarea con principio y "
        "final.",
        "",
        diagrama(todas, etiquetas),
        "",
        "| Prefijo | Para qué | Ramas |",
        "|---|---|---|",
    ]
    for pre in sorted(conteo, key=lambda p: -conteo[p]):
        partes.append(f"| `{pre}/` | {PARA_QUE.get(pre, 'otros')} "
                      f"| {conteo[pre]} |")
    partes += [
        "",
        "| Rama | Responsabilidad | Regla de salida |",
        "|---|---|---|",
        "| `main` | Lo que ve primero quien llega al repositorio "
        "| Solo recibe trabajo terminado y con las pruebas en verde |",
        "| `develop` | Integración: aquí se junta todo antes de subir "
        "| Merge `--no-ff` desde una rama `feature/*` |",
        "| `feature/*` | Un trabajo acotado, nombrado por lo que hace "
        "| Merge `--no-ff` a `develop` con sus pruebas escritas |",
        "",
        "Los mensajes siguen *Conventional Commits* y están en inglés. "
        "Explican **por qué**, no qué: el *qué* ya está en el diff. Varios "
        "cuentan el fallo que arreglan y cómo se descubrió, que es lo que "
        "sirve dentro de seis meses.",
        "",
        "<sub>El diagrama lo genera "
        "<a href=\"scripts/gitflow.py\"><code>scripts/gitflow.py</code></a> "
        "leyendo <code>git log --merges</code>.</sub>",
        "",
    ]
    bloque = "\n".join(partes)

    texto = README.read_text(encoding="utf-8")

    # La insignia de versión salía escrita a mano y se quedó en v0.3.0 con el
    # repositorio ya en la v0.5.0. Ahora sale de la última etiqueta, que es la
    # única fuente que no se puede olvidar de actualizar.
    if etiquetas:
        ultima = sorted(etiquetas, key=_orden)[-1]
        texto = re.sub(r"(badge/versi\u00f3n-)v[0-9.]+(-)",
                       lambda m: m.group(1) + ultima + m.group(2), texto)
    nuevo = f"{INICIO}\n\n{bloque}\n{FIN}"
    if INICIO in texto:
        texto = re.sub(re.escape(INICIO) + r".*?" + re.escape(FIN),
                       lambda _: nuevo, texto, flags=re.S)
    else:
        texto = texto.rstrip("\n") + "\n\n---\n\n" + nuevo + "\n"
    README.write_text(texto, encoding="utf-8", newline="\n")

    print(f"  {commits} commits · {len(todas)} fusiones · "
          f"{len(etiquetas)} etiquetas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
