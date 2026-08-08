"""Procesamiento de un video en hilo: RF-DETR + ByteTrack + analítica.

Lee el video una vez de principio a fin (archivo, no cámara), corre detección de
personas, las sigue con ByteTrack, dibuja cajas con ID, la línea de conteo y las
zonas, y publica el JPEG anotado (MJPEG) + un snapshot de estadísticas reales.
"""
from __future__ import annotations

import csv
import threading
import time
from pathlib import Path

import cv2
import numpy as np
import supervision as sv

from .analytics import Analytics, _fmt
from .config import config
from .detector import get_detector, mark_warmed
from .zones import line_to_px, load_config

GREEN = (80, 200, 80)
RED = (60, 60, 235)
BLUE = (235, 160, 40)
YELLOW = (40, 190, 235)
WHITE = (240, 240, 240)
DARK = (30, 30, 30)

_PALETTE = [(235, 130, 60), (80, 200, 80), (60, 170, 245), (70, 70, 235),
            (200, 120, 240), (235, 90, 190), (210, 200, 40)]


def _make_trace():
    """Estela de trayectoria por track (trazabilidad visual)."""
    try:
        return sv.TraceAnnotator(trace_length=28, thickness=2,
                                 color_lookup=sv.ColorLookup.TRACK)
    except Exception:
        return None


def _resize_max(frame, max_w):
    if max_w and frame.shape[1] > max_w:
        h, w = frame.shape[:2]
        return cv2.resize(frame, (max_w, int(h * max_w / w)))
    return frame


class VideoProcessor:
    def __init__(self):
        self.lock = threading.Lock()
        self.thread = None
        self.running = False
        self.finished = False
        self.latest_jpeg = None
        self.analytics: Analytics | None = None
        self.video = None
        self.cfg_data = None
        self.conf = config.default_conf
        self.progress = 0.0
        self.video_t = 0.0
        self.duration = 0.0
        self.proc_fps = 0.0
        self._line_px = None
        self._trace = None
        self.detector_kind = config.detector
        self.zone_only = False   # permanencia: rastrear solo a quienes están en zona

    # ── primer frame para el editor de zonas ──
    def first_frame_jpeg(self, video_path: str) -> bytes | None:
        cap = cv2.VideoCapture(video_path)
        ok, frame = cap.read()
        cap.release()
        if not ok:
            return None
        frame = _resize_max(frame, config.max_width)
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return buf.tobytes() if ok else None

    def video_meta(self, video_path: str) -> dict:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        return {"fps": round(fps, 2), "frames": n, "width": w, "height": h,
                "duration_sec": round(n / max(1.0, fps), 1)}

    # ── control ──
    def start(self, video_path: str, video_name: str, conf: float,
              detector_kind: str | None = None, zone_only: bool = False):
        self.stop()
        self.cfg_data = load_config(video_name)
        self.conf = float(conf)
        self.video = video_name
        self.detector_kind = (detector_kind or config.detector).lower()
        self.zone_only = bool(zone_only)
        self.finished = False
        self.progress = 0.0
        self.video_t = 0.0
        with self.lock:
            self.latest_jpeg = None
        self.running = True
        self.thread = threading.Thread(target=self._loop, args=(video_path,),
                                       daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        self.thread = None

    def _loop(self, video_path: str):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            self.running = False
            self.finished = True
            return

        src_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        self.duration = total / src_fps if total else 0.0

        # primer frame para dimensiones de procesamiento
        ok, frame = cap.read()
        if not ok:
            cap.release(); self.running = False; self.finished = True; return
        frame = _resize_max(frame, config.max_width)
        h, w = frame.shape[:2]

        detector = get_detector(self.detector_kind)
        tracker = sv.ByteTrack(
            track_activation_threshold=config.track_activation,
            lost_track_buffer=config.track_lost_buffer,
            minimum_matching_threshold=config.track_min_match,
            frame_rate=int(round(src_fps)),
        )
        self._trace = _make_trace()
        self.analytics = Analytics(self.cfg_data, w, h, src_fps,
                                   object_mode=detector.object_mode)
        self._line_px = line_to_px(self.cfg_data.get("line"), w, h)
        # modo objetos (YOLO-World): conf baja y sin filtro de área (productos chicos)
        obj = detector.object_mode
        eff_conf = config.world_conf if obj else self.conf
        min_area = 0.0 if obj else config.min_box_area_frac * w * h

        stride = max(1, config.frame_stride)
        dt = stride / src_fps
        frame_idx = 0
        t_wall = time.time()
        proc_count = 0
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # reiniciar tras leer el primero

        while self.running:
            ok = cap.grab()
            if not ok:
                break
            if frame_idx % stride != 0:
                frame_idx += 1
                continue
            ok, frame = cap.retrieve()
            if not ok:
                break
            frame = _resize_max(frame, config.max_width)

            dets = detector.infer(frame, eff_conf)
            dets = self._filter(dets, min_area)
            # objetos (anaquel): no se trackean, solo se cuentan por frame.
            # ByteTrack descartaría los objetos de baja confianza.
            if not obj:
                dets = tracker.update_with_detections(dets)

            self.video_t = frame_idx / src_fps
            self.analytics.update(dets, frame, self.video_t, dt)
            self._draw(frame, dets)
            mark_warmed(self.detector_kind)

            proc_count += 1
            elapsed = time.time() - t_wall
            self.proc_fps = proc_count / elapsed if elapsed > 0 else 0.0
            self.progress = (frame_idx / total) if total else 0.0

            ok, buf = cv2.imencode(".jpg", frame,
                                   [cv2.IMWRITE_JPEG_QUALITY, config.jpeg_quality])
            if ok:
                with self.lock:
                    self.latest_jpeg = buf.tobytes()
            frame_idx += 1

        cap.release()
        self.running = False
        self.finished = True
        self.progress = 1.0
        # exporta CSV automáticamente al terminar
        try:
            self.export_csv()
        except Exception as e:
            print(f"[processor] export CSV falló: {e}")

    def _filter(self, dets, min_area):
        if dets is None or len(dets) == 0:
            return dets
        xyxy = dets.xyxy
        areas = (xyxy[:, 2] - xyxy[:, 0]) * (xyxy[:, 3] - xyxy[:, 1])
        return dets[areas >= min_area]

    # ── dibujo ──
    def _draw(self, frame, dets):
        # zone_only (permanencia): dibujar/rastrear SOLO a quienes están en una zona
        if self.zone_only and self.analytics and self.analytics.zones \
                and dets is not None and len(dets) and dets.tracker_id is not None:
            inzone = self.analytics.person_zone
            keep = [i for i, t in enumerate(dets.tracker_id)
                    if t is not None and int(t) in inzone]
            dets = dets[keep]
        # zonas de permanencia
        for z in self.analytics.zones:
            self._draw_poly(frame, z["poly"], z["color"], z["name"],
                            len(z["present"]))
        # anaqueles
        for sh in self.analytics.shelves:
            col = self._hex(sh["color"])
            self._draw_poly(frame, sh["poly"], sh["color"],
                            f"{sh['name']} {sh['fill']:.0f}%", None)
        # línea de conteo
        if self._line_px:
            (ax, ay), (bx, by) = self._line_px
            cv2.line(frame, (int(ax), int(ay)), (int(bx), int(by)), RED, 3)
            cv2.putText(frame, f"IN {self.analytics.total_in}  OUT {self.analytics.total_out}",
                        (int(ax), int(ay) - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        RED, 2, cv2.LINE_AA)
        # estela de trayectoria (trazabilidad)
        if self._trace is not None and dets is not None and len(dets) \
                and dets.tracker_id is not None:
            try:
                self._trace.annotate(frame, dets)
            except Exception:
                pass
        # detecciones con ID + estado (visitante/dentro) o nombre de objeto
        pstate = self.analytics.person_state if self.analytics else {}
        cls_names = None
        if dets is not None and len(dets) and dets.data is not None:
            cls_names = dets.data.get("class_name")
        if dets is not None and len(dets):
            tids = dets.tracker_id if dets.tracker_id is not None else [None] * len(dets)
            for i, (box, tid) in enumerate(zip(dets.xyxy, tids)):
                x1, y1, x2, y2 = map(int, box)
                state = pstate.get(int(tid)) if tid is not None else None
                if state == "entrante":
                    col = GREEN
                elif state == "visitante":
                    col = YELLOW
                else:
                    col = _PALETTE[(int(tid) if tid is not None else 0) % len(_PALETTE)]
                cv2.rectangle(frame, (x1, y1), (x2, y2), col, 2)
                sfx = {"entrante": " ENTRANTE", "visitante": " visita"}.get(state, "")
                if tid is not None:
                    lbl = f"ID {int(tid)}{sfx}"
                elif cls_names is not None:
                    lbl = str(cls_names[i])       # nombre del objeto (YOLO-World)
                else:
                    lbl = "persona"
                (tw, th), _ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 6, y1), col, -1)
                cv2.putText(frame, lbl, (x1 + 3, y1 - 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, WHITE, 1, cv2.LINE_AA)
                # temporizador de permanencia en zona (⏱ Ns) sobre la persona
                if tid is not None:
                    pz = self.analytics.person_zone.get(int(tid))
                    if pz:
                        ztxt = f"{pz[0]}: {_fmt(pz[1])}"
                        (zw, zh), _ = cv2.getTextSize(ztxt, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                        yb = y2 + zh + 6
                        cv2.rectangle(frame, (x1, y2 + 2), (x1 + zw + 8, yb + 4), (25, 25, 25), -1)
                        cv2.putText(frame, ztxt, (x1 + 4, yb),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (120, 235, 120), 2, cv2.LINE_AA)
        # HUD
        hud = f"t {_fmt(self.video_t)} / {_fmt(self.duration)}   dentro: {self.analytics.inside}   {self.proc_fps:.1f} fps"
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 26), DARK, -1)
        cv2.putText(frame, hud, (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (120, 230, 120), 1, cv2.LINE_AA)

    def _draw_poly(self, frame, poly, hexcol, label, count):
        col = self._hex(hexcol)
        overlay = frame.copy()
        cv2.fillPoly(overlay, [poly], col)
        cv2.addWeighted(overlay, 0.18, frame, 0.82, 0, frame)
        cv2.polylines(frame, [poly], True, col, 2)
        p0 = poly[0]
        txt = f"{label}" + (f"  [{count}]" if count is not None else "")
        cv2.putText(frame, txt, (int(p0[0]), int(p0[1]) - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 2, cv2.LINE_AA)

    @staticmethod
    def _hex(h):
        h = h.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return (b, g, r)

    # ── salidas ──
    def mjpeg_frames(self):
        while True:
            with self.lock:
                data = self.latest_jpeg
            if data is None:
                time.sleep(0.03)
                continue
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + data + b"\r\n")
            time.sleep(0.04)

    def status(self) -> dict:
        from . import detector as _det
        base = {
            "running": self.running, "finished": self.finished,
            "video": self.video, "progress": round(self.progress, 4),
            "video_time": _fmt(self.video_t), "duration": _fmt(self.duration),
            "proc_fps": round(self.proc_fps, 1),
            "store_capacity": config.store_capacity,
            "has_frame": self.latest_jpeg is not None,
            "model_ready": _det.is_warmed(self.detector_kind),
            "detector": self.detector_kind,
        }
        if self.analytics:
            base.update(self.analytics.snapshot())
        return base

    def process_to_file(self, video_path: str, video_name: str, conf: float,
                        out_dir: Path, log=print) -> dict:
        """Modo headless (CLI): procesa el video completo, escribe un MP4
        anotado y el CSV. No usa hilo ni streaming. Devuelve resumen."""
        self.cfg_data = load_config(video_name)
        self.conf = float(conf)
        self.video = video_name

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"no se pudo abrir {video_path}")
        src_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        self.duration = total / src_fps if total else 0.0

        ok, frame = cap.read()
        if not ok:
            raise RuntimeError("video vacío")
        frame = _resize_max(frame, config.max_width)
        h, w = frame.shape[:2]

        detector = get_detector(self.detector_kind)
        tracker = sv.ByteTrack(
            track_activation_threshold=config.track_activation,
            lost_track_buffer=config.track_lost_buffer,
            minimum_matching_threshold=config.track_min_match,
            frame_rate=int(round(src_fps)))
        self._trace = _make_trace()
        self.analytics = Analytics(self.cfg_data, w, h, src_fps,
                                   object_mode=detector.object_mode)
        self._line_px = line_to_px(self.cfg_data.get("line"), w, h)
        min_area = config.min_box_area_frac * w * h

        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{Path(video_name).stem}_omni.mp4"
        writer = cv2.VideoWriter(str(out_file),
                                 cv2.VideoWriter_fourcc(*"mp4v"), src_fps, (w, h))

        obj = detector.object_mode
        eff_conf = config.world_conf if obj else self.conf
        if obj:
            min_area = 0.0
        stride = max(1, config.frame_stride)
        dt = stride / src_fps
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        frame_idx = 0
        t0 = time.time()
        while True:
            ok = cap.grab()
            if not ok:
                break
            if frame_idx % stride != 0:
                frame_idx += 1
                continue
            ok, frame = cap.retrieve()
            if not ok:
                break
            frame = _resize_max(frame, config.max_width)
            dets = detector.infer(frame, eff_conf)
            dets = self._filter(dets, min_area)
            if not obj:
                dets = tracker.update_with_detections(dets)
            self.video_t = frame_idx / src_fps
            self.analytics.update(dets, frame, self.video_t, dt)
            self._draw(frame, dets)
            writer.write(frame)
            if frame_idx % 50 == 0 and total:
                log(f"  frame {frame_idx}/{total} "
                    f"({100*frame_idx/total:.0f}%)  IN {self.analytics.total_in} "
                    f"OUT {self.analytics.total_out}")
            frame_idx += 1
        cap.release()
        writer.release()
        csv_path = self.export_csv()
        snap = self.analytics.snapshot()
        log(f"  ✓ {out_file.name} ({out_file.stat().st_size/1e6:.1f} MB)  "
            f"en {time.time()-t0:.1f}s")
        return {"video_out": str(out_file), "csv": str(csv_path),
                "in": snap["total_in"], "out": snap["total_out"],
                "inside": snap["inside"]}

    def export_csv(self) -> Path:
        """Exporta a CSV los datos REALES: resumen, permanencia, anaqueles, alertas."""
        if not self.analytics:
            raise RuntimeError("no hay analítica para exportar")
        snap = self.analytics.snapshot()
        out = config.data_abs / f"reporte_{Path(self.video).stem}.csv"
        with out.open("w", newline="", encoding="utf-8") as f:
            wr = csv.writer(f)
            wr.writerow(["OMNI Retail — Reporte", self.video])
            wr.writerow([])
            wr.writerow(["RESUMEN"])
            wr.writerow(["Ingresos (IN)", snap["total_in"]])
            wr.writerow(["Salidas (OUT)", snap["total_out"]])
            wr.writerow(["Dentro (final)", snap["inside"]])
            wr.writerow(["Pico simultáneo", snap["peak_inside"]])
            wr.writerow(["Permanencia promedio", snap["avg_dwell"]])
            wr.writerow([])
            wr.writerow(["PERMANENCIA POR ZONA"])
            wr.writerow(["Zona", "Visitantes", "Prom.", "Máx.", "Presentes(fin)"])
            for z in snap["zones"]:
                wr.writerow([z["name"], z["visitors"], z["avg"], z["max"],
                             z["people_now"]])
            wr.writerow([])
            wr.writerow(["NIVEL DE ANAQUELES"])
            wr.writerow(["Anaquel", "Nivel %", "Estado"])
            for s in snap["shelves"]:
                wr.writerow([s["name"], f"{s['fill']:.0f}", s["status"]])
            wr.writerow([])
            wr.writerow(["ALERTAS"])
            wr.writerow(["Tiempo video", "Módulo", "Tipo", "Detalle", "Severidad"])
            for a in snap["alerts"]:
                wr.writerow([a["video_time"], a["modulo"], a["tipo"],
                             a["detalle"], a["severity"]])
        return out


processor = VideoProcessor()
