# Metodología de armonización

Objetivo: que **el sensor de origen deje de importar**. Después de armonizar, un valor de 2005 y
otro de 2024 significan lo mismo, con su incertidumbre declarada.

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

Con los archivos de Perú (2000–2025) quedan **1 323 016 detecciones** tras el control de calidad:
336 778 de MODIS y 986 238 de VIIRS.

## 2. Cuadrícula y medida principal

Cuadrícula fija de **0,01° (≈1,1 km)**. La medida principal es **celdas-día con fuego**: una celda
cuenta como máximo una vez por día y por satélite.

- *Por qué*: VIIRS tiene ≈375 m y MODIS ≈1 km; además VIIRS observa dos veces por noche. Contar
  detecciones sueltas haría que los años recientes parecieran mucho más activos por un artefacto
  de instrumento. En 2024, por ejemplo, VIIRS produjo 4,7 veces más detecciones que MODIS en la
  misma zona.
- *Segunda medida*: **focos detectados** (detecciones sueltas). Se muestra siempre como referencia
  y sirve para explicar la diferencia, nunca como la serie armonizada.

Cada periodo (mes o semana ISO) suma las celdas-día. Fuera del periodo de un satélite el valor es
**sin dato**, nunca cero; y donde hay cobertura y no hubo focos, el valor es cero real.

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

**Valores de referencia con los datos de Perú:**

| granularidad | factor global | p25 – p75 | concordancia (r) | periodos de solape |
|---|---|---|---|---|
| mensual | 5,83 | 4,91 – 6,52 | 0,979 | 168 |
| semanal | 5,70 | 4,73 – 7,15 | 0,961 | 728 |

El factor es mayor en los meses de lluvia (feb–mar ≈ 7) y menor en el pico de la temporada
(sep ≈ 4,1): cuando hay muchos incendios grandes, MODIS también los ve y la diferencia entre
sensores se reduce. Que el factor **varíe con la estación** es justamente la razón de calibrar por
periodo y no con un único número global.

## 4. Serie armonizada

```
si el periodo tiene AMBOS satélites →  valor = celdas-día observadas (sin estimación)
si solo tiene MODIS            →  valor = modis_cd × factor(p)          [ESTIMADO]
                                    banda = [modis_cd × p25(p), modis_cd × p75(p)]
si solo tiene VIIRS            →  valor = viirs_cd × factor(p)          [ESTIMADO]
```

Los valores estimados se dibujan con **trama rayada** en el calendario y en la documentación. Antes
de 2012 todo es estimado; desde 2012 todo es observado.

## 5. Anomalías

Para cada periodo de la serie armonizada:

1. Historial = periodos del **mismo periodo del año ±1** (ventana configurable), de **otros años**
   (leave-one-out: el año evaluado nunca entra en su propio historial).
2. Percentil del valor dentro de ese historial (rango medio para empates).
3. Se marca **alto** desde el percentil 90 y **extremo** desde el 97,5.
4. Guardas: se exigen al menos **6 años** de historial y un mínimo de **5 celdas-día**; si no, no se
   clasifica (aparece como “sin historial suficiente” en el tooltip).

El calendario no depende solo del color: hay borde, símbolos ▲ (alto) y ◆ (extremo), trama para lo
estimado y texto alternativo en cada celda para lectores de pantalla.

## 6. Límites que declaramos

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
