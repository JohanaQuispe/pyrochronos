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

## Cómo importar un archivo propio ya limpio

Si tus focos vienen de un archivo propio (por ejemplo `focos_incendios_limpios.csv`, o un XLSX de
Excel, o un Parquet) y **no** llevan los nombres de archivo de FIRMS, no hace falta renombrar nada:

```bash
python backend/scripts/import_clean.py --file "C:\\ruta\\focos_incendios_limpios.csv" --inspect
python backend/scripts/import_clean.py --file "C:\\ruta\\focos_incendios_limpios.csv" --write
```

- `--inspect` (por defecto) **no escribe nada**: muestra columnas reconocidas, rango de fechas,
  cuántas filas por satélite, cuántas quedan dentro de la zona y cuántas caen por control de calidad.
- `--write` guarda una copia del parquet anterior como `detections_antes_<fecha>.parquet` y recién
  entonces escribe. Antes de reemplazar el almacén conviene mirar el informe de `--inspect`.
- En los CSV de FIRMS la columna **`instrument`** dice el sensor (`MODIS` / `VIIRS`); la columna
  `satellite` sólo trae códigos (`T`/`A` para Terra/Aqua, `N`/`N20`/`N21` para los VIIRS). El
  importador usa `instrument` cuando existe y también entiende esos códigos.
- **Si el archivo no trae columna de sensor** (sólo `latitude, longitude, acq_date, confidence, type`),
  el sensor se deduce del **nombre del archivo** (`MODIS_SP_historico`, `VIIRS_NOAA20_…`). Si tampoco
  el nombre lo dice, hay que declararlo con `--source modis` / `--source viirs`, y esa declaración
  queda anotada en `dataset.json` (`sensor_note`) para no hacerla pasar por dato observado.
- **Si el archivo no trae FRP**, el importador avisa: el calendario, las anomalías y el semáforo
  funcionan igual, pero el indicador de FRP queda en cero y el reporte lo dice.
- Reconoce nombres de columna en español e inglés (lat/lon, fecha, satélite, confianza, FRP, tipo),
  fechas `2024-09-15` o `20240915`, confianza `l/n/h` o escala 0–100 de MODIS, y deduplica por
  día + punto + sensor (`--dedupe off` para no hacerlo).
- El resultado queda con el mismo esquema y el mismo control de calidad que
  `build_dataset.py`, así que todo lo demás (calendario, anomalías, semáforo, reporte) funciona igual.

**Las cifras cambian si los datos cambian.** El factor de armonización (5.828), los totales y los
años más activos que aparecen en `docs/pitch.md` corresponden al parquet que está en el repositorio.
Si importas tu propio archivo y el número de filas es distinto, hay que volver a correr
`python backend/scripts/harmonize.py` y actualizar esas cifras antes de grabar o presentar.

## Qué NO se usa

- No se usan los servicios WMS/WFS de FIRMS como fuente del calendario (no sirven para series).
- No se consulta la API `area` en vivo desde la web: la app lee del almacén local.
- No hay datos sintéticos en la demo. Si en algún momento se usan para pruebas, se rotulan
  **SINTÉTICOS** en pantalla.
- No se usa ningún logo ni marca de terceros.

## Aviso que la aplicación muestra siempre

> Análisis histórico de focos de calor detectados por satélite. No es un sistema de detección en
> tiempo real ni de predicción de incendios.
