"""El chequeo general no debe filtrar claves y debe decir el siguiente paso."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "backend" / "scripts" / "doctor.py"
FAKE_TOKEN = "1234567890:" + "B" * 35


def run(extra_env=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("TELEGRAM_", "FIRMS_", "PYRO_"))}
    env.update(extra_env or {})
    return subprocess.run(
        [sys.executable, str(SCRIPT)], cwd=ROOT, capture_output=True, text=True, timeout=180, env=env
    )


def test_reports_without_env_and_gives_next_step():
    out = run().stdout
    assert "dependencias de Python instaladas" in out
    assert "SIGUIENTE PASO" in out
    assert ".env" in out


def test_never_prints_full_token():
    out = run({"TELEGRAM_BOT_TOKEN": FAKE_TOKEN, "TELEGRAM_CHAT_ID": "8915000180"}).stdout
    assert FAKE_TOKEN not in out
    assert "…" in out  # versión enmascarada
    assert "chat personal" in out


def test_warns_when_chat_id_is_not_numeric():
    out = run({"TELEGRAM_CHAT_ID": "mi-casa"}).stdout
    assert "no es un número" in out
