"""Analítica real por video: conteo de línea, permanencia por zona y anaquel.

Todo se calcula sobre el *tiempo del video* (frame / fps), no sobre el reloj de
pared, para que la permanencia sea correcta aunque el procesamiento sea más
lento o rápido que tiempo real.

- Conteo:      supervision.LineZone (cruces in/out con dirección).
- Permanencia: supervision.PolygonZone + acumulador de segundos por track_id.
- Anaquel:     densidad de bordes (Canny) del ROI vs. la del primer frame
               (heurística de "llenado"; documentada como experimental).
"""
from __future__ import annotations

import cv2
import numpy as np
import supervision as sv

from .config import config
from .zones import line_to_px, zone_to_px


def _build_polygon_zone(polygon: np.ndarray, w: int, h: int) -> sv.PolygonZone:
    """Construye PolygonZone compatible entre versiones de supervision."""
    anchor = getattr(sv.Position, "BOTTOM_CENTER", None)
    for kwargs in (
        {"triggering_anchors": (anchor,)} if anchor else {},
        {},
    ):
        try:
            return sv.PolygonZone(polygon=polygon, **kwargs)
        except TypeError:
            continue
    # versiones viejas exigían frame_resolution_wh
    return sv.PolygonZone(polygon=polygon, frame_resolution_wh=(w, h))


class Analytics:
    def __init__(self, cfg_data: dict, w: int, h: int, fps: float,
                 object_mode: bool = False):
        self.w, self.h, self.fps = w, h, max(1.0, fps)
        self.object_mode = object_mode   # True con YOLO-World: cuenta objetos

        # ── línea de conteo ──
        self.line_zone = None
        lp = line_to_px(cfg_data.get("line"), w, h)
        if lp:
            (ax, ay), (bx, by) = lp
            # anchor en los PIES (BOTTOM_CENTER): una persona cuenta al cruzar con
            # los pies. Con el default (4 esquinas) casi nunca cruzan todas → IN/OUT=0.
            try:
                self.line_zone = sv.LineZone(
                    start=sv.Point(ax, ay), end=sv.Point(bx, by),
                    triggering_anchors=[sv.Position.BOTTOM_CENTER],
                    minimum_crossing_threshold=config.line_cross_min)
            except TypeError:
                self.line_zone = sv.LineZone(
                    start=sv.Point(ax, ay), end=sv.Point(bx, by))

        # ── zonas ──
        self.zones = []        # permanencia
        self.shelves = []      # anaquel
        for z in cfg_data.get("zones", []):
            poly = zone_to_px(z, w, h)
            if len(poly) < 3:
                continue
            entry = {"id": z.get("id"), "name": z.get("name", "Zona"),
                     "color": z.get("color", "#3B82F6"), "poly": poly}
            if z.get("type") == "anaquel":
                entry["mask"] = self._poly_mask(poly)
                entry["baseline"] = None
                entry["fill"] = 100.0
                entry["count"] = 0        # objetos detectados ahora (YOLO-World)
                entry["expected"] = 0     # máximo visto = "anaquel lleno"
                self.shelves.append(entry)
            else:
                entry["pz"] = _build_polygon_zone(poly, w, h)
                entry["dwell"] = {}      # tid -> segundos acumulados
                entry["present"] = set()  # tids dentro ahora
                self.shelves  # noqa
                self.zones.append(entry)

        # estado de conteo/tiempo
        self.people = {}             # tid -> {first, last}  (trazabilidad)
        self.person_state = {}       # tid -> 'visitante' | 'entrante' (si hay línea)
        self.person_zone = {}        # tid -> (zona, segundos) temporizador en zona
        self.cur_t = 0.0
        self.timeline = []           # [{t, ins, outs, inside}] muestreado c/1s
        self._last_sample_sec = -1
        self.inside = 0              # ins - outs
        self.total_in = 0
        self.total_out = 0
        self.alerts = []             # alertas reales generadas
        self._dwell_alerted = set()  # (zone_id, tid) ya alertados
        self._shelf_state = {}       # zone_id -> "ok|warning|critical"
        self._capacity_alerted = False
        self.peak_inside = 0

    # ── helpers ──
    def _poly_mask(self, poly: np.ndarray) -> np.ndarray:
        m = np.zeros((self.h, self.w), dtype=np.uint8)
        cv2.fillPoly(m, [poly], 255)
        return m

    def _add_alert(self, t: float, modulo: str, tipo: str, detalle: str,
                   severity: str):
        self.alerts.append({
            "t": round(t, 1),
            "video_time": _fmt(t),
            "modulo": modulo, "tipo": tipo, "detalle": detalle,
            "severity": severity,
        })

    # ── actualización por frame ──
    def update(self, detections, frame_bgr, video_t: float, dt: float):
        self.cur_t = video_t
        # TRAZABILIDAD: registra primera/última vez que se ve cada track
        if detections is not None and len(detections) and detections.tracker_id is not None:
            for tid in detections.tracker_id:
                if tid is None:
                    continue
                tid = int(tid)
                p = self.people.get(tid)
                if p is None:
                    self.people[tid] = {"first": video_t, "last": video_t}
                    if self.line_zone is not None:
                        # aún no cruza → persona_visitante
                        self.person_state.setdefault(tid, "visitante")
                else:
                    p["last"] = video_t

        # LÍNEA — conteo + estado visitante/dentro por cruce
        if self.line_zone is not None and detections is not None and len(detections):
            crossed_in, crossed_out = self.line_zone.trigger(detections)
            tids = detections.tracker_id
            if tids is not None:
                for ci, co, tid in zip(crossed_in, crossed_out, tids):
                    if tid is None:
                        continue
                    tid = int(tid)
                    # cruzó la línea (en cualquier dirección) → pasa a ENTRANTE
                    if ci or co:
                        self.person_state[tid] = "entrante"
            self.total_in = int(self.line_zone.in_count)
            self.total_out = int(self.line_zone.out_count)
            self.inside = max(0, self.total_in - self.total_out)
            if self.inside > self.peak_inside:
                self.peak_inside = self.inside

        # PERMANENCIA
        self.person_zone = {}   # tid -> (zona, segundos) para el temporizador por persona
        for z in self.zones:
            present_now = set()
            if detections is not None and len(detections):
                mask = z["pz"].trigger(detections)
                tids = detections.tracker_id
                if tids is not None:
                    for inside_flag, tid in zip(mask, tids):
                        if inside_flag and tid is not None:
                            tid = int(tid)
                            present_now.add(tid)
                            z["dwell"][tid] = z["dwell"].get(tid, 0.0) + dt
                            self.person_zone[tid] = (z["name"], z["dwell"][tid])
                            if (z["dwell"][tid] >= config.dwell_alert_sec
                                    and (z["id"], tid) not in self._dwell_alerted):
                                self._dwell_alerted.add((z["id"], tid))
                                self._add_alert(
                                    video_t, "Permanencia", "Permanencia excesiva",
                                    f"{z['name']} — ID {tid} lleva {_fmt(z['dwell'][tid])}"
                                    f" (máx. {_fmt(config.dwell_alert_sec)})", "warning")
            z["present"] = present_now

        # ANAQUEL
        if self.object_mode and self.shelves:
            # YOLO-World: cuenta objetos reales dentro de cada anaquel
            centers = []
            if detections is not None and len(detections):
                for box in detections.xyxy:
                    centers.append(((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0))
            for sh in self.shelves:
                cnt = sum(1 for cx, cy in centers
                          if cv2.pointPolygonTest(sh["poly"], (float(cx), float(cy)), False) >= 0)
                # suaviza el conteo (evita parpadeo por detección intermitente)
                sh["count"] = int(round(0.6 * sh["count"] + 0.4 * cnt))
                sh["expected"] = max(sh["expected"], sh["count"])
                exp = max(1, sh["expected"])
                sh["fill"] = max(0.0, min(100.0, 100.0 * sh["count"] / exp))
                self._eval_shelf(sh, video_t)
        elif self.shelves:
            # heurística de llenado por densidad de bordes (sin YOLO-World)
            edges = cv2.Canny(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY), 60, 160)
            for sh in self.shelves:
                roi = cv2.bitwise_and(edges, edges, mask=sh["mask"])
                area = max(1, int(np.count_nonzero(sh["mask"])))
                density = float(np.count_nonzero(roi)) / area
                if sh["baseline"] is None:
                    sh["baseline"] = max(density, 1e-4)
                fill = max(0.0, min(100.0, 100.0 * density / sh["baseline"]))
                sh["fill"] = 0.8 * sh["fill"] + 0.2 * fill
                self._eval_shelf(sh, video_t)

        # AFORO
        if self.inside > config.store_capacity and not self._capacity_alerted:
            self._capacity_alerted = True
            self._add_alert(video_t, "Conteo", "Aforo excedido",
                            f"{self.inside} personas dentro (aforo {config.store_capacity})",
                            "critical")
        elif self.inside <= config.store_capacity:
            self._capacity_alerted = False

        # timeline (1 muestra por segundo de video)
        sec = int(video_t)
        if sec != self._last_sample_sec:
            self._last_sample_sec = sec
            self.timeline.append({"t": sec, "ins": self.total_in,
                                  "outs": self.total_out, "inside": self.inside})

    def _eval_shelf(self, sh, video_t):
        fill = sh["fill"]
        if fill < config.shelf_critical_pct:
            state = "critical"
        elif fill < config.shelf_alert_pct:
            state = "warning"
        else:
            state = "ok"
        prev = self._shelf_state.get(sh["id"])
        if state != prev and state in ("warning", "critical"):
            self._add_alert(
                video_t, "Anaqueles",
                "Anaquel crítico" if state == "critical" else "Anaquel bajo",
                f"{sh['name']} al {fill:.0f}%", state)
        self._shelf_state[sh["id"]] = state

    # ── snapshot para el dashboard ──
    def snapshot(self) -> dict:
        zones_out = []
        for z in self.zones:
            secs = list(z["dwell"].values())
            zones_out.append({
                "id": z["id"], "name": z["name"], "color": z["color"],
                "people_now": len(z["present"]),
                "visitors": len(z["dwell"]),
                "avg_sec": round(sum(secs) / len(secs), 1) if secs else 0.0,
                "max_sec": round(max(secs), 1) if secs else 0.0,
                "avg": _fmt(sum(secs) / len(secs)) if secs else "0s",
                "max": _fmt(max(secs)) if secs else "0s",
            })
        shelves_out = [{
            "id": sh["id"], "name": sh["name"], "color": sh["color"],
            "fill": round(sh["fill"], 1),
            "status": self._shelf_state.get(sh["id"], "ok"),
            "count": sh.get("count", 0),
            "expected": sh.get("expected", 0),
            "missing": max(0, sh.get("expected", 0) - sh.get("count", 0)),
            "mode": "objetos" if self.object_mode else "bordes",
        } for sh in self.shelves]

        all_dwell = [s for z in self.zones for s in z["dwell"].values()]
        avg_dwell = sum(all_dwell) / len(all_dwell) if all_dwell else 0.0

        # personas activas (vistas en el último ~segundo) para el visor/trazabilidad
        active = []
        for tid, p in self.people.items():
            if self.cur_t - p["last"] > 1.0:
                continue
            zname = next((z["name"] for z in self.zones if tid in z["present"]), None)
            total = sum(z["dwell"].get(tid, 0.0) for z in self.zones)
            active.append({"id": tid, "zone": zname,
                           "state": self.person_state.get(tid),
                           "dwell_sec": round(total, 1), "dwell": _fmt(total),
                           "seen": _fmt(p["last"] - p["first"])})
        active.sort(key=lambda x: -x["dwell_sec"])
        dentro_now = sum(1 for a in active if a["state"] == "entrante")
        entered_total = sum(1 for s in self.person_state.values() if s == "entrante")

        return {
            "active_people": active[:40],
            "active_count": len(active),
            "dentro_now": dentro_now,
            "entered_total": entered_total,
            "unique_people": len(self.people),
            "line_enabled": self.line_zone is not None,
            "total_in": self.total_in,
            "total_out": self.total_out,
            "inside": self.inside,
            "peak_inside": self.peak_inside,
            "avg_dwell": _fmt(avg_dwell),
            "avg_dwell_sec": round(avg_dwell, 1),
            "zones": zones_out,
            "shelves": shelves_out,
            "shelf_alerts": sum(1 for s in shelves_out if s["status"] != "ok"),
            "timeline": self.timeline[-600:],
            "alerts": self.alerts[-100:],
        }


def _fmt(sec: float) -> str:
    sec = int(round(sec))
    m, s = divmod(sec, 60)
    if m >= 60:
        h, m = divmod(m, 60)
        return f"{h}h {m:02d}m"
    return f"{m}m {s:02d}s" if m else f"{s}s"
