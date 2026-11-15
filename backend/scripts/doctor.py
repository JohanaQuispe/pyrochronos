#!/usr/bin/env python3
"""Revisa en un solo comando todo lo que necesita PyroChronos para funcionar.

    python backend/scripts/doctor.py

Mira dependencias, datos, `.env` (permisos y claves), el bot de Telegram, los focos
recientes, el contexto de POWER y la API. Al final dice el ÚNICO siguiente paso.
Nunca imprime una clave completa.
"""
from __future__ import annotations

import json
import os
import stat
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

OK, WARN, BAD = "✅", "⚠️ ", "❌"
WINDOWS = os.name == "nt"
VENV_HINT = ("python -m venv .venv && .venv\\Scripts\\pip install -r requirements.txt" if WINDOWS
             else "python3 -m venv .venv && .venv/bin/pip install -r requirements.txt")
results: list[tuple[str, str]] = []


def add(status: str, message: str, fix: str | None = None) -> None:
    results.append((status, message + (f"\n      → {fix}" if fix else "")))


def check_deps() -> None:
    missing = []
    for mod in ("pandas", "pyarrow", "numpy", "fastapi", "uvicorn", "requests", "yaml"):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        add(BAD, f"faltan dependencias: {', '.join(missing)}",
            f"python -m pip install -r requirements.txt   (o, en un entorno nuevo: {VENV_HINT})")
    else:
        add(OK, "dependencias de Python instaladas")


def check_data() -> None:
    path = ROOT / "data" / "derived" / "detections.parquet"
    if not path.exists():
        add(BAD, "no existe data/derived/detections.parquet",
            "python backend/scripts/build_dataset.py --raw data/raw")
        return
    try:
        import pyarrow.parquet as pq

        rows = pq.ParquetFile(path).metadata.num_rows
        add(OK, f"serie histórica: {rows:,} focos ({path.stat().st_size / 1e6:.1f} MB)")
    except Exception as exc:  # noqa: BLE001
        add(WARN, f"el parquet existe pero no pude leerlo ({exc})")


def check_env() -> dict:
    """Lee .env y comprueba permisos y claves (sin imprimir valores)."""
    from telegram_setup import load_env_file, looks_like_token, mask_token

    env_path = ROOT / ".env"
    values: dict[str, str] = {}
    if not env_path.exists():
        add(WARN, "no hay .env en la raíz del proyecto",
            ("copy .env.example .env" if WINDOWS else "cp .env.example .env && chmod 600 .env"))
    else:
        mode = stat.S_IMODE(os.stat(env_path).st_mode)
        if WINDOWS:
            add(OK, ".env encontrado (en Windows los permisos no se gestionan con chmod)")
        elif mode & 0o077:
            add(WARN, f".env con permisos {oct(mode)} (lo pueden leer otros usuarios)",
                "chmod 600 .env")
        else:
            add(OK, ".env con permisos 600")
        values = load_env_file(env_path)
        for key, value in values.items():
            values[key] = value or os.environ.get(key, "")
    # el entorno manda sobre el archivo
    for key in ("FIRMS_MAP_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
        values[key] = os.environ.get(key) or values.get(key, "")

    key = values.get("FIRMS_MAP_KEY", "")
    if not key:
        add(WARN, "sin FIRMS_MAP_KEY: el histórico funciona, la descarga de focos recientes no",
            "pide una gratis en https://firms.modaps.eosdis.nasa.gov/api/map_key/")
    elif len(key) == 32:
        add(OK, f"FIRMS_MAP_KEY presente ({key[:4]}…{key[-2:]}, 32 caracteres)")
    else:
        add(WARN, f"FIRMS_MAP_KEY con {len(key)} caracteres (se esperan 32)", "vuelve a copiarla")

    token = values.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        add(WARN, "sin TELEGRAM_BOT_TOKEN: no se pueden enviar avisos",
            "python backend/scripts/telegram_setup.py --guide")
    elif looks_like_token(token):
        add(OK, f"TELEGRAM_BOT_TOKEN con formato correcto ({mask_token(token)})")
    else:
        add(BAD, f"TELEGRAM_BOT_TOKEN no tiene formato de @BotFather ({mask_token(token)})",
            "en @BotFather: /mybots → API Token")

    chat = values.get("TELEGRAM_CHAT_ID", "")
    if not chat:
        add(WARN, "sin TELEGRAM_CHAT_ID",
            "pulsa /start en el chat del bot y luego: telegram_setup.py --chat-id")
    elif not chat.lstrip("-").isdigit():
        add(BAD, f"TELEGRAM_CHAT_ID no es un número ({chat[:4]}…)")
    else:
        kind = "grupo" if chat.startswith("-") else "chat personal"
        add(OK, f"TELEGRAM_CHAT_ID presente ({chat[:3]}…{chat[-2:]}, {kind})")
    return values


def check_telegram(values: dict) -> None:
    """Solo si hay token: getMe y getUpdates (dos llamadas, sin enviar nada)."""
    from telegram_setup import call, TelegramError, chats_from_updates

    token = values.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        return
    try:
        me = call(token, "getMe", timeout=15)
        add(OK, f"Telegram responde: @{me.get('username', '?')}")
    except TelegramError as exc:
        text = str(exc).lower()
        if "no pude conectar" in text or "ssl" in text or "name resolution" in text:
            add(WARN, "sin conexión a api.telegram.org desde este equipo: no puedo validar el token",
                "ejecuta este mismo comando en tu portátil (aquí no hay salida a internet)")
        else:
            add(BAD, f"Telegram no acepta el token: {exc}", "revisa el token en @BotFather")
        return
    try:
        updates = call(token, "getUpdates", timeout=15)
    except TelegramError as exc:
        add(WARN, f"no pude leer los mensajes del bot ({exc})")
        return
    chats = chats_from_updates(updates)
    if not chats:
        add(WARN, "el bot no ha recibido ningún mensaje",
            "abre su chat y pulsa /start (o escribe 'hola')")
    else:
        ids = {c["id"] for c in chats}
        configured = values.get("TELEGRAM_CHAT_ID", "")
        if configured and configured in ids:
            add(OK, "el chat configurado ya habló con el bot")
        else:
            add(OK, f"chats que ya hablaron con el bot: {', '.join(sorted(ids))}",
                "usa uno de esos ids en TELEGRAM_CHAT_ID")


def check_recent() -> None:
    path = ROOT / "data" / "derived" / "recent.parquet"
    meta = ROOT / "data" / "derived" / "recent.json"
    if not path.exists():
        add(WARN, "sin focos recientes (recent.parquet): el bot avisará de nada",
            "python backend/scripts/download_recent.py --zone madrededios --days 3")
        return
    try:
        import pyarrow.parquet as pq

        rows = pq.ParquetFile(path).metadata.num_rows
        add(OK, f"focos recientes: {rows:,} ({path.stat().st_size / 1e6:.2f} MB)")
    except Exception as exc:  # noqa: BLE001
        add(WARN, f"recent.parquet ilegible ({exc})")
    if meta.exists():
        try:
            info = json.loads(meta.read_text(encoding="utf-8"))
            fetched = info.get("fetched_at")
            if fetched:
                when = datetime.fromisoformat(fetched.replace("Z", "+00:00"))
                horas = (datetime.now(timezone.utc) - when).total_seconds() / 3600
                status = OK if horas < 24 else WARN
                add(status, f"descargados hace {horas:.1f} h ({fetched})",
                    None if horas < 24 else "vuelve a descargarlos: los avisos deben ser de hoy")
        except Exception:  # noqa: BLE001
            pass


def check_power() -> None:
    files = sorted((ROOT / "data" / "derived").glob("power_*.json"))
    if files:
        add(OK, f"contexto de POWER precargado: {', '.join(f.stem.replace('power_', '') for f in files)}")
    else:
        add(WARN, "sin contexto de NASA POWER (la tarjeta climática dirá 'sin datos')",
            "python backend/scripts/download_power.py --zone madrededios --years 5")


def check_api() -> None:
    import requests

    try:
        r = requests.get("http://127.0.0.1:8000/api/health", timeout=3)
        if r.status_code == 200:
            add(OK, "la API responde en http://127.0.0.1:8000")
        else:
            add(WARN, f"la API responde {r.status_code}")
    except Exception:  # noqa: BLE001
        add(WARN, "la API no está corriendo en el puerto 8000 (normal si no la has abierto)",
            "python -m uvicorn api.main:app --app-dir backend --host 0.0.0.0 --port 8000")


def next_step(values: dict) -> str:
    token = values.get("TELEGRAM_BOT_TOKEN", "")
    chat = values.get("TELEGRAM_CHAT_ID", "")
    recent = (ROOT / "data" / "derived" / "recent.parquet").exists()
    if not (ROOT / ".env").exists():
        plantilla = "copy .env.example .env" if WINDOWS else "cp .env.example .env && chmod 600 .env"
        return f"Crea el .env:  {plantilla}  y pega tus claves."
    if not token:
        return "Consigue el token:  python backend/scripts/telegram_setup.py --guide"
    if not chat:
        return "Pulsa /start en el bot y ejecuta:  python backend/scripts/telegram_setup.py --chat-id"
    if not recent:
        return "Descarga focos de hoy:  python backend/scripts/download_recent.py --zone madrededios --days 3"
    return "Todo listo. Prueba el aviso:  python backend/scripts/bot.py --send-demo --zone madrededios"


def main() -> int:
    print("PyroChronos · revisión del sistema\n" + "=" * 40)
    check_deps()
    check_data()
    values = check_env()
    check_telegram(values)
    check_recent()
    check_power()
    check_api()

    print()
    for status, message in results:
        print(f"{status} {message}")
    fails = sum(1 for s, _ in results if s == BAD)
    warns = sum(1 for s, _ in results if s == WARN)
    print("\n" + "=" * 40)
    print(f"{len(results) - fails - warns} bien · {warns} pendientes · {fails} con error")
    print(f"\nSIGUIENTE PASO → {next_step(values)}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
