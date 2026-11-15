# Arquitectura táctica (diseño) — geocercas, pines y validación en campo

> **Estado real: DISEÑADO, NO DESPLEGADO.** Sin Supabase y sin servidor de bot, implementar
> geocercas + PostGIS + `sendLocation` + botones inline son 4–6 h de trabajo **y no se pueden
> probar desde este entorno** (no hay salida a `api.telegram.org`). Hoy ya está probado:
> `sendMessage` (captura del 2026-11-15) y todo el calendario armonizado.
> Este documento existe para (a) que el jurado vea que la capa táctica está pensada y
> (b) que pueda implementarse sin rediseñar nada.

## 1. Qué ya existe y qué falta

| Pieza del pedido | Estado |
|---|---|
| Armonización MODIS+VIIRS en celda ~1 km² (0,01°) | **hecho y validado** (todo el calendario sale de aquí) |
| Matriz semana × año | **hecho** (`/api/calendar?granularity=week`) |
| Anomalías por percentil | **hecho** (p90 / p97.5, no p95: ver `docs/metodologia.md`) |
| Selector de métrica | **parcial**: celdas-día y focos detectados; FRP sale en el CSV de focos, no como serie |
| Banda de incertidumbre | **hecho**, pero es p25–p75 del factor de armonización, **no ±σ** |
| Exportación PDF | **hecho** vía HTML A4 + "Imprimir / Guardar como PDF" |
| `GET /api/historical-grid` | **falta**: es `/api/calendar` con otro nombre (alias trivial) |
| `GET /api/climate-context` | **falta** (NASA POWER, sin clave) |
| `POST /api/register-geofence` | **falta** |
| Bot con geocerca, `sendLocation`, botones "Ground Truth" | **falta** (solo envío de texto) |
| Supabase + PostGIS | **falta** (hoy Parquet detrás de una capa de acceso intercambiable) |

## 2. Estructura modular propuesta

```
backend/
  pyro/
    store.py          # capa de acceso actual (Parquet). Punto único a cambiar por Postgres.
    geofence.py       # NUEVO: haversine, filtro por radio, armado del mensaje (funciones puras)
    power.py          # NUEVO: cliente NASA POWER + caché en data/derived/power_<zona>.json
    groundtruth.py    # NUEVO: validación humana (hoy JSON; mañana tabla ground_truth)
  api/main.py         # + /api/historical-grid, /api/climate-context, /api/register-geofence
  bot/
    main.py           # NUEVO: bucle getUpdates (long polling) con requests, sin librerías extra
    handlers.py       # NUEVO: /start, contacto compartido, callback_query de los botones
  scripts/
    download_power.py # NUEVO: precarga POWER (la web nunca llama a NASA en vivo)
db/
  schema_postgis.sql  # esquema completo, listo para `supabase db push`
```

**Decisión de diseño:** el bot se hace con la Bot API cruda (`requests`), no con
`python-telegram-bot`. Motivos: cero dependencias nuevas, el mismo patrón del `sendMessage`
que ya funciona, y la lógica de geocerca queda en funciones puras testeables sin red.

## 3. Esquema PostGIS (Supabase)

```sql
create extension if not exists postgis;

-- Focos normalizados (una fila por detección, ambas fuentes, esquema común)
create table hotspots (
  id           bigserial primary key,
  sensor       text not null check (sensor in ('MODIS','VIIRS')),
  acq_date     date not null,
  acq_time     time,
  geom         geography(Point, 4326) not null,
  confidence   smallint,          -- 0/1/2 (baja/nominal/alta)
  frp_mw       real,
  type         smallint,
  version      text,
  cell_id      text not null,     -- cuadrícula 0,01°: "lon_idx_lat_idx"
  created_at   timestamptz default now()
);
create index hotspots_geom_idx on hotspots using gist (geom);
create index hotspots_date_idx on hotspots (acq_date);
create index hotspots_cell_idx on hotspots (cell_id, acq_date);

-- Serie armonizada resultante (la que dibuja el calendario)
create table calendar_cells (
  cell_id      text not null,
  iso_year     smallint not null,
  iso_week     smallint not null,
  cell_days    integer not null,
  detections   integer not null,
  frp_sum      real,
  estimated    boolean not null default false,
  primary key (cell_id, iso_year, iso_week)
);

-- Climatología y anomalías por celda y semana del año
create table climatology (
  cell_id      text not null,
  iso_week     smallint not null,
  p50          real, p90 real, p97_5 real,
  years_used   smallint,
  primary key (cell_id, iso_week)
);

-- Usuarios de campo y sus geocercas
create table field_users (
  telegram_id  bigint primary key,
  name         text,
  role         text check (role in ('bombero','guardaparque','cientifico','ciudadano')),
  geom         geography(Point, 4326),
  radius_km    real not null default 10,
  active       boolean not null default true,
  updated_at   timestamptz default now()
);
create index field_users_geom_idx on field_users using gist (geom);

-- Alertas enviadas (evita repetir el mismo foco al mismo usuario)
create table alerts (
  id           bigserial primary key,
  telegram_id  bigint references field_users(telegram_id) on delete cascade,
  hotspot_id   bigint references hotspots(id) on delete cascade,
  distance_km  real not null,
  sent_at      timestamptz default now(),
  unique (telegram_id, hotspot_id)
);

-- Validación humana ("Ground Truth") desde los botones inline
create table ground_truth (
  id           bigserial primary key,
  hotspot_id   bigint references hotspots(id) on delete cascade,
  telegram_id  bigint,
  verdict      text not null check (verdict in ('fuego_real','quema_agricola','falsa_alarma')),
  created_at   timestamptz default now()
);

-- Consulta de proximidad: focos críticos a menos de X km de un usuario
create or replace function hotspots_near(p_lat float8, p_lon float8, p_radius_km float8)
returns table (id bigint, lat float8, lon float8, acq_date date, frp_mw real, distance_km float8)
language sql stable as $$
  select h.id,
         st_y(h.geom::geometry) as lat,
         st_x(h.geom::geometry) as lon,
         h.acq_date, h.frp_mw,
         st_distance(h.geom, st_makepoint(p_lon, p_lat)::geography) / 1000.0 as distance_km
  from hotspots h
  where st_dwithin(h.geom, st_makepoint(p_lon, p_lat)::geography, p_radius_km * 1000)
  order by distance_km asc;
$$;

-- Seguridad: la web solo lee; escribe el servidor con service_role
alter table hotspots      enable row level security;
alter table field_users   enable row level security;
alter table ground_truth  enable row level security;
create policy "lectura publica de focos" on hotspots for select using (true);
create policy "nadie escribe desde el navegador" on field_users for all using (false);
```

## 4. Endpoints (especificación)

```
GET  /api/historical-grid?bbox=o,s,e,n&start=2000-01-01&end=2026-11-14&granularity=week
       -> { meta, calendar:{years, periods, values, levels, estimated}, cards, series }
       (implementado como /api/calendar; la ruta se puede aliasar en 3 líneas)

GET  /api/climate-context?zone=madrededios
       -> { available, source:"NASA POWER", params:{T2M_MAX, PRECTOTCORR, RH2M},
            window_days:30, deficit_pct, tmax_anom_c, note }

POST /api/register-geofence   { "telegram_id": 123, "lat": -12.59, "lon": -69.18, "radius_km": 10 }
       -> { ok, radius_km, geofences_active, nearest_critical_hotspots }
       Requiere cabecera X-Setup-Key (solo servidor); nunca desde el navegador.
```

`climate-context` **lee un archivo precargado** (`download_power.py`), nunca llama a NASA en la
petición: el mismo principio que ya se usa para los focos recientes.

## 5. Flujo del bot (7 pasos)

1. `/start` → teclado con `request_location=True` ("Compartir mi ubicación").
2. Llega un `message.location` → se guarda `field_users(geom, radius_km=10)`.
3. Cada N minutos el bot lee los focos recientes (`recent.parquet` o tabla `hotspots`).
4. Para cada foco **crítico** (anomalía ≥ p97.5 de su celda **y** FRP en el cuartil superior):
   `haversine(foco, usuario) ≤ radius_km`.
5. Envía tres cosas en un solo mensaje: texto (distancia, rumbo, FRP, fecha/hora) →
   `sendLocation(lat, lon)` (abre Waze/Google Maps) → `inline_keyboard` con tres botones.
6. Pulsa un botón → `callback_query` con `data="gt:<hotspot_id>:<veredicto>"` → se guarda en
   `ground_truth` y se responde `answerCallbackQuery` ("Gracias, registrado").
7. `alerts(telegram_id, hotspot_id)` evita repetir el mismo aviso; el mapa puede colorear por
   veredicto (fuego real / quema agrícola / falsa alarma).

```python
# handlers.py — diseño (no implementado)
BTN = {"🔥 Fuego real": "fuego_real", "🌾 Quema agrícola": "quema_agricola", "❌ Falsa alarma": "falsa_alarma"}

def keyboard(hotspot_id: int) -> dict:
    return {"inline_keyboard": [[{"text": label, "callback_data": f"gt:{hotspot_id}:{code}"}
                                 for label, code in BTN.items()]]}

def alert_text(h: dict, dist_km: float, wind: dict | None) -> str:
    viento = f"Viento {wind['dir']}° a {wind['kmh']} km/h." if wind else "Sin dato de viento."
    return (f"Foco a {dist_km:.1f} km ({h['bearing']}).\n"
            f"FRP {h['frp_mw']:.0f} MW · detectado {h['acq_date']} {h.get('acq_time','')}\n"
            f"{viento}\nEs una detección satelital: confírmala antes de movilizar.")

def on_callback(q: dict) -> None:
    _, hotspot_id, verdict = q["data"].split(":")
    groundtruth.save(int(hotspot_id), q["from"]["id"], verdict)
    answer_callback(q["id"], "Gracias, quedó registrado en el mapa.")
```

## 6. Por qué no se implementó hoy

- Faltaban ~90 minutos para el cierre; desplegar Supabase + PostGIS + un bot en escucha son
  4–6 h y **no verificables** sin salida a Telegram desde el entorno de desarrollo.
- Romper la demo que ya funciona cuesta la nota entera; una diapositiva de "trabajo futuro
  diseñado" cuesta cero.
- Lo que el jurado evalúa es la **armonización** y la honestidad del sistema; la capa táctica sin
  probar sería justo lo contrario.

## 7. Si hubiera una semana

1. `schema_postgis.sql` + `supabase db push`; cargar el Parquet con `COPY`.
2. `power.py` + `download_power.py` (contexto de sequía por zona).
3. `geofence.py` con pruebas unitarias (haversine, radio, rumbo, deduplicación).
4. `bot/main.py` en un contenedor con `getUpdates`; probar con dos teléfonos.
5. Vista "campo" en la web: pines con veredicto y contador de falsas alarmas por sensor.
