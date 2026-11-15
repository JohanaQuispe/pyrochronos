# PyroChronos · calendario de actividad de incendios

Aplicación web que **armoniza los focos de calor de MODIS y VIIRS** (NASA FIRMS) en un único
calendario de actividad de incendios, para que una persona pueda ver en menos de un minuto
**cuándo es la temporada de fuego de su zona** y **qué años o meses fueron anormales**.

- Reto: *Harmonization of MODIS and VIIRS Hot Spots* — NASA Space Apps Challenge 2026.
- Datos reales: Perú, MODIS desde 2000-11 y VIIRS S-NPP desde 2012, hasta 2025-12-31.
- **No es detección en tiempo real ni predicción.** Es análisis histórico.

## Lo que hace hoy (verificado con datos reales)

| Función | Estado |
|---|---|
| Descarga y normalización de los CSV de FIRMS (confianza unificada 0/1/2) | funciona |
| Cuadrícula común de 0,01° y medida principal **celdas-día con fuego** | funciona |
| Armonización MODIS+VIIRS con factor, incertidumbre y concordancia | funciona |
| Calendario de calor (años × meses / años × semanas) con anomalías | funciona |
| Mapa con focos del periodo y dibujo de zona | funciona |
| Tarjetas: mes y año más activos, último mes vs mediana, total de focos | funciona |
| Gráfico del año frente a la mediana con banda de percentiles 25–75 | funciona |
| Descarga CSV de focos y CSV de la serie armonizada | funciona |
| Resumen en lenguaje simple (plantillas, sin IA generativa) | funciona |
| **Semáforo de temporada** (aviso anticipado con la historia de la zona) | funciona |
| **Reporte ejecutivo imprimible** (PDF desde el navegador) | funciona |
| Boletín y vigilancia automática por Telegram (token solo en el servidor) | funciona en simulación |
| Modo reciente (NRT, latencia ~3 h) | implementado; requiere `FIRMS_MAP_KEY` y salida a internet |

## Cómo correrlo

```bash
# 1) entorno
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# 2) datos (dos opciones)
python backend/scripts/download_history.py --country Peru --years 2000-2025   # ~40 archivos, sin clave
#   o usa tus CSV ya descargados en data/raw/
python backend/scripts/build_dataset.py --raw data/raw

# 3) frontend
cd frontend && npm install && npm run build && cd ..

# 4) servidor (sirve la web y la API en el mismo puerto)
python -m uvicorn api.main:app --app-dir backend --host 0.0.0.0 --port 8000
```

Abre `http://localhost:8000`. Documentación interactiva de la API en `/api/docs`.

### Zonas no precargadas

```bash
export FIRMS_MAP_KEY=tu_clave      # nunca en el código ni en el navegador
python backend/scripts/download_zone.py --bbox -70.6,-13.4,-68.6,-11 --years 2025-2026
python backend/scripts/build_dataset.py --raw data/raw
```

### Pruebas

```bash
python -m pytest backend/tests -q      # 53 pruebas: normalización, armonización, anomalías, API, campo y POWER
cd frontend && npm run smoke           # monta la interfaz en jsdom y comprueba que renderiza sin errores
```

### Semáforo de temporada y avisos (opcional)

```bash
python backend/scripts/alert.py --zone madrededios          # semáforo en la terminal
python backend/scripts/telegram_setup.py --guide             # crear el bot en @BotFather
python backend/scripts/telegram_setup.py --check             # ¿el token funciona?
python backend/scripts/telegram_setup.py --chat-id           # descubrir tu chat_id
python backend/scripts/telegram_setup.py --write-env --test   # guardar en .env y probar
python backend/scripts/watch_alerts.py --zones peru,madrededios --send
```

El bot se crea a mano en **@BotFather** (Telegram no permite crearlo por API); el resto lo hace
`telegram_setup.py` sin imprimir nunca el token completo.

### Modo campo: geocercas y bot (opcional)

```bash
python backend/scripts/bot.py --dry-run                  # el aviso, sin enviar nada
python backend/scripts/bot.py --send-demo                # ejemplo marcado DEMO
python backend/scripts/bot.py --poll                     # avisa si un foco cae en tu radio
python backend/scripts/download_power.py --zone madrededios --years 5   # contexto NASA POWER
```

Detalles, comandos del bot y límites en [`docs/campo.md`](docs/campo.md).

### Focos recientes (NRT, ~3 h de latencia)

```bash
export FIRMS_MAP_KEY=...
python backend/scripts/download_recent.py --zone madrededios --days 3
```

Detalles, reglas y límites en [`docs/alertas.md`](docs/alertas.md).

## Arquitectura por capas

```
descarga      backend/scripts/download_history.py | download_zone.py
normalización backend/pyro/normalize.py    (esquema común: fecha, lat, lon, fuente, confianza 0/1/2, FRP, tipo)
cuadrícula    backend/pyro/grid.py         (celdas-día, series semanales y mensuales)
armonización  backend/pyro/harmonize.py    (factor VIIRS/MODIS, incertidumbre, concordancia)
anomalías     backend/pyro/anomalies.py    (percentiles leave-one-out, ventana ±1)
API           backend/api/main.py          (FastAPI)
interfaz      frontend/src                 (React + Vite + Tailwind + Leaflet)
almacén       backend/pyro/store.py        (Parquet hoy; la lógica no depende del motor)
```

Todo lo configurable está en **`config.yaml`**: zona, tamaño de celda, confianza mínima,
tipos de fuente excluidos, ventana de solape, umbrales de anomalía, límites de la API.

## Documentación

- [`docs/metodologia.md`](docs/metodologia.md) — cómo se armoniza, con fórmulas y límites.
- [`docs/alertas.md`](docs/alertas.md) — semáforo de temporada, modo reciente y avisos por Telegram.
- [`docs/campo.md`](docs/campo.md) — geocercas, pines, validación humana y contexto NASA POWER.
- [`docs/arquitectura-tactica.md`](docs/arquitectura-tactica.md) — esquema PostGIS y diseño de la capa táctica.
- [`docs/procedencia.md`](docs/procedencia.md) — de dónde salen los datos, con fechas y hashes.
- [`docs/ia.md`](docs/ia.md) — declaración de uso de IA.
- [`docs/pitch.md`](docs/pitch.md) — guion de 3 minutos y cómo hacer la demo.
- [`docs/verificado.md`](docs/verificado.md) — qué está verificado y qué queda POR VERIFICAR.

## Licencia

MIT (ver `LICENSE`). Datos: NASA FIRMS, dominio público. Sin logos ni marcas de terceros.
