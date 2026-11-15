# Lista de entrega (domingo, hasta las 24:00 de Lima)

## 1. Lo que ya está listo en este repositorio

- [x] Código completo en Python (FastAPI + pandas) y React (Vite + Tailwind + Leaflet).
- [x] Licencia MIT (`LICENSE`) y declaración de IA (`docs/ia.md`).
- [x] Metodología (`docs/metodologia.md`), procedencia de datos (`docs/procedencia.md`),
      verificado / POR VERIFICAR (`docs/verificado.md`) y guion del pitch (`docs/pitch.md`).
- [x] Datos reales cargados (`data/derived/detections.parquet`): 1 323 016 focos, 2000-11 a 2025-12.
- [x] 74 pruebas de backend + 2 pruebas de humo del frontend (motor, API, bot y POWER).
- [x] Frontend compilado en `backend/webapp` (no hace falta `npm install` para la demo).

## 1.b Textos listos para el formulario (copiar y pegar)

**Nombre:** PyroChronos

**Una frase (≤140 caracteres):**
> Calendario de fuego para brigadas de bomberos: armoniza 25 años de MODIS y VIIRS para anticipar la
> temporada y confirmar focos en campo.

**Descripción corta (≤300 caracteres):**
> Dos satélites, dos escalas: MODIS (1 km, desde 2000) y VIIRS (375 m, desde 2012) no se pueden
> comparar directamente. PyroChronos los armoniza en un calendario común y lo convierte en un semáforo
> de temporada y un bot que avisa a la brigada cuando un foco intenso aparece cerca.

**Descripción larga:**
> Las brigadas de bomberos forestales no saben con precisión cuándo arranca su temporada, no pueden
> comparar este año con los anteriores (los registros de MODIS y VIIRS no son comparables) y se enteran
> de los focos por una llamada. PyroChronos armoniza 25 años de focos de calor de NASA FIRMS en una
> cuadrícula común de 0,01°, con un factor de calibración medido en los 14 años de solape (5,83 veces,
> r = 0,98) y banda de incertidumbre; los años anteriores a 2012 se marcan como estimados. Sobre esa
> base calcula estacionalidad, anomalías por percentil y un semáforo de temporada por zona, y lo lleva
> al campo con un bot de Telegram: cuando un foco supera el percentil 95 de intensidad de su zona y cae
> dentro del radio del usuario, envía distancia, rumbo, un pin y tres botones para confirmar qué era
> (fuego real, quema agrícola o falsa alarma). El sistema no predice incendios ni sustituye un aviso
> oficial, y lo dice en cada pantalla y en cada mensaje.

**Público objetivo:** brigadas de bomberos forestales y comités de emergencia del Perú (amazonía sur y
central). Guardaparques, agricultores y municipios son el siguiente alcance
([`publico-objetivo.md`](publico-objetivo.md)).

**Tecnologías:** Python (FastAPI, pandas, NumPy), React (Vite, Tailwind, Leaflet), Parquet, Bot API de
Telegram, NASA FIRMS y NASA POWER. Licencia MIT.

## 2. Lo que falta hacer a mano (30-45 min)

0. **Probar el semáforo**: abre "Qué hacer" y pon una fecha de referencia en septiembre (Madre de Dios)
   para mostrar la ventana crítica. Vuelve con "Volver a la semana actual" antes de seguir.
1. **Subir el repositorio a GitHub público** (o ponerlo público si ya está).
   Verifica que `.env` **no** esté en el repo y que la licencia se vea en la portada.
2. **Grabar el video de 3 minutos** siguiendo `docs/pitch.md`:
   - Graba la pantalla con la app abierta y en zona Perú.
   - Muestra: semáforo → calendario → "Cómo se armonizó" → septiembre de 2024 → cambiar de zona →
     descargar CSV y abrir el reporte ejecutivo.
   - Si no quieres hablar de corrido, lee el guion: está escrito para 3 minutos.
3. **Escribir el texto de la propuesta** con: problema, qué construimos, cómo se armoniza,
   qué está validado y qué no. Puedes copiar de `README.md` y `docs/metodologia.md`.
4. **Probar la demo de punta a punta una vez más**:
   `python -m uvicorn api.main:app --app-dir backend --port 8000` y recorrer la lista del final de
   `docs/pitch.md`.
5. **Capturar 2-3 imágenes** del calendario (una de Perú, una de Madre de Dios) para la propuesta.
   Usa el botón "↓ Imagen del calendario (PNG)".

## 3. Si te sobra tiempo (en este orden)

1. Añadir los meses de 2026 descargándolos con tu clave (así la serie llega "hasta hoy"):
   ```bash
   export FIRMS_MAP_KEY=tu_clave
   python backend/scripts/download_zone.py --recent 400
   python backend/scripts/build_dataset.py --raw data/raw
   ```
   Después reinicia el servidor: la cobertura se detecta sola.
2. Activar el envío real del boletín de Telegram (`scripts/notify_telegram.py --send`).
3. Grabar el boletín llegando al grupo como cierre del video.

## 4. Qué NO decir en la demo

- No digas "tiempo real" ni "alerta temprana en vivo": es análisis histórico y la app lo dice.
- No digas que el año más activo es indiscutible: 2005 es estimado; explica el empate técnico.
- No digas que la armonización es perfecta: muestra el factor, su banda y la concordancia.
