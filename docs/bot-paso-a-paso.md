# Bot de PyroChronos: configuración paso a paso

Todo lo que hay que configurar, en orden, con lo que debes ver en cada paso.
Si algo falla, al final está la sección **Problemas y arreglos**.

---

## 0. Antes de empezar (5 min)

| Qué | Comando | Qué debes ver |
|---|---|---|
| Python 3.11+ y dependencias | `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` | termina sin errores |
| Clave de NASA FIRMS (gratis) | https://firms.modaps.eosdis.nasa.gov/api/map_key/ | un correo con tu `MAP_KEY` |
| Bot creado en @BotFather | ver paso 1 | un token `1234567890:AA…` |
| Datos históricos en su sitio | `ls data/derived/detections.parquet` | el archivo existe (13 MB) |

---

## 1. Crear el bot en @BotFather (5 min, a mano)

Telegram **no permite** crear bots por API: este paso es tuyo, desde el teléfono.

1. Abre Telegram → busca **@BotFather** (el oficial, insignia azul).
2. `/newbot`
3. Nombre visible: `PyroChronos`
4. Usuario: `pyrochronos_tu_nombre_bot` (debe terminar en `bot`)
5. Guarda el token que te da. **No lo pegues en ningún chat.**

---

## 2. Ponerle cara y voz al bot (2 min, opcional pero recomendado)

En el mismo chat con @BotFather, uno por uno:

**a) Nombre**
```
/setname
```
→ elige el bot → `PyroChronos`

**b) Foto de perfil** (usa `frontend/public/bot-avatar.png`, ya recortada para el círculo de Telegram)
```
/setuserpic
```
→ elige el bot → adjunta `bot-avatar.png`

**c) Descripción** (lo que se lee antes de pulsar /start; máximo 512 caracteres)
```
/setdescription
```
→ elige el bot → pega:

> Calendario de fuego de NASA (MODIS + VIIRS) armonizado desde el año 2000. Te aviso cuando un
> foco de calor intenso cae dentro de tu radio y te llevo al punto exacto en el mapa. Datos
> históricos y casi en tiempo real (≈3 h de latencia): no es un servicio oficial de emergencias
> ni predice incendios. Pulsa /start para activar tu geocerca.

**d) Texto del perfil** (máximo 120 caracteres)
```
/setabouttext
```
→

> Focos de calor NASA armonizados. Avisos por geocerca. No es un aviso oficial.

**e) Menú de comandos**
```
/setcommands
```
→ elige el bot → pega las cuatro líneas:

```
start - Activar aviso y compartir ubicación
estado - Mi geocerca y focos vigilados
radio - Cambiar el radio (ej. /radio 15)
ayuda - Qué puedo hacer
```

**f) Grupos** (si lo vas a usar con una brigada)
```
/setjoingroups
```
→ `Enable`.

---

## 3. Configurar las claves en `.env` (2 min)

En la raíz del proyecto:

```bash
cp .env.example .env
chmod 600 .env
```

Edita `.env` y deja exactamente esto:

```ini
FIRMS_MAP_KEY=tu_clave_de_firms
TELEGRAM_BOT_TOKEN=1234567890:AAH...
TELEGRAM_CHAT_ID=
PYRO_SETUP_KEY=
```

- `TELEGRAM_CHAT_ID` lo descubre el script en el paso 4.
- `PYRO_SETUP_KEY` es opcional: si la pones, `POST /api/register-geofence` exige la cabecera
  `X-Setup-Key`. Útil si publicas la demo.
- `.env` está en `.gitignore`: **nunca** se sube. Nunca pegues el token en capturas.

Comprobar que el token vale:

```bash
set -a && . ./.env && set +a
python backend/scripts/telegram_setup.py --check
```
Debes ver: `Bot: @tu_bot  (nombre: PyroChronos)`.

---

## 4. Descubrir tu `chat_id` y guardarlo (2 min)

1. Abre el chat de **tu bot** y pulsa `/start` (o escribe "hola").
2. Ejecuta:

```bash
python backend/scripts/telegram_setup.py --chat-id
```
Verás algo como `chat_id=123456789  tipo=private  Tu Nombre`.

3. Guárdalo:

```bash
python backend/scripts/telegram_setup.py --write-env
python backend/scripts/telegram_setup.py --test
```
Debe llegarte un mensaje al teléfono. **Si llega, el canal está probado.**

> Para un grupo: añade el bot al grupo, escribe `@tu_bot hola` y el `--chat-id` mostrará un id
> negativo (`-100…`). Ese es el que se guarda.

---

## 5. Encender la capa de campo (3 min)

```bash
set -a && . ./.env && set +a

# 1) datos recientes reales (necesita FIRMS_MAP_KEY; 1-5 días por consulta)
python backend/scripts/download_recent.py --zone madrededios --days 3

# 2) ver el aviso sin enviar nada
python backend/scripts/bot.py --dry-run --zone madrededios

# 3) mandar ese aviso a tu Telegram (marcado DEMO con un foco histórico)
python backend/scripts/bot.py --send-demo --zone madrededios

# 4) escuchar: /start, comparte ubicación, pulsa un botón del aviso
python backend/scripts/bot.py --poll --zone madrededios
```

**Deja la última terminal abierta**: ahí vive el bot. Si la cierras, deja de escuchar.

### Qué debes ver, en orden

| Acción | Respuesta esperada |
|---|---|
| `/start` | mensaje de bienvenida + botón **📍 Compartir mi ubicación** |
| pulsar el botón | `✅ Geocerca activada · Radio: 10 km · Centro: -12.59, -69.18` |
| `/estado` | tu geocerca, focos recientes cargados, validaciones hechas |
| `/radio 15` | `Radio actualizado a 15 km.` |
| pulsar 🔥 / 🌾 / ❌ | `Registrado: …` y `✅ Guardado` en el chat |
| ver el resultado | `curl -s localhost:8000/api/groundtruth` |

---

## 6. La web y la API (2 min)

```bash
python -m uvicorn api.main:app --app-dir backend --host 0.0.0.0 --port 8000
```

Abre `http://localhost:8000`. La tarjeta **Contexto climático** dice "sin datos" hasta que hagas:

```bash
python backend/scripts/download_power.py --zone madrededios --years 5
```

---

## 7. Lista de verificación final

```
[ ] .env con FIRMS_MAP_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID  (chmod 600)
[ ] telegram_setup.py --check  → Bot: @tu_bot
[ ] telegram_setup.py --test   → llega el mensaje al teléfono
[ ] download_recent.py         → data/derived/recent.parquet
[ ] bot.py --send-demo         → pin + 3 botones en el teléfono
[ ] bot.py --poll              → /start, ubicación, veredicto guardado
[ ] uvicorn ... --port 8000    → la web abre con el calendario
[ ] download_power.py          → la tarjeta climática deja de decir "sin datos"
[ ] git status                 → .env NO aparece
```

---

## 8. Problemas y arreglos

| Síntoma | Causa | Arreglo |
|---|---|---|
| `Unauthorized` / 401 | token mal copiado o revocado | @BotFather → `/mybots` → API Token → revocar y pegar el nuevo |
| `chat not found` | nunca pulsaste /start | abre el chat del bot, pulsa /start, reintenta |
| `No hay datos recientes cargados` | falta `recent.parquet` | `download_recent.py --zone … --days 3` (necesita MAP_KEY) |
| El bot no responde a nada | `--poll` no está corriendo o cerraste la terminal | vuelve a lanzarlo; debe quedarse abierto |
| No llegan avisos | radio pequeño o ningún foco sobre el p95 | `/radio 50`; mira `bot.py --dry-run` para ver el umbral |
| `Falta TELEGRAM_BOT_TOKEN` | `.env` no exportado en esa terminal | `set -a && . ./.env && set +a` |
| El pin abre en el navegador | configuración de Telegram | en Ajustes → Datos y almacenamiento → elegir app de mapas |
| `403` al registrar geocerca | `PYRO_SETUP_KEY` definida | manda la cabecera `X-Setup-Key` o quita la variable |

---

## 9. Cómo contarlo en el video (30 s)

> "Un guardaparque comparte su ubicación con el bot y queda dentro de una geocerca de 10 km. Cuando
> un foco supera el percentil 95 del FRP de su zona, recibe distancia, rumbo, el pin para ir en
> Waze y tres botones para decir qué era. Eso convierte 1,3 millones de detecciones históricas en
> una decisión de campo."
