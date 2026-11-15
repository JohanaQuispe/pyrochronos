# VERIFICADO / POR VERIFICAR

## Verificado (comprobado contra la fuente o con los datos en mano)

| Dato | Cómo se comprobó |
|---|---|
| Existen archivos anuales por país **sin MAP_KEY**: `/data/country/{modis\|viirs-snpp}/{año}/{slug}_{año}_Peru.csv` | Se descargaron y se leyeron sus cabeceras |
| MODIS: 2000 → 2025; VIIRS S-NPP: 2012 → 2025 | Conteo real por año en los archivos |
| Columnas de MODIS y VIIRS (incluida `type` y `version`) | Cabeceras de los CSV reales |
| Confianza: MODIS 0–100 numérica; VIIRS `l/n/h` | Distribución real de 2024 |
| API `area`: `DAY_RANGE` 1–5 y la fecha corre hacia adelante | Página oficial `/api/area/` |
| Límite de la clave: 5 000 transacciones por 10 minutos | Estado devuelto por el propio servicio |
| La API devuelve `Invalid MAP_KEY.` como texto plano con HTTP 400 | Probado |
| **Suomi-NPP dejó de entregar datos el 2026-11-02** (aviso de FIRMS) | Aviso oficial en la página del API |
| El entorno de construcción no alcanza `firms.modaps.eosdis.nasa.gov` | Probado (conexión cortada) |
| Los archivos por país de 2026 **todavía no existen** (404) | Petición directa al archivo |

## POR VERIFICAR

1. **Últimos meses de la serie estándar.** El archivo por país de 2025 ya incluye hasta diciembre,
   pero NASA puede reprocesar y revisar. Los meses más recientes podrían cambiar.
2. **Calidad de los años recientes del archivo por país.** El volumen de 2025 (8 440 detecciones
   MODIS) es cerca de la mitad de 2024 (21 201). Puede ser un año realmente más flojo o una
   revisión pendiente: **no lo afirmamos**. La interfaz lo muestra tal cual y el documento lo marca.
3. **NOAA-20 / NOAA-21 por país.** Una fuente de terceros indica que no se publican por país; solo
   los vimos disponibles por la API `area`. No se usan en esta entrega.
4. **Comportamiento de `type` en años muy antiguos** (¿está poblado desde 2000?). Se usa tal cual llega.
5. **Cambio de sensibilidad de MODIS en 2002** (Terra solo → Terra + Aqua). No corregido.
6. **Escala exacta de `confidence` de VIIRS** entre versiones. Se usa la categórica `l/n/h`.
