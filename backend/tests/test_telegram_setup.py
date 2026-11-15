"""Pruebas del asistente de Telegram: nunca filtra el token y no duplica claves."""
from __future__ import annotations

import importlib.util
import os
import stat
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "telegram_setup.py"
FAKE = "1234567890:" + "A" * 34 + "4fQ"


def load_module():
    spec = importlib.util.spec_from_file_location("telegram_setup", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def ts():
    return load_module()


def test_mask_never_leaks_full_token(ts):
    masked = ts.mask_token(FAKE)
    assert FAKE not in masked
    assert masked.endswith(f"4fQ ({len(FAKE)} caracteres)")
    assert ts.mask_token(None) == "(sin token)"


def test_looks_like_token(ts):
    assert ts.looks_like_token(FAKE)
    assert not ts.looks_like_token("")
    assert not ts.looks_like_token("abc:def")
    assert not ts.looks_like_token("1234567890:corto")


def test_env_roundtrip_and_permissions(ts, tmp_path):
    env = tmp_path / ".env"
    env.write_text("# comentario\nFIRMS_MAP_KEY=\nTELEGRAM_CHAT_ID=111\n", encoding="utf-8")
    ts.upsert_env(env, {"TELEGRAM_BOT_TOKEN": FAKE, "TELEGRAM_CHAT_ID": "222"})
    ts.upsert_env(env, {"TELEGRAM_BOT_TOKEN": FAKE, "TELEGRAM_CHAT_ID": "222"})  # idempotente
    text = env.read_text(encoding="utf-8")
    assert "# comentario" in text
    assert text.count("TELEGRAM_BOT_TOKEN=") == 1
    assert text.count("TELEGRAM_CHAT_ID=") == 1
    assert "TELEGRAM_CHAT_ID=222" in text
    assert ts.load_env_file(env)["TELEGRAM_BOT_TOKEN"] == FAKE
    assert stat.S_IMODE(os.stat(env).st_mode) == 0o600


def test_load_env_file_ignores_comments_and_quotes(ts, tmp_path):
    env = tmp_path / ".env"
    env.write_text('# TELEGRAM_BOT_TOKEN=no\nA="1"\nB=2\n\n', encoding="utf-8")
    values = ts.load_env_file(env)
    assert values == {"A": "1", "B": "2"}


def test_chats_from_updates_deduplicates(ts):
    updates = [
        {"message": {"chat": {"id": 42, "type": "private", "first_name": "Ana"}}},
        {"message": {"chat": {"id": 42, "type": "private", "first_name": "Ana"}}},
        {"message": {"chat": {"id": -100, "type": "supergroup", "title": "Brigada"}}},
        {"edited_message": {"chat": {"id": -100, "type": "supergroup", "title": "Brigada"}}},
    ]
    chats = ts.chats_from_updates(updates)
    assert [c["id"] for c in chats] == ["42", "-100"]
    assert chats[1]["title"] == "Brigada"


def test_main_without_token_exits_cleanly(ts, capsys):
    assert ts.main(["--check", "--env-file", "/nonexistent/.env"]) == 2
    out = capsys.readouterr().out
    assert "No hay token" in out


def test_test_command_without_chat_id(ts, capsys):
    assert ts.main(["--test", "--token", "123", "--env-file", "/nonexistent/.env"]) == 2
    assert "TELEGRAM_CHAT_ID" in capsys.readouterr().out


def test_write_env_refuses_invalid_token(ts, tmp_path, capsys):
    env = tmp_path / ".env"
    assert ts.main(["--write-env", "--token", "noesuntoken", "--env-file", str(env)]) == 2
    assert not env.exists()
    assert "no parece valido" in capsys.readouterr().out


def test_guide_mentions_botfather(ts, capsys):
    assert ts.main(["--guide"]) == 0
    out = capsys.readouterr().out
    assert "@BotFather" in out and "/newbot" in out


class FakeResponse:
    def __init__(self, status_code: int, body: dict | str):
        self.status_code = status_code
        self._body = body

    def json(self):
        if isinstance(self._body, str):
            raise ValueError("no json")
        return self._body

    @property
    def text(self) -> str:
        return self._body if isinstance(self._body, str) else str(self._body)


def test_send_telegram_retries_without_markdown(monkeypatch):
    """Si Telegram rechaza el Markdown, el mensaje debe llegar igual (texto plano)."""
    from pyro import notify

    seen = []

    def fake_post(url, data=None, timeout=None):
        seen.append(dict(data))
        if "parse_mode" in data:
            return FakeResponse(400, "Bad Request: can't parse entities")
        return FakeResponse(200, {"ok": True, "result": {"message_id": 7}})

    monkeypatch.setattr(notify.requests, "post", fake_post)
    out = notify.send_telegram("hola *mundo", token="t", chat_id="1")
    assert out["ok"] is True
    assert len(seen) == 2
    assert seen[0]["parse_mode"] == "Markdown"
    assert "parse_mode" not in seen[1]
    assert seen[1]["text"] == "hola *mundo"


def test_send_telegram_without_credentials_raises(monkeypatch):
    from pyro import notify

    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    with pytest.raises(RuntimeError, match="faltan"):
        notify.send_telegram("x")
