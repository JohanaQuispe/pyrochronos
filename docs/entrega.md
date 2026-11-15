# Lista de entrega (domingo 12:00)

## 1. Lo que ya está listo en este repositorio

- [x] Código completo en Python (FastAPI + pandas) y React (Vite + Tailwind + Leaflet).
- [x] Licencia MIT (`LICENSE`) y declaración de IA (`docs/ia.md`).
- [x] Metodología (`docs/metodologia.md`), procedencia de datos (`docs/procedencia.md`),
      verificado / POR VERIFICAR (`docs/verificado.md`) y guion del pitch (`docs/pitch.md`).
- [x] Datos reales cargados (`data/derived/detections.parquet`): 1 323 016 focos, 2000-11 a 2025-12.
- [x] 14 pruebas de backend + 2 pruebas de humo del frontend.
- [x] Frontend compilado en `backend/webapp` (no hace falta `npm install` para la demo).

## 2. Lo que falta hacer a mano (30-45 min)

1. **Subir el repositorio a GitHub público** (o ponerlo público si ya está).
   Verifica que `.env` **no** esté en el repo y que la licencia se vea en la portada.
2. **Grabar el video de 3 minutos** siguiendo `docs/pitch.md`:
   - Graba la pantalla con la app abierta y en zona Perú.
   - Muestra: calendario → "Cómo se armonizó" → septiembre de 2024 → cambiar de zona → descargar CSV.
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
