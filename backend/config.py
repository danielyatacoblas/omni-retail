"""Carga de configuración desde .env — OMNI Retail (tracking)."""
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _f(key, default):
    return float(os.getenv(key, default))


def _i(key, default):
    return int(os.getenv(key, default))


def _b(key, default):
    return os.getenv(key, str(default)).strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Config:
    # modelo
    detector: str = os.getenv("DETECTOR", "yolo").lower()   # yolo | rfdetr | yoloworld
    yolo_model: str = os.getenv("YOLO_MODEL", "weights/yolo11n.pt")
    yolo_world_model: str = os.getenv(
        "YOLO_WORLD_MODEL",
        r"C:/Users/USER/Desktop/ACCESORIO/Pixel-Civik/vision-node/server/shoplifting/yolov8s-world.pt")
    # clases open-vocabulary para YOLO-World (objetos comunes de retail); editable
    world_classes: list = field(default_factory=lambda: [
        c.strip() for c in os.getenv(
            "WORLD_CLASSES",
            "bottle,cup,box,can,carton,bag,jar,snack,product").split(",") if c.strip()])
    rfdetr_variant: str = os.getenv("RFDETR_VARIANT", "nano").lower()
    device: str = os.getenv("DEVICE", "cuda")
    optimize_inference: bool = _b("OPTIMIZE_INFERENCE", True)
    work_res: int = _i("WORK_RES", 640)
    default_conf: float = _f("DEFAULT_CONF", 0.40)
    world_conf: float = _f("WORLD_CONF", 0.05)   # conf baja: objetos de anaquel puntúan poco
    nms_iou: float = _f("NMS_IOU", 0.6)   # fusiona cajas dobles → menos IDs falsos

    # tracking
    track_activation: float = _f("TRACK_ACTIVATION", 0.35)
    track_lost_buffer: int = _i("TRACK_LOST_BUFFER", 45)
    track_min_match: float = _f("TRACK_MIN_MATCH", 0.75)
    min_box_area_frac: float = _f("MIN_BOX_AREA_FRAC", 0.0008)
    # frames que la persona debe permanecer del otro lado para contar el cruce
    # (evita falsas entradas por jitter/cambios de ID). Más alto = más estricto.
    line_cross_min: int = _i("LINE_CROSS_MIN", 5)

    # procesamiento
    frame_stride: int = _i("FRAME_STRIDE", 1)
    max_width: int = _i("MAX_WIDTH", 1280)
    jpeg_quality: int = _i("JPEG_QUALITY", 80)

    # reglas / alertas
    dwell_alert_sec: float = _f("DWELL_ALERT_SEC", 600)
    shelf_alert_pct: float = _f("SHELF_ALERT_PCT", 30)
    shelf_critical_pct: float = _f("SHELF_CRITICAL_PCT", 20)
    store_capacity: int = _i("STORE_CAPACITY", 50)

    # servidor
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = _i("PORT", 8010)
    videos_dir: str = os.getenv("VIDEOS_DIR", "videos")
    data_dir: str = os.getenv("DATA_DIR", "data")

    @property
    def videos_abs(self) -> Path:
        p = Path(self.videos_dir)
        return p if p.is_absolute() else ROOT / p

    @property
    def data_abs(self) -> Path:
        p = Path(self.data_dir)
        return p if p.is_absolute() else ROOT / p


config = Config()
config.data_abs.mkdir(parents=True, exist_ok=True)
config.videos_abs.mkdir(parents=True, exist_ok=True)
