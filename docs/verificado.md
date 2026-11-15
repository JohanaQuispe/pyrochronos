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
| **Un bot real de Telegram entrega los mensajes de PyroChronos** | La participante ejecutó `telegram_setup.py --test` el 2026-11-15 y el mensaje llegó a su teléfono (token válido, `chat_id` correcto, `sendMessage` funcionando) |

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
7. **El boletín real con cifras no se ha enviado todavía a Telegram.** Lo confirmado es el mensaje
   de prueba; el texto largo (`notify_telegram.py --send`) usa Markdown y hay un reintento
   automático en texto plano si Telegram rechaza el formato, pero **ese reintento no se ha visto
   funcionar contra el servicio real** (solo con una respuesta 400 simulada en las pruebas).
8. **El aviso automático por hora** (`watch_alerts.py --loop 3600 --send`) no se ha ejecutado
   todavía en un equipo con internet.

## Validación retrospectiva

- Probada con el **parquet del repositorio** (1 323 016 filas): validación mensual con exclusión del
  año evaluado, 14 años (2012–2025), mediana del error absoluto anual **7,63 %**, promedio **7,00 %**
  y máximo **16,54 %**, frente a la unión MODIS+VIIRS. Ver `docs/metodologia.md` para los límites.
- **POR VERIFICAR en el equipo de la participante:** ejecutar `python backend/scripts/validacion_retrospectiva.py`
  con su parquet de 2 212 061 filas. No extrapolar el 7,63 % ni redondearlo a 8 % para esa base.
  La prueba no comprueba incendios de campo, no mide error real anterior a 2012 y no resuelve la
  estimación de VIIRS sin MODIS.

## Cifras locales y armonización

- **Resultado comunicado por la participante:** `numeros_pitch.py` sobre su parquet local informa
  2 212 061 detecciones, desde 2000-11-11 hasta 2026-11-01. No es el parquet del repositorio.
- **POR VERIFICAR antes de presentar totales armonizados o ranking:** en `harmonize`, un periodo con
  VIIRS pero sin MODIS se multiplica por el factor unión/MODIS. Ese factor no está calibrado para
  convertir VIIRS a la unión y puede inflar los resultados. Revisar el método y recalcular con el
  archivo local. Las cifras provisionales están en `docs/pitch.md`.

## Mapa táctico y alertas: límites operativos

- El mapa separa el historial del archivo NRT local. La capa NRT **no se descarga en vivo**;
  hay que comprobar la fecha de descarga y de detección. Sin archivo no significa ausencia de focos.
- El color distingue sensores, no urgencia. El filtro de confianza no confirma un incendio;
  hay que validar por fuentes operativas antes de despachar.
- El aviso del bot selecciona FRP superior al percentil 95 histórico del sensor (y al umbral mínimo),
  no evalúa viviendas, vías ni riesgo de propagación. La distancia es desde la ubicación compartida
  por la persona, no desde un poblado. Las detecciones guardadas contienen fecha UTC, no hora.
- **POR VERIFICAR:** recepción real del nuevo formato del aviso y del pin en Telegram con la descarga
  NRT actualizada. Viento puntual, carreteras, agua, poblados, prioridad por exposición, recurrencia
  local y descarga de mapas sin conexión todavía no están implementados. No usarlos para decidir rutas.

## Consultas en la app y avisos automáticos (pendiente de prueba real)

- La caja de preguntas de la app y el bot usan el mismo respondedor de reglas, no un modelo de IA
  ni un chat de Telegram incrustado. Las preguntas se limitan a datos recientes guardados, temporada,
  sensores y funcionamiento de avisos; no calcula viento, rutas ni cercanía a viviendas.
- El modo `bot.py --poll --auto-refresh` intenta descargar FIRMS cada 15 minutos para la zona elegida.
  Si alguna fuente falla, conserva la descarga anterior y no envía alertas en ese ciclo. El bot solo
  envía detecciones de los últimos tres días UTC si la descarga cubre la zona y tiene hasta seis
  horas. Filtra por distancia y FRP sobre p95 por sensor, con mínimo 20 MW: **no alerta sobre todos
  los focos**. No hay garantía de detección, tiempo de entrega o disponibilidad.
- Las pruebas automáticas simulan FIRMS y Telegram, e incluyen falta de datos, fallos, datos viejos,
  cobertura y duplicados. **POR VERIFICAR:** acceso real a las tres fuentes configuradas, consulta
  en Telegram, actualización en ejecución y recepción de alerta y pin en el teléfono con la cuenta
  de la participante. Es necesario dejar encendido el equipo y el proceso; no es un servicio 24/7.
- La resolución temporal guardada es el día UTC, no el minuto de detección. Un foco de calor puede
  no ser un incendio; no sustituye avisos oficiales ni confirmación en campo.

## Departamentos y conexión

- El selector departamental usa polígonos **simplificados INEI 2007**; fuente, licencia y límites en
  `data/geo/README.md`. No son fronteras oficiales actuales y la precisión cerca de los bordes es
  limitada. Los focos se filtran antes de agregarse en celdas-día. Cada celda fronteriza puede
  contener focos de más de un departamento.
- El filtro de la web no cambia la zona del bot ni el radio de Telegram. La meteorología POWER no
  se ha precargado por departamento; el boletín preexistente solo está disponible en zonas originales.
- Un `Failed to fetch` indica una conexión fallida entre navegador y servidor: no demuestra falta
  de datos. La causa concreta en el equipo de la participante está **POR VERIFICAR**.
- Se corrigió la conversión de fechas de datos NRT para versiones recientes de pandas. La cuenta
  «últimos 7 días» se calcula respecto de la fecha UTC actual, no del último día guardado.
