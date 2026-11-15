# Guion de la demo (3 minutos) y preguntas del jurado

## Antes de empezar (30 s de preparación)

1. Servidor arriba: `python -m uvicorn api.main:app --app-dir backend --port 8000`.
2. Navegador en `http://localhost:8000`, ventana ancha, zoom 100 %.
3. Zona = **Perú**, rango = **todo el historial**, vista **Mes**, medida **Celdas‑día**.
4. Ten abierta la carpeta `docs/` por si preguntan por la metodología.

## Guion (minuto a minuto)

**0:00 — El problema, en una frase.**
> "Dos satélites llevan 25 años fotografiando incendios. Uno ve 1 km, el otro 375 m, así que sus
> registros no se pueden comparar. Sin arreglar eso, nadie puede decir si un año fue peor que otro.
> PyroChronos los armoniza en un solo calendario y lo convierte en un aviso para quien está en el campo."

**0:20 — El semáforo (lo primero que se ve).**
> "Un guardaparque no necesita un gráfico: necesita saber si está entrando en su temporada de riesgo.
> Hoy, en Perú, el semáforo dice 'fuera de temporada'. Si me pongo en la semana 36…"
> *(abre «Qué hacer», cambia la fecha de referencia a una semana de septiembre)*
> "…pasa a **ventana crítica**: la semana 36 es la de mayor actividad histórica. Y me dice qué hacer,
> con las razones y sus límites."

**0:50 — El calendario (lo que se mira primero).**
> "Cada fila es un año, cada columna un mes. En Perú la temporada es agosto–octubre, con septiembre
> como pico. Eso lo entiende cualquier persona en menos de un minuto."

**1:10 — La armonización, con números.**
Abre "Cómo se armonizó":
> "En los años en que ambos satélites coinciden, el conjunto ve 5,8 veces más celdas‑día que MODIS
> solo, y sus series correlacionan 0,98: miden lo mismo a distinta escala. Por eso el historial anterior
> a 2012 se estima con ese factor y se dibuja **rayado**, con su banda de incertidumbre. Lo estimado
> nunca se muestra como si fuera observado."

**1:30 — Anomalías.**
> "Cada mes se compara con el mismo mes de los demás años, sin incluirse a sí mismo. Septiembre de 2024
> quedó muy por encima: 30 400 celdas‑día frente a una mediana cercana a 12 000. El color no es lo único:
> hay borde, símbolo y texto para lector de pantalla, y una paleta especial para daltonismo."

**1:50 — Zona y mapa.**
> *(cambia a **Madre de Dios**, luego dibuja un rectángulo)*
> "El mismo análisis para otra zona, con los focos del periodo en el mapa y sus coordenadas exactas."

**2:10 — Descargas y honestidad.**
> *(abre "Descargar ▾")* "CSV de focos, CSV de la serie armonizada, imagen del calendario y **reporte
> ejecutivo** listo para imprimir o guardar como PDF: una hoja con el semáforo, las cifras y el método."
> "Y aquí está lo que no sabemos: la serie termina en diciembre de 2025, los años recientes pueden
> reprocesarse y el factor asume que la sensibilidad relativa entre satélites es estable."

**2:30 — El aviso que llega al grupo.**
> "El mismo cálculo se puede correr cada hora y mandar por Telegram a un grupo de guardaparques,
> **solo cuando el nivel sube**. No es detección en tiempo real: los satélites ven el calor después de
> que el fuego empezó, y el mensaje lo dice. Lo que aporta es anticipación estacional y un aviso que
> llega en horas, no en días."

**2:45 — Cierre.**
> "En resumen: una persona elige su zona y entiende su temporada y sus años anormales en menos de un
> minuto; la armonización está validada en 14 años de solape y declara su incertidumbre; y de ahí salen
> un CSV, un reporte y un aviso para quien tiene que actuar."

## Preguntas probables del jurado

**¿Esto es tiempo real?**
No, y no lo decimos. Hay dos piezas: el **calendario** (histórico, procesamiento estándar, hasta
diciembre de 2025) y el **modo reciente** con las fuentes NRT de FIRMS (latencia típica ~3 h), que se
activa con una clave gratuita y un comando. La demo corre con el histórico porque este entorno no tiene
salida a internet.

**¿Entonces sirve para bomberos?**
Sirve para **anticipar** (semáforo de temporada, ventana crítica, años anómalos) y para **priorizar
monitoreo**. Para respuesta inmediata existen los servicios de FIRMS en tiempo real; nosotros no los
duplicamos, los convertimos en calendario comparable y en aviso legible.

**¿Por qué celdas‑día y no número de focos?**
Porque VIIRS tiene 375 m y observa dos veces por noche: contar detecciones infla los años recientes.
La celda‑día cuenta una celda una vez por día y satélite. La medida de focos está igual disponible, y la
interfaz explica la diferencia.

**¿Cómo sabemos que la armonización es correcta?**
No lo sabemos con certeza: la validamos donde se puede. En los 14 años de solape las series
correlacionan 0,96–0,98 y el cociente es estable mes a mes (4,1 a 7,1). Publicamos el factor, su banda
p25–p75 y la concordancia; donde hay estimación, se marca.

**¿Cuál es el año más activo?**
2005, con ≈95 700 celdas‑día armonizadas, por delante de 2020 (84 000). 2005 es estimado, así que
comparamos contra el extremo inferior de su banda (87 100): sigue por delante. Cuando el segundo año cae
dentro de la banda, la tarjeta dice "empate técnico" en lugar de dar un ganador falso.

**¿Cuánto de esto es IA?**
La IA se usó como asistente de programación (declarado en `docs/ia.md`). El producto no tiene modelo de
lenguaje: los textos se arman con plantillas sobre cifras calculadas, y el semáforo es aritmética.

## Lista de comprobación antes de presentar

- [ ] `/api/health` responde y el calendario carga en menos de 1 s.
- [ ] El semáforo cambia al poner una fecha de referencia en septiembre (y vuelve con "Volver a la semana actual").
- [ ] Los dos CSV descargan y el reporte ejecutivo se abre e imprime bien.
- [ ] La zona dibujada funciona.
- [ ] Modo **Semana**, medida **Focos** y paleta **Daltonismo** se ven bien.
- [ ] Modo **Solo MODIS** muestra el factor como "no aplica" (transparencia del método).
- [ ] Navegación solo con teclado (Tab; flechas dentro del calendario).
