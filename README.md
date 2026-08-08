# OMNI Retail — MVP de Tracking (ApexCorp)

Dashboard funcional de **visión computacional para retail** sobre video real.
Detecta y **sigue personas con RF-DETR + ByteTrack**, y entrega, con **datos reales**
del procesamiento (no simulados):

- **Conteo de personas** por una *línea de conteo* configurable (IN / OUT / dentro).
- **Permanencia por zona** (dwell time real por persona en polígonos que tú dibujas).
- **Nivel de anaqueles** por región (heurística de llenado por densidad de bordes — *experimental*).
- **Alertas** reales (permanencia excesiva, aforo excedido, anaquel bajo/crítico).
- **Exportación a CSV** de todo el reporte.

> **RF-DETR (Roboflow)** se usa en vez de YOLO por su mejor precisión/velocidad en
> personas y porque su salida integra directo con ByteTrack, LineZone y PolygonZone.

---

## 1. Instalar

Este MVP **comparte el mismo Python global** que `first_mvp_ppe` (ya trae
**torch 2.5.1+cu121 con CUDA**, ultralytics y supervision), así no se re-descarga
torch. Solo falta agregar `rfdetr`:

```bash
cd first_mvp_tranking
pip install rfdetr            # arrastra supervision>=0.29; torch CUDA ya está
```

> Si prefieres un entorno aislado: `python -m venv .venv` y luego
> `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121`
> (GPU) **o** `pip install torch torchvision` (CPU / Intel N100), y `pip install -r requirements.txt`.
> Requiere ~3 GB libres para el torch CUDA.

## 2. Descargar modelo + videos de muestra

```bash
python download_models.py              # pesos RF-DETR + videos retail (Roboflow/Supervision)
python download_models.py --no-video   # solo el modelo
```

Los videos de muestra (mercado, tienda, mall) vienen de `supervision.assets` (Roboflow)
y quedan en `videos/`. También puedes copiar tus propios `.mp4` a esa carpeta.

## 3. Ejecutar

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8010
```

Abre <http://localhost:8010>:

1. Elige un video (se muestra el primer frame).
2. Con las herramientas dibuja según el caso de uso:
   - **╱ Línea de conteo** → 2 clics (para contar entradas/salidas).
   - **▢ Zona permanencia** → clics + doble clic para cerrar (dwell time).
   - **▤ Zona anaquel** → clics + doble clic (nivel de llenado).
   - Si el video no necesita zonas, solo pulsa **Procesar** (detección + tracking).
3. **Procesar** → verás el video anotado en vivo y las estadísticas reales.
4. **Exportar CSV** cuando termine (se guarda también automático en `data/`).

### Modo CLI (sin servidor)

```bash
python run_video.py videos/market-square.mp4 --conf 0.35
# genera outputs/<video>_omni.mp4 anotado + data/reporte_<video>.csv
```

---

## Ajustes (`.env`)

| Clave | Descripción |
| ----- | ----------- |
| `RFDETR_VARIANT` | `nano` (N100) · `small` · `medium` (más preciso) |
| `DEVICE` | `cuda` (RTX 3060) · `cpu` (Intel N100) |
| `WORK_RES` | Resolución de trabajo (múltiplo de 56): 448/560 edge, 640 preciso |
| `DEFAULT_CONF` | Umbral de confianza de persona |
| `TRACK_*` | Parámetros de ByteTrack (activación, buffer, IoU) |
| `FRAME_STRIDE` | 1 = todos los frames (conteo preciso); 2-3 = más rápido |
| `DWELL_ALERT_SEC` | Segundos de permanencia que disparan alerta |
| `SHELF_ALERT_PCT` / `SHELF_CRITICAL_PCT` | Umbrales de nivel de anaquel |
| `STORE_CAPACITY` | Aforo (KPI y alerta de aforo excedido) |

## Cómo se calcula (datos reales)

- **Conteo:** `supervision.LineZone` cuenta cruces con dirección → IN/OUT; *dentro* = IN − OUT.
- **Permanencia:** `supervision.PolygonZone` marca qué tracks están dentro; se acumulan
  segundos por `track_id` usando el **tiempo del video** (frame / fps), no el reloj real.
- **Anaquel:** densidad de bordes (Canny) del ROI vs. la del primer frame (baseline ≈ lleno).
  Es una **heurística** para demo; para producción se recomienda un detector de producto/vacío
  dedicado o referencia calibrada por anaquel.

## Ruta a producción / edge (Intel N100)

- `DEVICE=cpu` + `RFDETR_VARIANT=nano` + `WORK_RES=448–560`.
- Exportar RF-DETR a **ONNX/OpenVINO** e **INT8 (NNCF)** para 2 cámaras en paralelo,
  siguiendo el patrón ya probado en `vision-node` (`num_streams=2`, ByteTrack, zonas por cámara).
- Migrar de archivo de video a **RTSP** en vivo reutilizando `vision-node/server`.
