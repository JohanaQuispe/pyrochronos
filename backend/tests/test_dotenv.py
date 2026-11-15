"""El .env de la raiz debe cargarse solo, sin pisar lo que ya está en el sistema."""
from __future__ import annotations

import os

import pytest

from pyro.config import load_dotenv


@pytest.fixture(autouse=True)
def restore_environ():
    """load_dotenv escribe en os.environ: devolvemos todo a su sitio al terminar."""
    before = dict(os.environ)
    yield
    for key in [k for k in os.environ if k not in before]:
        del os.environ[key]
    os.environ.update(before)


def test_loads_keys_without_overriding(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text(
        "# comentario\n"
        "FIRMS_MAP_KEY=abc123\n"
        'TELEGRAM_BOT_TOKEN="1234567890:AAAA"\n'
        "TELEGRAM_CHAT_ID=8915000180\n"
        "export PYRO_SETUP_KEY=exportado\n"
        "linea sin igual\n"
        "\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("FIRMS_MAP_KEY", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.delenv("PYRO_SETUP_KEY", raising=False)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "111")  # ya definida: debe mandar

    added = load_dotenv(env)
    assert added == 3
    assert os.environ["FIRMS_MAP_KEY"] == "abc123"
    assert os.environ["TELEGRAM_BOT_TOKEN"] == "1234567890:AAAA"  # sin comillas
    assert os.environ["TELEGRAM_CHAT_ID"] == "111"
    assert os.environ["PYRO_SETUP_KEY"] == "exportado"


def test_missing_file_is_a_noop(tmp_path):
    assert load_dotenv(tmp_path / "no-existe.env") == 0


def test_repo_dotenv_is_ignored_by_git():
    from pyro.config import ROOT

    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in [line.strip() for line in ignore]
