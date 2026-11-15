# Público objetivo: brigadas de bomberos (alcance de esta entrega)

## La persona

**Jefe de brigada o bombero forestal** de una zona con temporada seca marcada (en el Perú: amazonía
sur y central, valles interandinos). Trabaja con pocos recursos, turnos largos y decisiones que se
toman con información incompleta:

- No sabe con precisión **cuándo arranca** su temporada: cada año el pico se mueve una o dos semanas.
- No puede comparar el año actual con los anteriores: los registros de MODIS y VIIRS **no son
  comparables** entre sí (1 km contra 375 m, sensibilidades distintas).
- Se entera de los focos **cuando alguien llama**, no cuando aparece el punto de calor.
- Cuando por fin sale, muchas veces era quema agrícola o una falsa alarma.

## Qué le resuelve PyroChronos (y en qué orden)

| Pregunta del brigadista | Cómo se responde |
|---|---|
| ¿Ya empieza mi temporada? | **Semáforo** con la semana del año y el pico histórico de *su* zona. |
| ¿Este año viene peor? | **Cifras y anomalías** comparadas con la mediana histórica de la misma zona. |
| ¿Dónde aprieto primero? | **Calendario y mapa**: meses y celdas con más actividad, con el área dibujada a mano. |
| ¿Y ahora mismo? | **Bot de Telegram**: cuando un foco intenso cae a menos de X km, aviso con distancia, rumbo, pin y un botón para confirmar. |
| ¿Qué llevo al comité? | **Reporte imprimible** en una página, con las cifras y los límites del método. |

El valor central es **anticiparse a la temporada**: saber que la semana 36 es la de mayor actividad
histórica permite adelantar turnos, revisar equipos y preposicionar brigadas *antes* de que
aparezcan los focos. Y el bot reduce el tiempo entre "hay un punto de calor" y "alguien confirma qué
es", que es donde se pierden las horas buenas.

## Qué NO hace (se dice siempre)

- **No predice incendios.** Los satélites detectan calor **después** de que el fuego empezó.
- **No es un aviso oficial** ni reemplaza a la autoridad de emergencias.
- **No detecta en tiempo real**: los datos tienen ~3 h de latencia y el histórico cierra el día anterior.
- **No confirma un incendio**: un píxel de fuego puede ser quema agrícola, una fuente industrial o
  una falsa alarma. Por eso el bot pide confirmación humana.

## Alcance de esta entrega

- **Dentro:** brigadas de bomberos forestales y comités de emergencia de una zona concreta del Perú
  (Perú, Madre de Dios, Ucayali, Loreto y cualquier área dibujada hasta 300 grados²).
- **Fuera (deliberadamente, para no prometer lo que no está probado):** guardaparques como usuario
  primario, agricultores, municipios, aseguradoras, turismo. La app y el bot ya les servirían, pero
  **no están diseñados ni validados con ellos**.
- **Siguiente paso natural, en este orden:**
  1. **Guardaparques** de áreas protegidas: mismas funciones, con capas de límites de ANP y reporte
     por puesto de control.
  2. **Agricultores y asociaciones**: calendario de quema agrícola y aviso de "tu parcela está en
     zona de quema permitida" para reducir falsas alarmas.
  3. **Municipios y defensa civil**: tablero público de riesgo estacional y reporte mensual.
  4. **Brigadas de otros países**: basta cambiar los archivos por país de FIRMS (el motor ya es
     genérico; solo está cargado Perú).

## Mensajes clave (para el video y el formulario)

1. "Dos satélites, un solo calendario: así se puede comparar 2005 con 2024."
2. "El semáforo dice en qué punto de la temporada está tu zona, no cuándo se va a incendiar."
3. "El bot no adivina: avisa cuando el satélite ve un foco intenso cerca de ti y te pide confirmarlo."
4. "Los años anteriores a 2012 son estimados y se dibujan rayados: nunca fingimos datos que no hay."

## Frases que no se usan

- ❌ "Predicción de incendios" · ❌ "Detección en tiempo real" · ❌ "Alerta oficial"
- ❌ "Inteligencia artificial que anticipa el fuego" (la IA no interviene en el cálculo)
- ✅ "Anticiparse a la temporada" · ✅ "Detección satelital casi en tiempo real (~3 h)" ·
  ✅ "Apoyo a la decisión, con confirmación en campo"
