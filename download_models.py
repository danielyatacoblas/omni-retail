#!/usr/bin/env python3
"""Descarga los pesos de RF-DETR y videos de muestra de retail (Roboflow/Supervision).

Uso:
    python download_models.py            # pesos RF-DETR + videos de muestra
    python download_models.py --no-video # solo pesos del modelo
    python download_models.py --only-video

Los videos vienen de `supervision.assets` (Roboflow) — libres para pruebas.
Se guardan en videos/ y aparecen en el selector del dashboard.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VIDEOS = ROOT / "videos"
VIDEOS.mkdir(exist_ok=True)


def download_weights():
    print("→ Descargando pesos RF-DETR (nano) ...")
    try:
        from rfdetr import RFDETRNano
        RFDETRNano()   # instanciar dispara la descarga de pesos a la cache
        print("  ✓ pesos RF-DETR listos")
    except Exception as e:
        print(f"  ✗ error descargando RF-DETR: {e}")


def download_videos():
    print("→ Descargando videos de muestra (retail) desde Roboflow/Supervision ...")
    try:
        from supervision.assets import VideoAssets, download_assets
    except Exception as e:
        print(f"  ✗ supervision.assets no disponible: {e}")
        return

    # nombres candidatos (varían entre versiones de supervision)
    wanted = ["MARKET_SQUARE", "GROCERY_STORE", "MALL", "SUBWAY",
              "PEOPLE_WALKING", "SHOPPING_MALL"]
    got = 0
    for name in wanted:
        asset = getattr(VideoAssets, name, None)
        if asset is None:
            continue
        try:
            fname = download_assets(asset)     # descarga en el cwd
            src = Path(fname)
            if not src.exists():
                # algunas versiones devuelven solo el nombre
                src = ROOT / fname
            dst = VIDEOS / src.name
            if src.resolve() != dst.resolve():
                shutil.move(str(src), str(dst))
            print(f"  ✓ {dst.name}")
            got += 1
        except Exception as e:
            print(f"  · {name}: {e}")
    if got == 0:
        print("  (no se pudo descargar ninguno; copia tus .mp4 manualmente a videos/)")
    else:
        print(f"  ✓ {got} videos en videos/")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-video", action="store_true")
    ap.add_argument("--only-video", action="store_true")
    a = ap.parse_args()
    if not a.only_video:
        download_weights()
    if not a.no_video:
        download_videos()
    print("\nListo. Arranca el servidor con:  uvicorn backend.main:app --port 8010")


if __name__ == "__main__":
    sys.exit(main())
