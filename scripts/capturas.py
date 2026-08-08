# -*- coding: utf-8 -*-
"""Genera las capturas del README a partir de la aplicación de verdad.

    python -m uvicorn backend.main:app --port 8010     # en otra consola
    python scripts/capturas.py

Se generan en vez de recortarse a mano porque una captura hecha a mano
envejece en silencio: cambia un color, se añade un panel, y el README sigue
enseñando la versión de hace tres semanas sin que nadie se entere.

Se conduce Chrome por CDP y no con `--screenshot` porque el tablero se alimenta
de un MJPEG: es una respuesta que no termina nunca, así que la página nunca
queda «cargada» y `--virtual-time-budget` se cuelga. Además el tiempo virtual
resolvería los `setTimeout` al instante, y aquí hay que esperar segundos de
verdad a que la GPU procese fotogramas de verdad.
"""
from __future__ import annotations

import asyncio
import base64
import json
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import websockets

RAIZ = Path(__file__).resolve().parents[1]
DOCS = RAIZ / "docs" / "capturas"
PUERTO = 8010
PUERTO_CDP = 9333

# (archivo, escena, video, módulo, segundos de proceso, ancho, alto)
ESCENAS = [
    ("01-conteo", "tablero", "^entradas", "conteo", 12, 1500, 1000),
    ("02-permanencia", "tablero", "tiempo_en_caja", "permanencia", 14, 1500, 1000),
    ("03-anaqueles", "tablero", "anaqueles", "anaqueles", 14, 1500, 1000),
    ("04-editor-de-zonas", "editor", "tiempo_en_caja", "permanencia", 0, 1500, 1000),
]


def chrome() -> str:
    for c in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              "/usr/bin/google-chrome", "/usr/bin/chromium"):
        if Path(c).exists():
            return c
    hallado = shutil.which("chrome") or shutil.which("chromium")
    if not hallado:
        raise SystemExit("No se encontró Chrome.")
    return hallado


def vivo() -> bool:
    try:
        with urllib.request.urlopen(
                f"http://127.0.0.1:{PUERTO}/api/videos", timeout=4) as r:
            return r.status == 200
    except Exception:
        return False


def _objetivo(intentos: int = 60) -> str:
    for _ in range(intentos):
        try:
            with urllib.request.urlopen(
                    f"http://127.0.0.1:{PUERTO_CDP}/json", timeout=2) as r:
                for t in json.load(r):
                    if t.get("type") == "page":
                        return t["webSocketDebuggerUrl"]
        except Exception:
            pass
        time.sleep(0.5)
    raise SystemExit("Chrome no abrió el puerto de depuración.")


class Sesion:
    def __init__(self, ws):
        self.ws, self.n = ws, 0

    async def cmd(self, metodo: str, **params):
        self.n += 1
        mio = self.n
        await self.ws.send(json.dumps(
            {"id": mio, "method": metodo, "params": params}))
        while True:
            msg = json.loads(await self.ws.recv())
            if msg.get("id") == mio:
                if "error" in msg:
                    raise RuntimeError(f"{metodo}: {msg['error']}")
                return msg.get("result", {})

    async def js(self, expr: str, segundos: int = 300):
        r = await self.cmd("Runtime.evaluate", expression=expr,
                           awaitPromise=True, returnByValue=True,
                           timeout=segundos * 1000)
        det = r.get("exceptionDetails")
        if det:
            raise RuntimeError(det.get("exception", {}).get("description")
                               or det.get("text"))
        return r.get("result", {}).get("value")


async def una(s: Sesion, nombre, escena, video, uc, segs, ancho, alto) -> bool:
    await s.cmd("Emulation.setDeviceMetricsOverride",
                width=ancho, height=alto, deviceScaleFactor=1, mobile=False)
    await s.cmd("Page.navigate", url=f"http://127.0.0.1:{PUERTO}/")
    await asyncio.sleep(3)
    guion = (RAIZ / "scripts" / "capturas.js").read_text(encoding="utf-8")
    op = json.dumps({"video": video, "uc": uc, "segs": segs})

    fallo = None
    try:
        await s.js(f"{guion}\nmontar('{escena}', {op})", segundos=segs + 240)
    except Exception as e:
        # Se fotografía igual: la pantalla del fallo dice en dos segundos lo
        # que el mensaje de la excepción no dice nunca.
        fallo = e

    r = await s.cmd("Page.captureScreenshot", format="png",
                    captureBeyondViewport=False)
    destino = DOCS / f"{nombre}.png"
    destino.write_bytes(base64.b64decode(r["data"]))
    kb = destino.stat().st_size // 1024
    if fallo is not None:
        print(f"  {destino.name:<28} FALLÓ — {str(fallo)[:90]}")
        return False
    print(f"  {destino.name:<28} {kb} KB")
    return True


async def trabajo() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    perfil = RAIZ / "scripts" / "_perfil_chrome"
    shutil.rmtree(perfil, ignore_errors=True)
    proc = subprocess.Popen(
        [chrome(), "--headless=new", "--disable-gpu", "--mute-audio",
         "--force-prefers-reduced-motion",
         f"--remote-debugging-port={PUERTO_CDP}",
         f"--user-data-dir={perfil}",
         "--no-first-run", "--no-default-browser-check", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    malas = 0
    try:
        async with websockets.connect(_objetivo(),
                                      max_size=64 * 1024 * 1024) as ws:
            s = Sesion(ws)
            await s.cmd("Page.enable")
            await s.cmd("Runtime.enable")
            for esc in ESCENAS:
                if not await una(s, *esc):
                    malas += 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except Exception:
            proc.kill()
        shutil.rmtree(perfil, ignore_errors=True)
    return 1 if malas else 0


def main() -> int:
    if not vivo():
        print(f"  Levanta el servidor primero:\n"
              f"    python -m uvicorn backend.main:app --port {PUERTO}")
        return 2
    return asyncio.run(trabajo())


if __name__ == "__main__":
    sys.exit(main())
