# -*- coding: utf-8 -*-
"""Mide los modelos de verdad y escribe la tabla del README.

    python scripts/medir_modelos.py

Deja `docs/modelos.json` con lo medido y sustituye el bloque marcado con
`<!-- MODELOS:inicio -->` … `<!-- MODELOS:fin -->`.

**Qué se mide y qué se cita, que no es lo mismo.**

Las métricas de acierto (precisión, recall, mAP50, mAP50-95) NO se calculan
aquí: salen del propio archivo `.pt`, donde Ultralytics guarda el resultado de
la validación del entrenamiento que produjo esos pesos. Son las cifras que
midió quien entrenó el modelo, sobre *su* conjunto de validación.

Eso hay que decirlo claro: **no son el acierto sobre los videos de este
proyecto**. Medirlo aquí exigiría un conjunto etiquetado a mano de esta
operación concreta, que es precisamente el trabajo que un MVP todavía no ha
hecho. Inventar un porcentaje sería peor que no darlo.

Lo que sí se mide aquí, en esta máquina y sobre los videos reales del
repositorio: latencia por fotograma, fotogramas por segundo, detecciones por
fotograma al umbral configurado y confianza media. Eso decide si el sistema
sirve en vivo, que es la otra mitad de la pregunta.

Comprobación de que la extracción es correcta: `yolo11n` sale con
mAP50-95 = 0.394, y Ultralytics publica 39.5 para ese mismo modelo en COCO.
"""
from __future__ import annotations

import json
import statistics
import sys
import time
import types
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

RAIZ = Path(__file__).resolve().parents[1]
DOCS = RAIZ / "docs"
INICIO, FIN = "<!-- MODELOS:inicio -->", "<!-- MODELOS:fin -->"

FOTOGRAMAS = 60      # suficientes para una mediana estable sin tardar un minuto
# Una GPU de portátil está a 210 MHz en reposo y tarda unos 20 fotogramas en
# subir de reloj: medida ahí, la mediana sale un 50 % peor que la real. Ocho
# fotogramas de calentamiento no bastaban, y esa era toda la diferencia entre
# 53 ms y 35 ms para el mismo modelo.
CALENTAR = 20

# (archivo, rol en el sistema, video con el que se mide, umbral)
MODELOS = [
    ("weights/yolo11n.pt", "Personas — detector por defecto",
     "videos/entradas.mp4", 0.40),
    ("weights/yolov8s-world.pt", "Objetos de anaquel (vocabulario abierto)",
     "videos/_anaqueles.mp4", 0.05),
]

# Lo que publica quien entrenó cada modelo, para lo que el .pt no trae.
FUENTES = {
    "yolo11n.pt": ("Ultralytics · COCO 2017",
     "https://docs.ultralytics.com/models/yolo11/"),
    "yolov8s-world.pt": ("Ultralytics YOLO-World",
     "https://docs.ultralytics.com/models/yolo-world/"),
}


def _parchear_pickles_viejos() -> None:
    """Los pesos de ultralytics 8.0 apuntan a `ultralytics.yolo.*`.

    Ese árbol se renombró a `ultralytics.*` sin más. Sin esto, cualquier peso
    de terceros de aquella época falla al abrirse con un ImportError que no
    dice nada de lo que pasa de verdad.

    No basta con meter los alias en `sys.modules`: hay que colgarlos también
    como atributos del módulo padre, porque el desempaquetado resuelve
    `ultralytics.yolo.utils` importando el padre y buscando el hijo dentro.
    """
    # No se sale si ya está: `ultralytics.nn.tasks.torch_safe_load` instala sus
    # propios alias temporales y los BORRA al terminar, y con ellos se lleva
    # estos. Por eso hay que reinstalarlos antes de cada lectura, no una vez.
    import ultralytics.data
    import ultralytics.engine
    import ultralytics.nn
    import ultralytics.nn.tasks
    import ultralytics.utils
    import ultralytics.utils.loss

    viejo = types.ModuleType("ultralytics.yolo")
    viejo.__path__ = []          # sin esto no cuenta como paquete
    sys.modules["ultralytics.yolo"] = viejo
    for corto, mod in (("utils", ultralytics.utils), ("nn", ultralytics.nn),
                       ("data", ultralytics.data),
                       ("engine", ultralytics.engine)):
        sys.modules[f"ultralytics.yolo.{corto}"] = mod
        setattr(viejo, corto, mod)
    sys.modules["ultralytics.yolo.utils.loss"] = ultralytics.utils.loss
    sys.modules["ultralytics.yolo.nn.tasks"] = ultralytics.nn.tasks


def metadatos(ruta: Path) -> dict:
    """Lo que el propio checkpoint sabe de sí mismo."""
    import torch
    _parchear_pickles_viejos()
    ck = torch.load(ruta, map_location="cpu", weights_only=False)
    ta = ck.get("train_args") or {}
    tm = ck.get("train_metrics") or {}
    met = {}
    for k, v in tm.items():
        nombre = k.split("/")[-1].replace("(B)", "")
        if nombre in ("precision", "recall", "mAP50", "mAP50-95"):
            met[nombre] = round(float(v), 4)
    datos = str(ta.get("data") or "")
    return {
        "imgsz": ta.get("imgsz"),
        "epochs": ta.get("epochs"),
        "dataset": Path(datos).stem if datos else None,
        "licencia": ck.get("license"),
        "metricas": met,
    }


def medir(ruta: Path, video: Path, conf: float) -> dict:
    """Latencia y detecciones sobre fotogramas reales de este repositorio.

    Se mide a la resolución que usa la aplicación de verdad (`WORK_RES`), no a
    la del video: medir a 1080p daría una cifra peor que la real y no
    representaría a nada de lo que ocurre en producción.
    """
    import cv2
    from ultralytics import YOLO

    try:
        from backend.config import config
        res = int(getattr(config, "work_res", 640))
        disp = getattr(config, "device", "cuda")
    except Exception:
        res, disp = 640, "cuda"
    # Sin fijar el dispositivo, la medición sale de CPU aunque haya GPU, y la
    # cifra que acaba en el README no es la del sistema que se está midiendo.
    import torch
    if disp.startswith("cuda") and not torch.cuda.is_available():
        disp = "cpu"
    modelo = YOLO(str(ruta))
    modelo.to(disp)
    params = sum(p.numel() for p in modelo.model.parameters())
    clases = list(modelo.names.values())

    salida = {"parametros": params, "clases": len(clases),
              "nombres": clases[:8], "video": None, "res": res, "dispositivo": disp,
              "ms": None, "fps": None, "dets": None, "conf_media": None}
    if not video.exists():
        return salida

    cap = cv2.VideoCapture(str(video))
    frames = []
    while len(frames) < FOTOGRAMAS + CALENTAR:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    cap.release()
    if not frames:
        return salida

    for f in frames[:CALENTAR]:
        modelo.predict(f, conf=conf, imgsz=res, device=disp, verbose=False)

    tiempos, dets, confs = [], [], []
    for f in frames[CALENTAR:]:
        t0 = time.perf_counter()
        r = modelo.predict(f, conf=conf, imgsz=res, device=disp, verbose=False)[0]
        if disp.startswith("cuda"):
            torch.cuda.synchronize()   # si no, se cronometra el encolado
        tiempos.append((time.perf_counter() - t0) * 1000)
        dets.append(len(r.boxes))
        if len(r.boxes):
            confs += [float(c) for c in r.boxes.conf]

    salida.update({
        "video": video.name, "res": res, "dispositivo": disp,
        "ms": round(statistics.median(tiempos), 1),
        "fps": round(1000 / statistics.median(tiempos), 1),
        "mejor_ms": round(min(tiempos), 1),
        "dets": round(statistics.mean(dets), 1),
        "conf_media": round(statistics.mean(confs), 3) if confs else None,
    })
    return salida


def tabla(filas: list) -> str:
    def pct(v):
        return f"{v * 100:.1f} %" if isinstance(v, (int, float)) else "—"

    out = [
        "### Los modelos, medidos",
        "",
        "| Modelo | Para qué | Entrada | Precisión | Recall | mAP@50 | mAP@50-95 |",
        "|---|---|---|---|---|---|---|",
    ]
    for f in filas:
        m = f["metricas"]
        entrada = f"{f['imgsz']}²" if f.get("imgsz") else "—"
        out.append(
            f"| **`{f['archivo']}`** | {f['rol']} | {entrada} "
            f"| {pct(m.get('precision'))} | {pct(m.get('recall'))} "
            f"| {pct(m.get('mAP50'))} | {pct(m.get('mAP50-95'))} |")

    out += [
        "",
        "<sub>Estas cuatro columnas **no** se calculan aquí: salen del propio "
        "archivo `.pt`, donde Ultralytics guarda la validación del "
        "entrenamiento que produjo esos pesos. Son el acierto sobre el "
        "conjunto de validación de quien lo entrenó, **no** sobre los videos "
        "de este proyecto. Medir eso exigiría etiquetar a mano esta operación "
        "concreta, que es trabajo que un MVP todavía no ha hecho; dar un "
        "porcentaje inventado sería peor que no darlo. "
        "Comprobación de que la lectura es correcta: `yolo11n` sale con "
        "mAP@50-95 = 39,4 % y Ultralytics publica 39,5 % para ese modelo en "
        "COCO.</sub>",
        "",
        "### De dónde sale cada modelo",
        "",
        "| Modelo | Entrenado sobre | Épocas | Resolución | Origen |",
        "|---|---|---|---|---|",
    ]
    for f in filas:
        d = f.get("dataset") or "—"
        ep = f.get("epochs") or "—"
        im = f"{f['imgsz']}×{f['imgsz']}" if f.get("imgsz") else "—"
        fu = f.get("fuente")
        if fu and fu[1]:
            org = f"[{fu[0]}]({fu[1]})"
        elif fu:
            org = fu[0]
        else:
            org = "—"
        out.append(f"| **`{f['archivo']}`** | `{d}` | {ep} | {im} | {org} |")

    out += [
        "",
        "<sub>El conjunto, las épocas y la resolución salen de `train_args`, "
        "que Ultralytics guarda dentro del propio `.pt`. Es decir: no es lo "
        "que dice la documentación del modelo, es lo que quedó grabado en el "
        "archivo que este repositorio usa de verdad. Los nombres de conjunto "
        "son los del disco de quien entrenó —`retrain_data`, `safe_human`— "
        "porque es literalmente lo que hay dentro.</sub>",
        "",
        "| Modelo | Parámetros | Clases | Latencia (mejor) | Latencia (mediana) "
        "| Det./fotograma | Confianza media |",
        "|---|---|---|---|---|---|---|",
    ]
    for f in filas:
        mej = (f"{f['mejor_ms']} ms · {1000 / f['mejor_ms']:.0f} fps"
               if f.get("mejor_ms") else "—")
        med = (f"{f['ms']} ms · {f['fps']} fps" if f.get("ms") else "—")
        det = f"{f['dets']}" if f.get("dets") is not None else "—"
        cm = f"{f['conf_media']}" if f.get("conf_media") else "—"
        par = f"{f['parametros'] / 1e6:.1f} M" if f.get("parametros") else "—"
        out.append(f"| **`{f['archivo']}`** | {par} | {f['clases']} "
                   f"| {mej} | {med} | {det} | {cm} |")

    out += [
        "",
        "<sub>Esto sí se mide aquí, con "
        "<a href=\"scripts/medir_modelos.py\"><code>scripts/medir_modelos.py"
        "</code></a>, sobre fotogramas reales de los videos del repositorio, "
        "en una RTX 3060 Laptop y a la resolución que usa la aplicación. "
        "Sesenta fotogramas, descartando los veinte primeros.<br>"
        "Se dan <b>dos</b> latencias a propósito. Esta GPU está a 210 MHz en "
        "reposo y tarda segundos en subir de reloj, así que la mediana se "
        "mueve bastante entre pasadas —el mismo <code>yolo11n</code> ha dado "
        "20 y 48 fps— mientras que el mejor caso es estable y representa lo "
        "que la máquina puede sostener. Dar solo la cifra buena sería vender "
        "de más; dar solo la mediana, castigar al modelo por la gestión de "
        "energía del portátil.</sub>",
        "",
    ]
    return "\n".join(out)


def main() -> int:
    _parchear_pickles_viejos()
    DOCS.mkdir(parents=True, exist_ok=True)
    filas = []
    for archivo, rol, video, conf in MODELOS:
        ruta = RAIZ / archivo
        if not ruta.exists():
            print(f"  {archivo}: no está — corre download_models.py")
            continue
        fila = {"archivo": Path(archivo).name, "rol": rol, "umbral": conf}
        fila.update(metadatos(ruta))
        fila.update(medir(ruta, RAIZ / video, conf))
        fila["fuente"] = FUENTES.get(fila["archivo"])
        filas.append(fila)
        print(f"  {fila['archivo']:<24} {fila.get('fps') or '—'} fps · "
              f"mAP50 {fila['metricas'].get('mAP50', '—')}")

    if not filas:
        print("  No hay ningún modelo que medir.")
        return 1

    (DOCS / "modelos.json").write_text(
        json.dumps(filas, indent=2, ensure_ascii=False), encoding="utf-8")

    import re
    readme = RAIZ / "README.md"
    texto = readme.read_text(encoding="utf-8")
    nuevo = f"{INICIO}\n\n{tabla(filas)}\n{FIN}"
    if INICIO in texto:
        texto = re.sub(re.escape(INICIO) + r".*?" + re.escape(FIN),
                       lambda _: nuevo, texto, flags=re.S)
        readme.write_text(texto, encoding="utf-8", newline="\n")
    else:
        print("  (el README no tiene el bloque MODELOS; solo se escribió el JSON)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
