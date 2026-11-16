# PyroChronos 🔥

PyroChronos reúne detecciones de calor de **MODIS y VIIRS** de NASA FIRMS para ayudar a bomberos y brigadas a explorar la actividad en Perú. Ofrece un mapa de datos recientes, un calendario histórico y un bot de Telegram que puede avisar sobre detecciones cercanas.

> Un foco de calor **no confirma un incendio**. Los datos pueden tener retraso y no reemplazan la verificación en campo ni los avisos oficiales. PyroChronos no predice incendios.

## Qué puedes hacer

- **Mapa:** seleccionar una zona y consultar los datos recientes guardados o el historial. Revisa siempre la fecha de descarga.
- **Historial:** comparar meses y años. Algunas cifras son estimadas y los totales y rankings son provisionales.
- **Telegram:** compartir una ubicación en privado y elegir la distancia para recibir avisos de detecciones que cumplan el umbral de intensidad. El bot debe estar funcionando y tener datos recientes.
- **Informes:** descargar datos y abrir un informe imprimible. La interfaz está disponible en español e inglés.

## Probar la web en tu computadora

Necesitas **Python 3.11 o posterior** y conexión a internet para instalar las dependencias y cargar el mapa base. El repositorio incluye un archivo histórico de ejemplo; no necesitas una clave de NASA para explorar ese historial. La fecha disponible aparece en la web. Este archivo es distinto al usado para la validación local de la participante.

En Windows, abre PowerShell en la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn api.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

En macOS o Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn api.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Abre **http://127.0.0.1:8000**. La versión compilada de la web ya viene incluida; no necesitas Node.js para esta prueba. Para detener el servidor, pulsa `Ctrl + C` en su terminal.

La capa de datos recientes aparece vacía si no hay una descarga guardada. Eso **no significa que no haya focos**. El calendario histórico y los datos recientes son independientes.

## Probar el bot y los datos recientes (opcional)

Necesitas una [clave de NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/api/map_key/) y un bot de Telegram creado con BotFather. Copia `.env.example` como `.env` **solo si aún no tienes uno** y completa `FIRMS_MAP_KEY` y `TELEGRAM_BOT_TOKEN` en tu computadora. No publiques ese archivo ni compartas tus claves. `TELEGRAM_CHAT_ID` se usa para la demo de envío, no es necesario para la vigilancia por ubicación.

En otra terminal, desde la carpeta del proyecto, con el entorno virtual instalado:

```powershell
# Windows
.\.venv\Scripts\python.exe backend\scripts\bot.py --poll --auto-refresh --zone peru
```

```bash
# macOS / Linux
.venv/bin/python backend/scripts/bot.py --poll --auto-refresh --zone peru
```

En el chat **privado** del bot, envía `/start`, comparte tu ubicación y elige la distancia. El proceso intenta actualizar FIRMS y revisar las detecciones aproximadamente cada 15 minutos. Para recibir también una confirmación de cada revisión en el chat privado, añade `--heartbeat` al comando. Usa una sola instancia del bot a la vez.

La participante comprobó la llegada de confirmaciones periódicas a Telegram. La entrega automática de una **alerta real por una detección cercana** aún está pendiente de comprobar. Si el equipo se apaga, se suspende o pierde conexión, el bot deja de vigilar. Los avisos no cubren todas las detecciones ni garantizan disponibilidad o entrega.

Guía de prueba y diagnóstico: [comprobación de alertas](docs/comprobacion-alerta-real.md).

## Datos y validación

La aplicación compara las fuentes sobre una cuadrícula común. Para los periodos con un solo sensor utiliza factores separados para estimar la unión; si no hay calibración VIIRS suficiente, no inventa un valor. Las cifras dependen del archivo, la zona y el periodo.

Con su propio archivo de **2 212 061 detecciones**, la participante comunicó una validación mensual para Perú de 14 años (2012–2025): la mediana del error absoluto anual de VIIRS hacia la unión satelital fue **1,02 %**. Esta comparación no es una medición de incendios confirmados ni valida otros periodos o zonas. El archivo de ejemplo del repositorio produce otros resultados.

- [Método y límites](docs/metodologia.md)
- [Validación VIIRS](docs/validacion-viirs.md) y [validación MODIS](docs/validacion-retrospectiva.md)
- [Procedencia de los datos](docs/procedencia.md)
- [Declaración de uso de IA](docs/ia.md)

## Privacidad y licencia

Las ubicaciones, verificaciones e historial de envíos se guardan localmente. **No publiques la aplicación sin proteger el acceso a esos datos**: ocultarlos en la pantalla no protege la API. El bot envía mensajes y ubicaciones de detecciones a Telegram; el mapa base usa OpenStreetMap.

El archivo de ejemplo `data/derived/detections.parquet` está versionado. Si lo reemplazas con datos propios, Git verá el cambio: revisa `git status` antes de subir nada y no publiques datos sensibles ni `.env`. No es necesario reconstruir el archivo para probar la web.

Código bajo [licencia MIT](LICENSE). Detecciones de NASA FIRMS; límites departamentales simplificados con sus [atribuciones y licencia](data/geo/README.md).

---

**Cambiando vidas, un fueguito menos a la vez. 🔥**
