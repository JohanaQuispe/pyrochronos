# Lista de entrega

> **Actualización del método:** VIIRS usa un factor unión/VIIRS independiente. La participante comunicó la validación mensual de VIIRS y el recálculo de Perú con su parquet local; ver [validación VIIRS](validacion-viirs.md) y [cifras](pitch.md). Los resultados y rankings siguen siendo provisionales: la unión no es verdad de campo, la cobertura no está garantizada y la prueba no valida otras zonas ni periodos fuera del solape.


## Datos usados

La participante ejecutó `python backend\scripts\numeros_pitch.py` sobre su parquet local: **2 212 061
registros**, del **11-11-2000 al 01-11-2026**; 579 777 MODIS y 1 632 284 VIIRS. El parquet incluido
en el repositorio es distinto; no sustituir los datos locales ni reconstruirlos desde archivos FIRMS.
Las cifras calculadas y sus límites están en [`pitch.md`](pitch.md).

La participante comunicó la validación mensual VIIRS para Perú y el recálculo con sus datos locales.
Sus resultados y límites están en `validacion-viirs.md`. Los totales y rankings son provisionales y
el año 2026 está incompleto.

## Texto de propuesta (borrador; revisar antes de enviar)

**Nombre:** PyroChronos

**Una frase:** Calendario de focos de calor para brigadas de bomberos: compara datos de MODIS y VIIRS
y apoya la vigilancia por zona.

**Descripción:** PyroChronos reúne detecciones satelitales de NASA FIRMS en una cuadrícula común y
muestra un calendario de estacionalidad y anomalías históricas. En los datos locales de la
participante contiene 2 212 061 detecciones entre noviembre de 2000 y noviembre de 2026. El sistema
incluye una capa de datos recientes previamente descargados y un bot de Telegram que puede avisar
sobre focos intensos cercanos a una ubicación compartida, con coordenadas y botones de confirmación.
En validaciones retrospectivas de 14 años del solape, la estimación mensual de celdas-día desde MODIS
tuvo una mediana de error absoluto anual de 4,94 % y desde VIIRS de 1,02 %, frente a la unión de los
sensores, no frente a incendios confirmados.
Una detección no es necesariamente un incendio. La armonización y las alertas requieren las
verificaciones indicadas en `docs/pitch.md` y `docs/verificado.md`. No predice incendios ni sustituye
un aviso oficial.

**Público objetivo:** brigadas de bomberos forestales. Otros usuarios son alcance futuro no validado.

**Tecnologías:** Python (FastAPI, pandas), React (Vite, Tailwind, Leaflet), Parquet, Telegram Bot API,
NASA FIRMS y NASA POWER. Licencia MIT.

## Antes de entregar

- [x] Corregir el factor VIIRS y ejecutar validación mensual y recálculo locales; conservar los límites.
- [ ] Revisar el mapa, filtros y reportes con los datos locales; no confundir historial con focos activos.
- [ ] Comprobar descarga y fecha NRT; probar el nuevo mensaje y pin de Telegram en el teléfono.
- [ ] Revisar que `.env` y credenciales no aparezcan en el repositorio, la pantalla ni la documentación.
- [ ] Verificar propuesta, capturas y alcance; grabar únicamente cuando la aplicación esté lista.

No afirmar que hay viento puntual, rutas, cercanía a viviendas, prioridad por exposición o modo sin
señal: todavía no están implementados. No afirmar que el ranking anual es definitivo ni que 2026 es
un año completo.
