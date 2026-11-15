# Semáforo de temporada y avisos para guardaparques

## La idea en una frase

El calendario dice **cuándo arde históricamente** una zona; el semáforo convierte eso en un aviso
anticipado: *"estás entrando en la ventana en la que, en los últimos 25 años, se concentraron los
incendios de tu zona"*.

## Qué hace el semáforo (`backend/pyro/alerts.py`)

1. Toma la climatología **semanal** de la propia zona: para cada semana del año, la mediana histórica
   (y el percentil 90) de celdas‑día armonizadas.
2. Identifica la **semana pico** (la de mayor mediana).
3. Mira la semana actual y las **4 siguientes** y calcula qué fracción del pico representan.
4. Clasifica:

| Nivel | Criterio | Qué significa |
|---|---|---|
| **Ventana crítica** | alguna de las próximas 4 semanas alcanza ≥ 75 % del pico | es la época en la que se concentran los incendios |
| **Vigilancia** | ≥ 40 % del pico | la temporada ya empezó |
| **Fuera de temporada** | < 40 % del pico | históricamente no es época de incendios |

5. Si hay datos recientes cargados (NRT), añade la comparación **observada**: focos de los últimos 7
   días frente a la mediana histórica de esa semana. Si la actividad observada es 1,5× lo normal, sube
   a vigilancia; a 2,5×, a ventana crítica.

Ejemplo real (Madre de Dios, referencia 2026‑09‑08): `critico`, semana 36, pico histórico en la 38,
ratio 1,0 → *"se espera el 100 % de la actividad del pico histórico"*.

## Qué NO hace (y por eso el texto lo dice)

- **No predice igniciones.** Un satélite detecta calor **después** de que el fuego empezó.
- **No es un pronóstico meteorológico.** No usa viento, humedad ni temperatura: solo la historia de la zona.
- **No sustituye un aviso oficial.** Es una señal para priorizar el monitoreo.
- Los focos NRT llegan con **~3 horas** de latencia (más en zonas nubladas), y los incendios pequeños
  o bajo nubes pueden no detectarse.

## Cómo activar el modo "casi en tiempo real" (en tu máquina, no en este contenedor)

Este entorno de desarrollo **no tiene salida a `firms.modaps.eosdis.nasa.gov`**, así que los focos
recientes no se pueden descargar aquí. En tu máquina, con la `MAP_KEY` gratuita de FIRMS:

```bash
export FIRMS_MAP_KEY=...        # en .env, nunca en el código ni en el navegador
python backend/scripts/download_recent.py --zone madrededios --days 3
python backend/scripts/alert.py --zone madrededios        # ver el semáforo
```

La web detecta los datos automáticamente: aparece la etiqueta *"reciente: N focos"* en el semáforo y
`/api/recent` los expone. Fuentes NRT usadas: `VIIRS_SNPP_NRT`, `VIIRS_NOAA20_NRT`, `MODIS_NRT`.

### Vigilancia automática por Telegram

**Crear el bot (una sola vez, a mano).** Telegram solo permite crear bots desde @BotFather,
así que ese paso no se puede automatizar. Sí se automatiza todo lo demás:

```bash
python backend/scripts/telegram_setup.py --guide       # los 5 pasos de @BotFather
# (crear el bot en el telefono, abrir su chat y pulsar /start)
python backend/scripts/telegram_setup.py --check       # getMe: ¿el token es válido?
python backend/scripts/telegram_setup.py --chat-id     # getUpdates: cuál es tu chat_id
python backend/scripts/telegram_setup.py --write-env   # guarda en .env con permisos 600
python backend/scripts/telegram_setup.py --test        # manda un mensaje de prueba
```

- El token **nunca** se imprime completo ni entra en el código: se lee del entorno o de `.env`
  (que está en `.gitignore`).
- `.env` no se carga solo: `set -a && . ./.env && set +a` antes de usar los demás scripts.
- Un chat de grupo (id negativo) sirve igual: añade el bot al grupo, menciónalo una vez y `--chat-id`
  lo mostrará.

**Vigilar y avisar:**

```bash
export TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=...
python backend/scripts/watch_alerts.py --zones peru,madrededios --loop 3600 --send
```

- Revisa cada hora y **solo avisa cuando el nivel sube** (guarda estado en `data/derived/alert_state.json`).
- El mensaje lleva las razones, la acción y el descargo de responsabilidad.
- Si no hay datos recientes cargados, **no inventa** detecciones: avisa solo con la estacionalidad.

## Arquitectura recomendada para el aviso en producción

```
cron cada hora:
  1. download_recent.py        (FIRMS NRT, 1-3 días, zona vigilada)
  2. watch_alerts.py --send    (semáforo + Telegram si sube de nivel)
  3. (opcional) NASA POWER     (déficit de lluvia y temperatura para el contexto de riesgo)
```

## Siguiente paso honesto (no implementado)

**Contexto meteorológico con NASA POWER** (sin clave): temperatura máxima, humedad y déficit de lluvia
de los últimos 30 días por punto. Permitiría pasar de "es época de incendios" a "es época y además el
combustible está seco". **No está en esta entrega** porque el entorno de construcción no tiene salida a
`power.larc.nasa.gov` y no quisimos mostrar una función sin verificar.
