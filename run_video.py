#!/usr/bin/env python3
"""CLI headless: procesa un video con RF-DETR + ByteTrack y genera MP4 anotado + CSV.

Usa las zonas/línea guardadas para ese video (dibújalas antes en el dashboard, o
corre solo detección+tracking si no hay ninguna).

Uso:
    python run_video.py videos/market-square.mp4
    python run_video.py videos/market-square.mp4 --conf 0.35 --out outputs
"""
from __future__ import annotations

import argparse
from pathlib import Path

from backend.processor import VideoProcessor


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    ap.add_argument("--conf", type=float, default=0.40)
    ap.add_argument("--out", type=Path, default=Path("outputs"))
    a = ap.parse_args()

    if not a.video.exists():
        print(f"ERROR: no existe {a.video}")
        return 1

    print(f"Procesando {a.video.name} (conf={a.conf}) ...")
    vp = VideoProcessor()
    res = vp.process_to_file(str(a.video), a.video.name, a.conf, a.out)
    print("\nRESUMEN")
    print(f"  IN {res['in']}  OUT {res['out']}  dentro {res['inside']}")
    print(f"  video: {res['video_out']}")
    print(f"  csv:   {res['csv']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
