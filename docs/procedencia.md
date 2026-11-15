# Procedencia de los datos

## Fuente original

**NASA FIRMS** (Fire Information for Resource Management System), NASA EOSDIS.
Datos de **dominio público**. Productos usados: procesamiento estándar (SP).

| producto | archivo | cobertura usada | detecciones tras control de calidad |
|---|---|---|---|
| MODIS (Terra + Aqua), colección 6.1 | `modis_{año}_Peru.csv` | 2000-11-01 → 2025-12-31 | 336 778 |
| VIIRS Suomi-NPP, versión 2.0 | `viirs-snpp_{año}_Peru.csv` | 2012-01-20 → 2025-12-31 | 986 238 |

URL oficial de los archivos anuales por país (sin clave):

```
https://firms.modaps.eosdis.nasa.gov/data/country/{modis|viirs-snpp}/{año}/{slug}_{año}_Peru.csv
```

Columnas originales: MODIS `latitude, longitude, brightness, scan, track, acq_date, acq_time,
satellite, instrument, confidence, version, bright_t31, frp, daynight, type`; VIIRS igual pero con
`bright_ti4 / bright_ti5` y `confidence` en categorías `l/n/h`.

## Cómo se obtuvieron (y una transparencia incómoda)

El script propio del proyecto es `backend/scripts/download_history.py`. Descarga esos archivos
directamente desde `firms.modaps.eosdis.nasa.gov`, con manifiesto de tamaño, SHA-256 y fecha.

**Transparencia:** el entorno de desarrollo usado para construir la demo (un contenedor en la nube)
tiene la salida de red restringida y **no puede alcanzar `firms.modaps.eosdis.nasa.gov`**. Para no
bloquear el desarrollo, los mismos archivos oficiales de FIRMS (mismos nombres, mismas columnas,
mismo contenido de NASA) se obtuvieron desde una copia pública en GitHub. Los CSV resultantes son
los de FIRMS; no se usó código de terceros, sólo los archivos de datos.

Reproducir desde la fuente original:

```bash
python backend/scripts/download_history.py --country Peru --years 2000-2025
python backend/scripts/build_dataset.py --raw data/raw
```

Los archivos crudos **no se versionan** (`data/raw/` está en `.gitignore`, son ~107 MB). Lo que se
versiona es `data/derived/detections.parquet` (13 MB) junto con `data/derived/dataset.json`, que
guarda filas, rango de fechas, hash y parámetros de calidad usados.

## Qué NO se usa

- No se usan los servicios WMS/WFS de FIRMS como fuente del calendario (no sirven para series).
- No se consulta la API `area` en vivo desde la web: la app lee del almacén local.
- No hay datos sintéticos en la demo. Si en algún momento se usan para pruebas, se rotulan
  **SINTÉTICOS** en pantalla.
- No se usa ningún logo ni marca de terceros.

## Aviso que la aplicación muestra siempre

> Análisis histórico de focos de calor detectados por satélite. No es un sistema de detección en
> tiempo real ni de predicción de incendios.
