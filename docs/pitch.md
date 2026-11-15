# Guion de la demo (3 minutos) y preguntas del jurado

## Antes de empezar (30 s de preparación)

1. Servidor arriba: `python -m uvicorn api.main:app --app-dir backend --port 8000`.
2. Navegador en `http://localhost:8000`, ventana ancha, zoom 100 %.
3. Zona = **Perú**, rango = **todo el historial**, vista **Mes**.
4. Ten a mano la carpeta `docs/` por si preguntan por la metodología.

## Guion (minuto a minuto)

**0:00 — El problema, en una frase.**
> "Dos satélites llevan 25 años fotografiando incendios. Pero uno ve 1 km y el otro 375 m, así que
> sus registros no se pueden comparar. Sin arreglar eso, nadie puede decir si un año fue peor que
> otro. PyroChronos los armoniza en un solo calendario."

**0:20 — El calendario (lo que se mira primero).**
Señala las filas naranjas de agosto, septiembre y octubre:
> "Cada fila es un año, cada columna un mes. En Perú la temporada de fuego es agosto–octubre, con
> septiembre como pico. Eso lo ve cualquier persona en menos de un minuto."

**0:45 — La armonización, con números.**
Abre "Cómo se armonizó":
> "En los años en que ambos satélites coinciden, el conjunto ve 5,8 veces más celdas-día que MODIS
> solo. Sus series correlacionan 0,98: miden lo mismo a distinta escala. Por eso el historial
> anterior a 2012 se estima con ese factor por mes y se dibuja **rayado**, con su banda de
> incertidumbre. Nada de lo estimado se muestra como si fuera observado."

**1:10 — Anomalías.**
Señala un ◆ y un ▲:
> "Cada mes se compara con el mismo mes de los demás años, sin incluirse a sí mismo. Septiembre de
> 2024 quedó muy por encima de lo normal: 30 400 celdas-día frente a una mediana cercana a 12 000.
> El color no es lo único: hay borde, símbolo y texto para lector de pantalla."

**1:35 — Zona y mapa.**
Cambia a **Madre de Dios** y luego dibuja un rectángulo:
> "El mismo análisis para otra zona, con los focos del periodo en el mapa y el CSV descargable."

**2:00 — Descargas y honestidad.**
> "Dos CSV: los focos crudos de la búsqueda y la serie armonizada con su percentil. Y aquí está lo
> que no sabemos: la serie termina en diciembre de 2025, los años recientes pueden reprocesarse y
> el factor asume que la sensibilidad relativa entre satélites es estable."

**2:20 — Extra para guardaparques.**
> "El mismo cálculo genera un boletín de texto para un grupo de Telegram, con las cifras que calcula
> el sistema. No es una alerta en tiempo real y lo dice el propio mensaje."

**2:35 — Cierre.**
> "En resumen: una persona elige su zona y entiende su temporada de fuego y sus años anormales en
> menos de un minuto; la armonización está validada en los 14 años de solape y muestra su
> incertidumbre; y todo se puede descargar."

## Preguntas probables del jurado (y respuestas honestas)

**¿Por qué celdas-día y no número de focos?**
Porque VIIRS tiene 375 m y observa dos veces por noche: contar detecciones infla los años recientes.
La celda-día cuenta una celda una vez por día y satélite. La medida de focos está igual disponible
como segunda cifra, y la interfaz explica la diferencia.

**¿Cómo sabemos que la armonización es correcta?**
No lo sabemos con certeza: la validamos donde se puede. En los 14 años de solape las dos series
correlacionan 0,96–0,98 y el cociente es estable mes a mes (4,1 a 7,1). Publicamos el factor, su
banda p25–p75 y la concordancia. Donde hay estimación, se marca.

**¿Cuál es el año más activo?**
2005, con ≈95 700 celdas-día armonizadas, por delante de 2020 (84 000). 2005 es estimado, así que
comparamos contra el extremo inferior de su banda (87 100): sigue por delante. Cuando el segundo año
cae dentro de la banda, la tarjeta dice "empate técnico" en lugar de dar un ganador falso.

**¿Por qué la serie termina en 2025 y no en hoy?**
Porque usamos el archivo por país de procesamiento estándar, que se publica por año completo. Los
meses recientes se descargan con `download_zone.py` y la clave de FIRMS (bloques de 5 días). Además,
Suomi-NPP dejó de entregar datos el 2 de noviembre de 2026: la continuidad futura pasa por
NOAA-20/21, y eso está declarado como trabajo siguiente.

**¿Esto sirve para bomberos en un incendio?**
No, y no lo decimos. Es análisis histórico: patrones, temporadas y anomalías. Para respuesta
inmediata existen los servicios de FIRMS en tiempo real.

**¿Cuánto de esto es IA?**
La IA se usó como asistente de programación y está declarada en `docs/ia.md`. El producto no tiene
modelo de lenguaje: los textos se arman con plantillas sobre cifras calculadas.

## Lista de comprobación antes de presentar

- [ ] El servidor responde en `/api/health`.
- [ ] El calendario carga en menos de 1 s.
- [ ] Los dos CSV descargan.
- [ ] La zona dibujada funciona.
- [ ] Modo **Semana** y medida **Focos detectados** se ven bien (por si preguntan).
- [ ] Modo **Solo MODIS** muestra el factor como "no aplica" (transparencia del método).
- [ ] Navegación solo con teclado (Tab y flechas en el calendario).
