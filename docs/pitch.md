# PyroChronos: cifras y alcance para la presentación

> **Actualización del método:** VIIRS usa un factor unión/VIIRS independiente. La participante comunicó la validación mensual de VIIRS y el recálculo de Perú con su parquet local; ver [validación VIIRS](validacion-viirs.md) y [cifras](pitch.md). Los resultados y rankings siguen siendo provisionales: la unión no es verdad de campo, la cobertura no está garantizada y la prueba no valida otras zonas ni periodos fuera del solape.


> **Resultado comunicado:** estas cifras proceden de la salida de `numeros_pitch.py` ejecutada
> por la participante con el método corregido y su parquet local. El parquet del repositorio es otro
> conjunto. Los totales y el orden de años son provisionales, especialmente con años incompletos.

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

Con el método corregido, el programa produjo **2 465 147 celdas-día armonizadas mensuales**;
incluyen estimaciones, no son 2 465 147 observaciones ni incendios. El listado mensual obtenido es
2005: 155 310; 2024: 134 932; 2020: 132 140; 2022: 132 084; 2016: 124 219. **2026 está
incompleto** (hasta el 1 de noviembre); 2005 incluye estimaciones. La serie semanal dio un total de
2 477 221 y otro orden: 2005, 2024, 2022, 2020 y 2016. No declarar un año ganador definitivo.

Según esa serie mensual, agosto, septiembre y octubre representan **24,6 %, 31,7 % y 12,6 %**,
respectivamente; septiembre es el máximo. Son porcentajes provisionales que dependen del conjunto
y el método, no un pronóstico para un año o lugar concreto.

### Limitación importante que revisar antes de usar el ranking o los totales

La versión anterior multiplicaba VIIRS por el factor unión/MODIS, lo que podía inflar los valores.
Ahora se usa un factor unión/VIIRS independiente o se indica que no hay estimación si faltan datos.
La participante ya ejecutó la validación VIIRS mensual y el recálculo con su archivo local. El ranking
sigue siendo provisional: la evaluación no garantiza cobertura ni valida todos los periodos o zonas.

## Validación retrospectiva (reproducible)

La participante ejecutó la validación sobre su **parquet local de 2 212 061 filas** en Perú. Al
retirar cada año completo del solape de la calibración y estimarlo desde MODIS, la **mediana del
error absoluto porcentual anual fue 4,94 % en 14 años (2012–2025)**, frente a la unión observada
MODIS+VIIRS. El error promedio (MAPE) fue **7,01 %**, el ponderado (WAPE) **7,04 %** y el mayor error
anual **19,70 %** (2025). Ver [los resultados por año](validacion-retrospectiva.md).

> «Validamos retrospectivamente 14 años del solape: retiramos cada año de la calibración y lo
> estimamos desde MODIS. La mediana del error absoluto anual fue 4,94 %, frente a la unión de los
> dos satélites».

La participante también validó VIIRS → unión con el mismo parquet: mediana del error absoluto anual
**1,02 %** en 14 años (2012–2025), MAPE **1,20 %**, WAPE **1,18 %** y máximo **3,34 %** (2025).
Ver [la tabla y los límites](validacion-viirs.md). No confundir este resultado con el de MODIS.

El entrenamiento puede incluir años posteriores al año evaluado. La unión de sensores **no es verdad
de campo**: esto no mide la precisión de detección de incendios. Tampoco valida directamente las
estimaciones anteriores a 2012 ni valida por sí sola las estimaciones desde VIIRS. Cada año evaluado tiene
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

- [x] Ejecutar la validación mensual VIIRS para Perú y recalcular con el parquet local; mantener los límites de la prueba.
- [ ] Revisar calendario, zona, fechas, mapa y descarga de reportes con los datos locales.
- [ ] Comprobar fecha y cobertura de los datos recientes antes de interpretarlos.
- [ ] Probar aviso y pin en Telegram; no mostrar credenciales en pantalla.
- [ ] Revisar el texto de entrega y distinguir resultados observados de estimaciones.
