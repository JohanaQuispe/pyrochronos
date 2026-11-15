# PyroChronos: cifras y alcance para la presentación

> **Pendiente de revisión:** estas cifras proceden de la salida de `numeros_pitch.py` que la
> participante ejecutó sobre sus propios archivos locales. El parquet del repositorio es otro
> conjunto y dará resultados distintos. No presentar el orden de años como definitivo hasta resolver
> la limitación de la armonización descrita abajo.

## Datos locales informados

- **2 212 061 detecciones**, del 11 de noviembre de 2000 al 1 de noviembre de 2026.
- MODIS: **579 777** detecciones; VIIRS: **1 632 284**. FRP medio: **15,93 MW**.
- **1 706 806 celdas-día observadas**, unión de sensores sin duplicar la misma celda y día.
  Por separado: MODIS 555 349 y VIIRS 1 234 013; no se deben sumar porque pueden coincidir.
- Una detección es un foco de calor satelital, no necesariamente un incendio confirmado.
  Una celda-día no es una hectárea quemada ni un incendio.

## Cifras calculadas por el programa (provisionales)

En la configuración mensual de celdas-día, el factor global de unión/MODIS fue **5,238**, con
percentiles 25–75 **4,494–5,814**. La correlación MODIS–VIIRS fue **r = 0,979** para 176 pares
mensuales con ambas fuentes. El factor usado cambia según el mes; correlación no implica que los
sensores sean equivalentes ni valida por sí sola la estimación.

El programa produjo un total mensual armonizado de **2 564 502 celdas-día**. Este total incluye
estimaciones: no equivale a 2 564 502 observaciones ni a incendios. El listado mensual obtenido fue
2026: 166 307; 2005: 155 310; 2024: 134 932; 2020: 132 140; 2022: 132 084. **2026 está
incompleto** (hasta el 1 de noviembre); 2005 incluye estimaciones. El orden semanal calculado fue
diferente: 2005: 157 876 y 2026: 155 699. No declarar un año ganador definitivo.

Según esa serie mensual calculada, agosto, septiembre y octubre representan **23,6 %, 32,3 % y
14,2 %**, respectivamente; septiembre es el máximo. Estos porcentajes son provisionales y dependen
 del conjunto y del método aplicado, no son un pronóstico para un año o lugar concreto.

### Limitación importante que revisar antes de usar el ranking o los totales

En la implementación actual, cuando un periodo tiene VIIRS pero no MODIS, el programa también
multiplica VIIRS por el factor calibrado como unión/MODIS. Ese factor no está calibrado para
convertir VIIRS por sí solo a la unión. Puede inflar estimaciones, especialmente cuando falta MODIS.
Hay que corregir o justificar el método, ejecutar de nuevo el cálculo con los archivos locales y
comprobar las cifras antes de presentarlas como resultado definitivo.

## Validación retrospectiva (reproducible)

La participante ejecutó la validación sobre su **parquet local de 2 212 061 filas** en Perú. Al
retirar cada año completo del solape de la calibración y estimarlo desde MODIS, la **mediana del
error absoluto porcentual anual fue 4,94 % en 14 años (2012–2025)**, frente a la unión observada
MODIS+VIIRS. El error promedio (MAPE) fue **7,01 %**, el ponderado (WAPE) **7,04 %** y el mayor error
anual **19,70 %** (2025). Ver [los resultados por año](validacion-retrospectiva.md).

> «Validamos retrospectivamente 14 años del solape: retiramos cada año de la calibración y lo
> estimamos desde MODIS. La mediana del error absoluto anual fue 4,94 %, frente a la unión de los
> dos satélites».

El entrenamiento puede incluir años posteriores al año evaluado. La unión de sensores **no es verdad
de campo**: esto no mide la precisión de detección de incendios. Tampoco valida directamente las
estimaciones anteriores a 2012 ni corrige el caso de VIIRS sin MODIS. Cada año evaluado tiene
detecciones de ambos sensores en los 12 meses, lo que no garantiza cobertura completa.

El parquet de ejemplo del repositorio es distinto y dio **7,63 %** de mediana; no mezclar sus
resultados con los del archivo local.

## Qué hace y qué no hace

PyroChronos está dirigido a **brigadas de bomberos**: muestra estacionalidad y anomalías históricas y
puede preparar avisos sobre focos cargados en la capa reciente. El bot filtra focos cercanos por FRP
respecto al historial local y solicita confirmación humana. El modo reciente depende de datos NRT
previamente descargados; no es una consulta en vivo. El aviso nuevo y el pin aún requieren prueba
real de extremo a extremo. El sistema no predice incendios, no confirma fuego y no sustituye una
alerta oficial ni el criterio operativo. Viento puntual, rutas, cercanía a viviendas y modo sin señal
no están implementados.

## Comprobación antes de presentar

- [ ] Resolver la limitación de armonización para periodos con VIIRS sin MODIS y recalcular con el parquet local.
- [ ] Revisar calendario, zona, fechas, mapa y descarga de reportes con los datos locales.
- [ ] Comprobar fecha y cobertura de los datos recientes antes de interpretarlos.
- [ ] Probar aviso y pin en Telegram; no mostrar credenciales en pantalla.
- [ ] Revisar el texto de entrega y distinguir resultados observados de estimaciones.
