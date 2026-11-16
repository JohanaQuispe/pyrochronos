# Arquitectura de la aplicación

PyroChronos funciona como una aplicación local de Python con una interfaz web y un proceso opcional de Telegram.

- **Datos históricos:** `data/derived/detections.parquet`; `backend/pyro/store.py` carga el archivo y los módulos de cuadrícula y armonización calculan el calendario.
- **Datos recientes:** el bot puede descargar FIRMS y guardar el resultado en `data/derived/recent.parquet`. La web lee ese archivo; no realiza una descarga de FIRMS en cada consulta.
- **Interfaz y API:** FastAPI (`backend/api/main.py`) sirve la API y la web compilada (`backend/webapp`). El código fuente de la interfaz está en `frontend/src`.
- **Bot:** `backend/scripts/bot.py` consulta la API de Telegram, actualiza datos recientes si se activa esa opción y revisa detecciones cercanas. Los mensajes de estado son opcionales.
- **Estado de campo:** `backend/pyro/groundtruth.py` guarda ubicaciones compartidas, verificaciones e historial de envíos en JSON local. `PYRO_FIELD_DIR` permite elegir otra carpeta para ese estado.

No se usa Supabase ni PostGIS en esta implementación. El almacenamiento local requiere persistencia y protección de acceso antes de publicar la aplicación. Los endpoints de lectura de ubicaciones y verificaciones no están protegidos por `PYRO_SETUP_KEY`; esa clave solo protege el registro cuando se configura.

Los puntos son detecciones de calor, no incendios confirmados. Ver [método](metodologia.md), [guía del bot](comprobacion-alerta-real.md) y [estado de las comprobaciones](verificado.md).
