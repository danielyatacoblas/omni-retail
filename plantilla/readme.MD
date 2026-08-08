Tengo este prototipo visual [pega aquí el código del mockup o adjúntalo] de un dashboard OMNI Retail v1 para ApexCorp. Necesito convertirlo en una aplicación funcional que:

1. Backend en Python con FastAPI (según arquitectura definida: modelo person-detection-retail-0013 de Intel sobre OpenVINO para detección, y ByteTrack o Supervision para seguimiento, línea de conteo y zonas poligonales)
2. Procese un archivo de video real subido por el usuario (no cámara en vivo)
3. Permita definir zonas poligonales sobre el primer frame del video (reutilizar el editor de zonas del mockup) y guardarlas como coordenadas reales que el backend use para calcular permanencia
4. Calcule y sirva al dashboard: conteo de ingresos/salidas/tránsito por la línea configurada, tiempo de permanencia real por zona, y alertas de nivel de anaquel por región
5. Exporte los datos reales a CSV (no simulado)
6. Optimizado para correr en un mini PC con Intel N100 (cuantización INT8 vía NNCF si aplica, resolución de trabajo 416–640 px)
7. Usa los modelos de RF-DETR que tien optimzado el uso de tranig nmas preciso y rapido que l yolo tal vez uses es o y de ai toros caso de uso de timpo en zona o cosas utiles que pueda llamar la atencion. entonoces con ello

DISEÑA ALGO MAS BONITO O INTERACTIVO PARA QUE LLAME LA ATENCION AL CLIENTE PARECIDO Al mockup, solo reemplaza los datos simulados por datos reales del procesamiento de video. serian videos par aello en la captea asi como el first mvp_ppe.
