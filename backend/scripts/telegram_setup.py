#!/usr/bin/env python3
"""Asistente para conectar PyroChronos con un bot de Telegram.

Lo unico que NO se puede automatizar es crear el bot: Telegram solo permite
crearlo a mano desde tu telefono, hablando con @BotFather. Este script hace
todo lo demas:

    --guide      recuerda los pasos de @BotFather
    --check      comprueba que el token funciona (getMe)
    --chat-id    descubre tu chat_id a partir de los mensajes recibidos
    --test       manda un mensaje de prueba al chat
    --write-env  guarda TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID en .env (chmod 600)

El token NUNCA se imprime completo, ni se escribe en el codigo, ni se sube al
repositorio: solo se lee del entorno o de .env (que esta en .gitignore).

    python backend/scripts/telegram_setup.py --guide
    python backend/scripts/telegram_setup.py --check
    python backend/scripts/telegram_setup.py --chat-id
    python backend/scripts/telegram_setup.py --test
    python backend/scripts/telegram_setup.py --write-env
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV = ROOT / ".env"
API = "https://api.telegram.org/bot{token}/{method}"
TIMEOUT = 20

GUIDE = """\
PASOS PARA CREAR EL BOT (5 minutos, desde el telefono o el escritorio)

1. Abre Telegram y busca @BotFather (el oficial, con la insignia azul).
2. Escribe /newbot.
3. Nombre visible: PyroChronos        (puede llevar espacios)
4. Usuario: pyrochronos_tu_nombre_bot   (debe terminar en "bot"; si esta
   ocupado, prueba otro)
5. BotFather responde con un token parecido a
       1234567890:AAH...corta...4fQ
   Ese texto es la llave del bot: no lo pegues en el chat, ni en capturas,
   ni en el codigo. Guardalo como TELEGRAM_BOT_TOKEN en .env.
6. Abre el chat de tu bot y pulsa /start (o envia "hola"). Sin ese mensaje
   el bot no puede escribirte.
7. Vuelve aqui y ejecuta, en este orden:
       python backend/scripts/telegram_setup.py --check
       python backend/scripts/telegram_setup.py --chat-id
       python backend/scripts/telegram_setup.py --write-env
       python backend/scripts/telegram_setup.py --test
8. Si el --test llega a tu telefono, ya puedes enviar el boletin real:
       python backend/scripts/notify_telegram.py --zone madrededios --send

Para avisos en grupo: agrega el bot al grupo, envia algo mencionandolo
(@tu_bot hola) y el --chat-id mostrara el id del grupo (empieza con "-").
"""


class TelegramError(RuntimeError):
    """Error devuelto por la API de Telegram (mensaje ya sin token)."""


def mask_token(token: str | None) -> str:
    """Devuelve una version segura de mostrar: nunca el token completo."""
    if not token:
        return "(sin token)"
    token = token.strip()
    head = token.split(":", 1)[0]
    tail = token[-4:] if len(token) > 8 else ""
    return f"{head[:10]}…{tail} ({len(token)} caracteres)"


def looks_like_token(token: str | None) -> bool:
    """Formato de BotFather: <id numerico>:<35+ caracteres>."""
    if not token or ":" not in token:
        return False
    left, right = token.split(":", 1)
    return left.isdigit() and len(right) >= 30


def load_env_file(path: Path = DEFAULT_ENV) -> dict[str, str]:
    """Lee un .env sencillo (KEY=valor, # comentarios, comillas opcionales)."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def upsert_env(path: Path, values: dict[str, str]) -> None:
    """Escribe/actualiza claves en .env conservando comentarios y orden."""
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    pending = {k: v for k, v in values.items() if v}
    out: list[str] = []
    for line in existing:
        stripped = line.strip()
        if "=" in stripped and not stripped.startswith("#"):
            key = stripped.split("=", 1)[0].strip()
            if key in pending:
                out.append(f"{key}={pending.pop(key)}")
                continue
        out.append(line)
    if pending:
        if out and out[-1].strip():
            out.append("")
        for key, value in pending.items():
            out.append(f"{key}={value}")
    path.write_text("\n".join(out).rstrip("\n") + "\n", encoding="utf-8")
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 600: solo tu usuario


def resolve_credentials(token: str | None = None, chat_id: str | None = None) -> tuple[str | None, str | None]:
    """Prioridad: argumento de linea de comandos > entorno > archivo .env."""
    file_env = load_env_file()
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN") or file_env.get("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID") or file_env.get("TELEGRAM_CHAT_ID")
    return (token.strip() if token else None, chat_id.strip() if chat_id else None)


def call(token: str, method: str, timeout: int = TIMEOUT, **params) -> dict:
    """Llama a la API de bots con un mensaje de error que no filtra el token."""
    try:
        r = requests.post(API.format(token=token, method=method), data=params, timeout=timeout)
    except requests.RequestException as exc:
        raise TelegramError(
            "No pude conectar con api.telegram.org "
            f"({type(exc).__name__}). Si esto corre dentro de un contenedor sin "
            "salida a internet, ejecutalo en tu portatil."
        ) from None
    try:
        body = r.json()
    except ValueError:
        raise TelegramError(f"Telegram respondio {r.status_code} sin JSON legible.") from None
    if not body.get("ok"):
        desc = str(body.get("description", "error desconocido"))
        if r.status_code == 401:
            desc += " (token invalido o revocado: pide uno nuevo con /mybots en @BotFather)"
        raise TelegramError(f"Telegram respondio {r.status_code}: {desc}")
    return body.get("result", {})


def chats_from_updates(updates: list[dict]) -> list[dict]:
    """Extrae chats unicos de getUpdates, con el tipo y el titulo."""
    found: dict[str, dict] = {}
    for upd in updates:
        for key in ("message", "edited_message", "channel_post", "my_chat_member"):
            payload = upd.get(key) or {}
            chat = payload.get("chat") or {}
            cid = chat.get("id")
            if cid is None:
                continue
            found[str(cid)] = {
                "id": str(cid),
                "type": chat.get("type", "?"),
                "title": chat.get("title")
                or " ".join(filter(None, [chat.get("first_name"), chat.get("last_name")]))
                or chat.get("username")
                or "(sin nombre)",
            }
    return list(found.values())


def cmd_guide() -> int:
    print(GUIDE)
    return 0


def cmd_check(token: str | None) -> int:
    if not token:
        print("No hay token. Guardalo en .env como TELEGRAM_BOT_TOKEN (mira --guide).")
        return 2
    if not looks_like_token(token):
        print(f"El token no tiene el formato de @BotFather: {mask_token(token)}")
        print("Debe ser un numero, dos puntos y ~35 caracteres. Revisa que no falte nada al copiar.")
        return 2
    try:
        me = call(token, "getMe")
    except TelegramError as exc:
        print(f"Token {mask_token(token)} -> {exc}")
        return 1
    print(f"Token valido: {mask_token(token)}")
    print(f"Bot: @{me.get('username', '?')}  (nombre: {me.get('first_name', '?')})")
    print(f"Puede unirse a grupos: {'si' if me.get('can_join_groups') else 'no'}")
    print("\nSiguiente paso: abre el chat del bot, pulsa /start y ejecuta --chat-id")
    return 0


def cmd_chat_id(token: str | None) -> int:
    if not token:
        print("No hay token: primero --check (mira --guide).")
        return 2
    try:
        updates = call(token, "getUpdates", timeout=35)
    except TelegramError as exc:
        print(f"No pude leer los mensajes: {exc}")
        return 1
    chats = chats_from_updates(updates)
    if not chats:
        print("No hay mensajes todavia. Abre el chat de tu bot en Telegram,")
        print("pulsa /start (o escribe 'hola') y vuelve a ejecutar --chat-id.")
        return 1
    print("Chats que han hablado con el bot:\n")
    for c in chats:
        print(f"  chat_id={c['id']:<16} tipo={c['type']:<10} {c['title']}")
    if len(chats) == 1:
        print(f"\nUsa este: TELEGRAM_CHAT_ID={chats[0]['id']}")
        print("Guardalo con --write-env (o copialo a mano en .env).")
    else:
        print("\nHay varios: elige el que corresponda a tu persona o grupo.")
    return 0


def cmd_test(token: str | None, chat_id: str | None) -> int:
    if not token or not chat_id:
        print("Faltan datos: necesito TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID.")
        print("Ejecuta --check y --chat-id, guarda con --write-env y reintenta.")
        return 2
    text = (
        "PyroChronos conectado ✅\n"
        "Este es un mensaje de prueba del calendario de fuego armonizado "
        "(NASA FIRMS). Si lo ves, el envio funciona.\n"
        "Ojo: es informacion historica, no un aviso en tiempo real."
    )
    try:
        msg = call(token, "sendMessage", chat_id=chat_id, text=text)
    except TelegramError as exc:
        hint = ""
        if "chat not found" in str(exc).lower():
            hint = "\nPista: abre el chat del bot y pulsa /start una vez."
        print(f"No se pudo enviar: {exc}{hint}")
        return 1
    print(f"Mensaje enviado a chat_id={chat_id} (message_id={msg.get('message_id', '?')}).")
    print("Revisa tu telefono. Luego: python backend/scripts/notify_telegram.py --zone madrededios --send")
    return 0


def cmd_write_env(token: str | None, chat_id: str | None, path: Path) -> int:
    if not token:
        print("No hay token que guardar (mira --guide).")
        return 2
    if not looks_like_token(token):
        print(f"El token no parece valido: {mask_token(token)}. No escribo nada.")
        return 2
    upsert_env(path, {"TELEGRAM_BOT_TOKEN": token, "TELEGRAM_CHAT_ID": chat_id or ""})
    saved = load_env_file(path)
    print(f"Guardado en {path} (permisos 600, fuera de git por .gitignore).")
    print(f"  TELEGRAM_BOT_TOKEN={mask_token(saved.get('TELEGRAM_BOT_TOKEN'))}")
    print(f"  TELEGRAM_CHAT_ID={saved.get('TELEGRAM_CHAT_ID') or '(vacio: falta --chat-id)'}")
    print("\nAviso: los scripts cargan .env automaticamente al arrancar (pyro.config).")
    print("Si prefieres exportarlo a mano:  Linux/macOS: set -a && . ./.env && set +a")
    return 0 if saved.get("TELEGRAM_CHAT_ID") else 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Comprueba y guarda la conexion del bot de Telegram de PyroChronos.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=GUIDE,
    )
    ap.add_argument("--guide", action="store_true", help="muestra los pasos de @BotFather")
    ap.add_argument("--check", action="store_true", help="valida el token (getMe)")
    ap.add_argument("--chat-id", dest="chat_id_cmd", action="store_true", help="descubre tu chat_id")
    ap.add_argument("--test", action="store_true", help="manda un mensaje de prueba")
    ap.add_argument("--write-env", dest="write_env", action="store_true", help="guarda las claves en .env")
    ap.add_argument("--token", default=None, help="token del bot (mejor por entorno o .env)")
    ap.add_argument("--chat-id-value", dest="chat_id", default=None, help="chat_id a usar")
    ap.add_argument("--env-file", default=str(DEFAULT_ENV), help="ruta del .env (por defecto ./.env)")
    ap.add_argument("--json", action="store_true", help="salida legible por maquina donde aplique")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    token, chat_id = resolve_credentials(args.token, args.chat_id)
    path = Path(args.env_file)

    if args.guide:
        return cmd_guide()
    if args.check:
        return cmd_check(token)
    if args.chat_id_cmd:
        return cmd_chat_id(token)
    if args.test:
        return cmd_test(token, chat_id)
    if args.write_env:
        return cmd_write_env(token, chat_id, path)

    # sin accion: diagnostico corto
    print("PyroChronos · conexion con Telegram")
    print(f"  token:   {mask_token(token)}")
    print(f"  chat_id: {chat_id or '(sin definir)'}")
    print(f"  .env:    {path} {'existe' if path.exists() else 'no existe'}")
    print("\nAcciones: --guide  --check  --chat-id  --test  --write-env")
    if args.json:
        print(json.dumps({"token": mask_token(token), "chat_id": chat_id, "env_exists": path.exists()},
                         ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
