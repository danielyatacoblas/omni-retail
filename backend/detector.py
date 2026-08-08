"""Detectores intercambiables → detecciones Supervision.

Backends (seleccionables en runtime desde la UI):
  - yolo      : Ultralytics YOLO11n — personas, rápido y estable (DEFAULT).
  - rfdetr    : RF-DETR nano (Roboflow) — personas, DETR, mejor en objetos chicos
                pero más lento (~20fps en 720p, ~8fps en 4K).
  - yoloworld : YOLO-World (open-vocabulary) — detecta OBJETOS comunes por nombre
                (botella, caja, lata…). Para contar productos en anaqueles.

person-detectors (yolo/rfdetr) devuelven solo personas.
yoloworld devuelve los objetos de config.world_classes (con class_name).
Todos aplican NMS class-agnostic (fusiona cajas dobles → menos IDs falsos).
"""
from __future__ import annotations

import os
from pathlib import Path

import supervision as sv

from .config import config

if config.device.lower() == "cpu":
    os.environ["CUDA_VISIBLE_DEVICES"] = ""

ROOT = Path(__file__).resolve().parent.parent
RFDETR_PERSON_ID = 1
YOLO_PERSON_ID = 0
_VARIANTS = {"nano", "small", "medium", "base", "large"}

KINDS = ("yolo", "rfdetr", "yoloworld")
LABELS = {
    "yolo": "YOLO11n · personas (rápido)",
    "rfdetr": "RF-DETR · personas (preciso)",
    "yoloworld": "YOLO-World · objetos (anaqueles)",
}


def _round_res(x: int, base: int = 32) -> int:
    x = max(base * 7, int(x))
    return int(round(x / base) * base)


def _nms(dets):
    if dets is not None and len(dets):
        try:
            return dets.with_nms(threshold=config.nms_iou, class_agnostic=True)
        except Exception:
            pass
    return dets


def _dev():
    import torch
    return 0 if (config.device.lower().startswith("cuda")
                 and torch.cuda.is_available()) else "cpu"


class Detector:
    def __init__(self, kind: str):
        self.kind = kind if kind in KINDS else "yolo"
        self.resolution = _round_res(config.work_res)
        self.object_mode = (self.kind == "yoloworld")
        self.classes = None
        if self.kind == "yolo":
            self._init_yolo()
        elif self.kind == "rfdetr":
            self._init_rfdetr()
        else:
            self._init_world()

    # ── YOLO personas ──
    def _init_yolo(self):
        from ultralytics import YOLO
        p = Path(config.yolo_model)
        if not p.is_absolute():
            p = ROOT / config.yolo_model
        self.model = YOLO(str(p) if p.exists() else config.yolo_model)
        self.device = _dev()
        self.variant = p.stem

    def _infer_yolo(self, frame, conf):
        r = self.model.predict(frame, conf=conf, classes=[YOLO_PERSON_ID],
                               device=self.device, imgsz=self.resolution,
                               verbose=False)[0]
        return _nms(sv.Detections.from_ultralytics(r))

    # ── YOLO-World objetos ──
    def _init_world(self):
        from ultralytics import YOLO
        mp = config.yolo_world_model
        p = Path(mp)
        if not p.exists() and not p.is_absolute():
            p = ROOT / mp
        self.model = YOLO(str(p) if p.exists() else "yolov8s-worldv2.pt")
        self.classes = list(config.world_classes)
        try:
            self.model.set_classes(self.classes)
        except Exception as e:
            print(f"[detector] YOLO-World set_classes falló: {e}")
        self.device = _dev()
        self.variant = "yolo-world"

    def _infer_world(self, frame, conf):
        r = self.model.predict(frame, conf=conf, device=self.device,
                               imgsz=self.resolution, verbose=False)[0]
        return _nms(sv.Detections.from_ultralytics(r))

    # ── RF-DETR personas ──
    def _init_rfdetr(self):
        import rfdetr as _rf
        variant = config.rfdetr_variant if config.rfdetr_variant in _VARIANTS else "nano"
        cls = {"nano": _rf.RFDETRNano, "small": _rf.RFDETRSmall,
               "medium": _rf.RFDETRMedium}.get(variant, _rf.RFDETRNano)
        try:
            self.model = cls(resolution=self.resolution)
        except TypeError:
            self.model = cls()
        self.variant = variant
        if config.optimize_inference:
            try:
                self.model.optimize_for_inference()
            except Exception as e:
                print(f"[detector] optimize_for_inference no disponible: {e}")

    def _infer_rfdetr(self, frame, conf):
        import cv2
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        dets = self.model.predict(rgb, threshold=conf)
        if dets is not None and len(dets):
            dets = dets[dets.class_id == RFDETR_PERSON_ID]
        return _nms(dets)

    # ── API común ──
    def infer(self, frame, conf: float):
        if self.kind == "yolo":
            return self._infer_yolo(frame, conf)
        if self.kind == "yoloworld":
            return self._infer_world(frame, conf)
        return self._infer_rfdetr(frame, conf)


# ── caché por tipo + estado de "warmed" ──
_cache: dict[str, Detector] = {}
_warmed: set[str] = set()


def get_detector(kind: str | None = None) -> Detector:
    kind = (kind or config.detector or "yolo").lower()
    if kind not in KINDS:
        kind = "yolo"
    if kind not in _cache:
        _cache[kind] = Detector(kind)
    return _cache[kind]


def mark_warmed(kind: str):
    _warmed.add(kind)


def is_warmed(kind: str | None = None) -> bool:
    kind = (kind or config.detector or "yolo").lower()
    return kind in _warmed
