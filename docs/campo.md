# Modo campo: geocercas, pines y validación humana

Lo que hay aquí lleva el calendario histórico al terreno: un bot de Telegram que avisa cuando un
foco **intenso** cae cerca de ti, manda el pin y pide confirmación. Es la parte que convierte un
panel en una herramienta para bomberos y guardaparques.

> **Qué es y qué no es.** Es un aviso sobre detecciones satelitales de calor, con datos de hasta
> 3 h de antigüedad. **No** detecta incendios en tiempo real (los satélites ven el calor cuando ya
> hay fuego), **no** predice igniciones y **no** sustituye un aviso oficial. El mensaje lo dice.

## 1. Encender el bot

```bash
python backend/scripts/telegram_setup.py --guide     # crear el bot en @BotFather
python backend/scripts/telegram_setup.py --check
python backend/scripts/telegram_setup.py --chat-id
python backend/scripts/telegram_setup.py --write-env
set -a && . ./.env && set +a
```

Después:

```bash
python backend/scripts/bot.py --dry-run          # cómo se verá el aviso (sin red)
python backend/scripts/bot.py --send-demo        # manda el ejemplo, marcado DEMO
python backend/scripts/bot.py --poll             # escucha y avisa (bucle)
python backend/scripts/bot.py --poll --once      # una pasada y sale
```

`--poll` hace long polling de la Bot API (sin librerías extra).

**Se usa con botones, sin escribir nada.** La jerga («geocerca», «radio», «centro») no aparece
delante del brigadista: se habla de *dónde estás* y *a cuántos km te aviso*.

| Botón / comando | Qué hace |
|---|---|
| **📍 Compartir mi ubicación** | guarda dónde está la persona (una vez; se puede repetir) |
| **⚙️ Distancia de aviso** | botones de 5 / 10 / 20 / 50 km (también `/distancia 15`) |
| **ℹ️ Mi estado** | dónde estás, tu distancia, focos vigilados y tus confirmaciones |
| **❓ Ayuda** | el texto de ayuda |
| `/start` · `/ayuda` | equivalentes escritos |

Los comandos toleran lo que manda Telegram de verdad: `/radio@mi_bot 15`, `15 km`, `15km`, `7,5`.

### En un grupo de brigada

1. **BotFather** → `/setjoingroups` → `Enable` (el bot puede entrar en grupos).
2. **BotFather** → `/setprivacy` → **`Disable`**. Sin esto el bot **no recibe** la ubicación que
   comparten los miembros: el «modo privacidad» de Telegram solo le deja ver comandos.
3. Quita el bot del grupo y **vuélvelo a añadir**: el cambio de privacidad solo aplica al entrar.
4. Cada bombero pulsa *Compartir mi ubicación*: su posición se guarda **por persona** y los avisos
   llegan al grupo. Dos personas en el mismo grupo con el mismo foco no generan dos mensajes.
5. Aviso de privacidad: en un grupo **todos ven la ubicación** que se comparte. Para uso real, la
   posición personal va por privado y el grupo se usa solo para los avisos.

## 2. Qué dispara un aviso

1. Se lee `data/derived/recent.parquet` (lo genera `download_recent.py`; **nunca** la web).
2. Se calcula el percentil 95 del FRP **del mismo sensor y la misma zona** con el histórico.
3. Un foco es **crítico** si su FRP supera ese umbral **y** ≥ 20 MW.
4. Si está dentro del radio (`haversine` ≤ radio), se envía:
   - texto con distancia, rumbo cardinal, FRP, sensor y confianza;
   - **pin** con `sendLocation` (abre Waze o Google Maps de un toque);
   - tres botones inline: 🔥 Fuego real · 🌾 Quema agrícola · ❌ Falsa alarma.
5. Cada aviso enviado se anota (`alerts_sent.json`): el mismo foco no se repite al mismo usuario.
6. El veredicto se guarda en `groundtruth.json` con historial (gana el último).

Sin datos recientes el bot **no inventa**: `/estado` dice "no hay datos recientes cargados".

## 3. API de la capa de campo

| Ruta | Para qué |
|---|---|
| `GET /api/historical-grid` | matriz del calendario por BBox (alias de `/api/calendar`) |
| `POST /api/register-geofence` | registra posición + radio y devuelve focos críticos cerca |
| `GET /api/geofences` | geocercas activas (para pintar puestos de campo en el mapa) |
| `GET/POST /api/groundtruth` | veredictos de campo y su resumen |
| `GET /api/climate-context` | déficit de lluvia y anomalía de Tmax (NASA POWER en caché) |

`POST /api/register-geofence` acepta una cabecera `X-Setup-Key` si defines `PYRO_SETUP_KEY` en el
entorno: sirve para que el endpoint no quede abierto en una demo pública.

## 4. Contexto climático (NASA POWER)

```bash
python backend/scripts/download_power.py --zone madrededios --years 5
```

Descarga temperatura máxima, lluvia y humedad diarias del punto central de la zona (sin clave) y
deja `data/derived/power_<zona>.json`. La web **solo lee ese archivo**; si no existe, la tarjeta
dice "sin datos" y muestra el comando exacto. El contexto compara los últimos 30 días con los
mismos 30 días de los años disponibles del caché: `seco` si el déficit de lluvia es ≤ −30 % o la
Tmax está 1,5 °C sobre lo normal.

## 5. Dónde se guarda todo (y cómo migrar a Supabase)

Hoy: JSON en `data/derived/` (fuera de git) detrás de `backend/pyro/groundtruth.py`. Las funciones
tienen la misma forma que las consultas SQL de `docs/arquitectura-tactica.md`
(`field_users`, `alerts`, `ground_truth`), así que migrar es cambiar el cuerpo de ese módulo.

Variables de entorno útiles:

| Variable | Para qué |
|---|---|
| `PYRO_FIELD_DIR` | carpeta del estado de campo (por defecto `data/derived/`) |
| `PYRO_POWER_DIR` | carpeta del caché de POWER |
| `PYRO_SETUP_KEY` | exige `X-Setup-Key` en `register-geofence` |

## 6. Pruebas

```bash
python -m pytest backend/tests -q       # incluye geocercas, veredictos y POWER con datos sintéticos
cd frontend && npm run smoke            # monta la app en jsdom con un payload real
```

## 7. POR VERIFICAR

- **El bucle `--poll` no se ha ejecutado contra Telegram** desde el entorno de desarrollo (sin
  salida a internet). Sí está probado el envío real de `sendMessage` (captura del 2026-11-15) y
  toda la lógica de geocerca, botones y almacenamiento con pruebas unitarias.
- **`sendLocation` y los botones** no se han visto en un teléfono todavía.
- **NASA POWER** no se ha descargado nunca desde aquí: la descarga solo se probó en modo
  `--dry-run`; el cálculo del déficit está probado con series sintéticas.
