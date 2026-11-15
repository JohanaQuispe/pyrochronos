# Declaración de uso de inteligencia artificial

El reto exige declarar el uso de IA. Esto es lo que se usó y para qué.

## Resumen

| Uso | Herramienta | Dónde | Cómo se revisó |
|---|---|---|---|
| Asistencia de programación (estructura del código, borradores de funciones, redacción de textos y documentación) | Asistente de IA en el editor (Arena.ai / Agent Mode) | Todo el repositorio | Cada función se ejecutó con datos reales, se cubrió con pruebas automáticas y se revisó a mano antes de usarla |
| Verificación de parámetros del servicio FIRMS (máximo de días por consulta, columnas, fechas de inicio) | Búsqueda web + páginas oficiales de NASA | `docs/verificado.md` | Contraste contra la página oficial del API y contra las cabeceras reales de los archivos |

## Lo que la IA **no** hace en el producto

- **No calcula ningún número.** Todo lo que se muestra lo calculan `backend/pyro/*` con pandas/NumPy
  a partir de los CSV de NASA.
- **No hay modelo de lenguaje en la aplicación.** El bloque "En una frase" son plantillas que
  rellenan cifras calculadas por el sistema (`backend/pyro/summary.py`) y el boletín de Telegram usa
  las mismas plantillas (`backend/pyro/notify.py`). Por eso no puede inventar cifras.
- **No se envía ningún dato del usuario a ningún servicio externo.**

## Por qué se decidió así

Se evaluó un asistente de preguntas con un modelo generativo (Groq/Gemini, claves en el servidor).
Se **descartó para esta entrega** por dos razones honestas: (1) el tiempo alcanzaba mejor para
asegurar el calendario, el mapa, las anomalías y el CSV; (2) un asistente que redacta cifras es un
riesgo si no se puede verificar cada respuesta. La arquitectura deja el hueco preparado: el payload
de `/api/calendar` ya contiene todo lo que un redactor necesitaría, y `summary.py` es el único punto
donde se genera texto.

## Reglas que se respetaron

- Ninguna clave de API en el código ni en el navegador: solo en variables de entorno
  (`FIRMS_MAP_KEY`, `TELEGRAM_BOT_TOKEN`) y `.env` está en `.gitignore`.
- Nada simulado: lo que la interfaz muestra está construido y se puede ejecutar.
- Licencia de código abierto (MIT) y datos de dominio público.
