# Metodología de armonización

Objetivo: reducir las diferencias entre sensores para facilitar la comparación histórica, sin
suponer que son equivalentes. Las estimaciones tienen incertidumbre y limitaciones declaradas.

## 1. Normalización (esquema común)

Cada archivo de FIRMS se convierte a una sola tabla:

| campo | significado |
|---|---|
| `day` | fecha de la detección |
| `lat`, `lon` | coordenadas del píxel del foco |
| `source` | 1 = MODIS (Terra y Aqua), 2 = VIIRS S-NPP |
| `conf_level` | **0 baja, 1 nominal, 2 alta** (escala unificada) |
| `conf_raw` | MODIS: confianza 0–100 tal cual llega · VIIRS: −1 |
| `frp` | potencia radiativa del fuego (MW) |
| `ftype` | 0 vegetación · 1 volcán · 2 fuente fija industrial · 3 costa/otro |

La confianza se unifica así: MODIS numérica → baja si < 30, nominal entre 30 y 79, alta desde 80;
VIIRS por categorías → `l` baja, `n` nominal, `h` alta. Por defecto se descartan las de confianza
baja y, opcionalmente, los tipos de fuente fija (`quality.exclude_types` en `config.yaml`).

El parquet de ejemplo incluido en el repositorio contiene **1 323 016 detecciones**: 336 778
MODIS y 986 238 VIIRS. El parquet local de la participante es distinto: **2 212 061 detecciones**;
los resultados y la validación deben calcularse con el archivo que se va a presentar.

## 2. Cuadrícula y medida principal

Cuadrícula fija de **0,01° (≈1,1 km)**. La medida principal es **celdas-día con fuego**: una celda
cuenta como máximo una vez por día y por satélite.

- *Por qué*: VIIRS tiene ≈375 m y MODIS ≈1 km; además VIIRS observa dos veces por noche. Contar
  detecciones sueltas haría que los años recientes parecieran mucho más activos por un artefacto
  de instrumento. En 2024, por ejemplo, VIIRS produjo 4,7 veces más detecciones que MODIS en la
  misma zona.
- *Segunda medida*: **focos detectados** (detecciones sueltas). Se muestra siempre como referencia
  y sirve para explicar la diferencia, nunca como la serie armonizada.

Cada periodo (mes o semana ISO) suma las celdas-día. Fuera de las fechas extremas del conjunto
se marca sin dato; dentro de ellas, periodos sin detecciones se muestran como cero. Las detecciones
por sí solas no demuestran cobertura efectiva de los satélites durante todo el periodo.

## 3. Calibración (solo en los años de solape)

La escala de referencia es la de **los dos satélites juntos** (celdas-día sin duplicar entre
sensores). Esa escala solo se puede observar donde ambos existen: **2012–2025**.

Para cada periodo del año `p` (mes 1–12 o semana 1–53):

```
cociente(p, año) = union_cd(p, año) / modis_cd(p, año)      # solo años de solape
factor(p)        = mediana de cociente(p, ·)                # si hay >= 5 años
incertidumbre(p) = [percentil 25, percentil 75] del cociente
```

Si un periodo no tiene suficientes años de solape, se usa el factor global y el valor se marca
como *factor de reserva* (menos fiable).

**Valores de referencia del parquet de ejemplo del repositorio**, no del parquet local:

| granularidad | factor global | p25 – p75 | concordancia (r) | periodos de solape |
|---|---|---|---|---|
| mensual | 5,83 | 4,91 – 6,52 | 0,979 | 168 |
| semanal | 5,70 | 4,73 – 7,15 | 0,961 | 728 |

En el parquet de ejemplo el factor varía según el periodo del año. Esta variación motiva calcular
factores por mes o semana, pero por sí sola no demuestra la causa de las diferencias entre sensores.

## 4. Serie armonizada

```
si el periodo tiene AMBOS satélites →  valor = celdas-día observadas (sin estimación)
si solo tiene MODIS            →  valor = modis_cd × factor(p)          [ESTIMADO]
                                    banda = [modis_cd × p25(p), modis_cd × p75(p)]
si solo tiene VIIRS            →  valor = viirs_cd × factor(p)          [ESTIMADO]
```

Los valores estimados se dibujan con **trama rayada**. También puede haber periodos estimados después
de 2012. **Limitación pendiente:** aplicar el factor unión/MODIS a VIIRS sin MODIS no está justificado
por esa calibración y puede inflar el resultado; el ranking y el total armonizado siguen siendo
provisionales hasta corregir o justificar ese caso.

## 5. Validación retrospectiva de la estimación desde MODIS

Se agrega por mes la unión observada de celdas-día de MODIS y VIIRS. Para cada año **completo**
elegible dentro del solape configurado (2012–2025), se excluyen **todos los meses de ese año**,
se recalibran los factores unión/MODIS con los demás años y se estima el año apartado usando solo
sus celdas-día MODIS y los factores mensuales. Se compara la suma de los doce meses estimados con
la suma de los doce meses de la unión observada. El **error absoluto porcentual anual** es
`100 × |estimado − observado| / observado`; el error típico se resume con la **mediana** de esos
errores anuales. El script también informa los valores por año, el error firmado, el MAPE, el WAPE,
el número de años y los meses que recurrieron al factor global. Cada año evaluado debe estar dentro
de la cobertura global del archivo y tener detecciones de ambos sensores en los 12 meses; los años
que no cumplen se excluyen y se muestran con el motivo. Tener detecciones cada mes **no demuestra**
cobertura satelital completa. Si no hay al menos tres periodos útiles de entrenamiento se omite el
año, en vez de inventar un factor.

Ejecutar `python backend/scripts/validacion_retrospectiva.py` usa la zona predeterminada y el parquet
local sin modificarlo. La validación es retrospectiva: el entrenamiento puede incluir años posteriores
al evaluado. Contrasta contra la **unión satelital, no contra incendios confirmados en campo**. No
valida directamente las estimaciones anteriores a 2012, otros departamentos ni el caso de VIIRS sin
MODIS. El rango p25–p75 es dispersión de cocientes, no un intervalo de confianza garantizado.

En el parquet de ejemplo del repositorio, con Perú y 14 años evaluados, la mediana fue **7,63 %**
(≈8 %); el promedio fue 7,00 % y el máximo anual 16,54 %. **No son resultados del parquet local** de
2 212 061 filas: deben calcularse por separado antes de citarse para esa base.

## 6. Anomalías

Para cada periodo de la serie armonizada:

1. Historial = periodos del **mismo periodo del año ±1** (ventana configurable), de **otros años**
   (leave-one-out: el año evaluado nunca entra en su propio historial).
2. Percentil del valor dentro de ese historial (rango medio para empates).
3. Se marca **alto** desde el percentil 90 y **extremo** desde el 97,5.
4. Guardas: se exigen al menos **6 años** de historial y un mínimo de **5 celdas-día**; si no, no se
   clasifica (aparece como “sin historial suficiente” en el tooltip).

El calendario no depende solo del color: hay borde, símbolos ▲ (alto) y ◆ (extremo), trama para lo
estimado y texto alternativo en cada celda para lectores de pantalla.

## 7. Límites que declaramos

1. **Supuesto de estabilidad**: el factor asume que la diferencia de sensibilidad entre sensores es
   estable en el tiempo. No modela cambios de versión del algoritmo (MODIS C6.1, VIIRS 2.0), ni la
   degradación de Terra/Aqua, ni la sustitución de Suomi-NPP por NOAA-20/21.
2. **El denominador del factor** son los años 2012–2025. Si la relación entre sensores cambió,
   la estimación histórica hereda ese sesgo.
3. **MODIS cambia de sensibilidad en 2002** (antes solo Terra; desde 2002 Terra + Aqua). No está
   corregido: puede haber un escalón suave entre 2000–2002 y el resto.
4. **La unión de sensores no es una "verdad"**: es una escala consistente y declarada. Por eso el
   selector *Fuente → Solo MODIS* existe como modo de verificación.
5. **Comparación entre años**: el año más activo se publica con su banda de incertidumbre y, si el
   segundo año cae dentro de esa banda, la interfaz lo dice explícitamente ("empate técnico").
6. **Sin tiempo real**: la serie estándar (SP) llega con meses de retraso y NASA la reprocesa.
   Los últimos meses deben descargarse aparte y pueden cambiar.
