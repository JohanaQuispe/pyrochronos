# Bot de Telegram: guía rápida

El bot puede enviar avisos sobre detecciones de calor cercanas a una ubicación compartida. No confirma incendios ni reemplaza una alerta oficial.

## 1. Preparar las claves

- Obtén una [clave de NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/api/map_key/).
- Crea un bot en [BotFather](https://t.me/BotFather) y guarda su token.
- En la carpeta del proyecto, copia `.env.example` como `.env` **si todavía no tienes `.env`**. Escribe allí `FIRMS_MAP_KEY` y `TELEGRAM_BOT_TOKEN`.

En PowerShell, para crear el archivo sin sobrescribir uno existente:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

No compartas el archivo, las claves ni capturas donde aparezcan. El bot carga `.env` al iniciarse. `TELEGRAM_CHAT_ID` solo es necesario para la demo de envío `--send-demo`, no para los avisos por ubicación.

## 2. Iniciar el bot

Con las dependencias instaladas según el [README](../README.md), abre una terminal en la carpeta del proyecto:

```bash
python backend/scripts/bot.py --poll --auto-refresh --zone peru
```

En Windows puedes usar `python backend\scripts\bot.py --poll --auto-refresh --zone peru`. Deja la terminal abierta y no ejecutes dos procesos del mismo bot. Para incluir una confirmación periódica de vigilancia, añade `--heartbeat` al comando.

En Telegram abre el bot **en privado**, envía `/start`, comparte tu ubicación y elige el radio de aviso. Puedes consultar `/estado`, usar `/language en` para inglés o `/idioma es` para español. Cambiar la zona en la web no modifica la zona vigilada por el bot.

## 3. Comprobar el funcionamiento

El bot intenta descargar FIRMS y revisar detecciones aproximadamente cada 15 minutos. En otra terminal puedes ejecutar:

```bash
python backend/scripts/bot.py --check-live --zone peru
```

El diagnóstico no envía mensajes ni cambia el historial. Muestra si la descarga está fresca y cubre la zona, y si hay coincidencias pendientes. La llegada de un mensaje de estado o una coincidencia en el diagnóstico **no demuestra la entrega de una alerta real**. Consulta la [guía de comprobación](comprobacion-alerta-real.md).

Si el proceso se detiene, la computadora se suspende o falla la conexión, el bot deja de vigilar. Una confirmación de estado no implica que no haya incendios. El bot filtra por distancia e intensidad; no avisa de todas las detecciones.

Las ubicaciones y el historial se guardan localmente. **No publiques la web con datos personales sin proteger el acceso a la API.** En un grupo, todos pueden ver lo que se comparte; por privacidad se recomienda el chat privado.
