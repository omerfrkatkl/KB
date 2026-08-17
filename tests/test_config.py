"""WP0.1 — the config layer and the bootstrap's idempotency."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from knowledge_base import config

ROOT = Path(__file__).resolve().parents[1]


def test_repo_config_loads():
    s = config.load(ROOT / "config.yaml")
    assert set(s.fields) == {"complex-analysis", "ordinary-differential-equations"}
    assert s.fields["complex-analysis"].title == "Complex Analysis"
    assert s.capture_folders.board == "Lecture-Boards"


def test_round_trip(tmp_path):
    s = config.load(ROOT / "config.yaml")
    out = tmp_path / "config.yaml"
    config.dump(s, out)
    assert config.load(out) == s


def test_unknown_key_is_rejected(tmp_path):
    """A silently ignored setting is indistinguishable from one never applied."""
    text = (ROOT / "config.yaml").read_text(encoding="utf-8") + "\nmax_pages: 12\n"
    p = tmp_path / "config.yaml"
    p.write_text(text, encoding="utf-8", newline="")
    with pytest.raises(Exception):
        config.load(p)


def test_measured_values_start_unset():
    """Phase-0 measurements must not ship with plausible-looking guesses."""
    s = config.load(ROOT / "config.yaml")
    assert s.measured() == {
        "budget.max_pages_per_night": False,
        "resolution_floor_px": False,
    }


TYPST = ROOT / "tools" / "typst"


@pytest.mark.skipif(not TYPST.exists(), reason="run `make bootstrap` to vendor typst")
def test_bootstrap_is_idempotent():
    """A second run must fetch nothing and must not rewrite the manifest."""
    manifest = ROOT / "template" / "TOOL-SHAS.txt"
    before = manifest.read_bytes()
    r = subprocess.run(
        [sys.executable, "-m", "knowledge_base.ops.bootstrap", "--check"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert manifest.read_bytes() == before


@pytest.mark.skipif(not TYPST.exists(), reason="run `make bootstrap` to vendor typst")
def test_bootstrap_detects_a_tampered_artefact(tmp_path):
    """The pin is the whole point: a changed byte must fail, not warn."""
    font = ROOT / "fonts" / "FiraSans-Regular.ttf"
    backup = tmp_path / "backup.ttf"
    shutil.copy(font, backup)
    try:
        font.write_bytes(backup.read_bytes() + b"\x00")
        r = subprocess.run(
            [sys.executable, "-m", "knowledge_base.ops.bootstrap", "--check"],
            capture_output=True, text=True, cwd=ROOT,
        )
        assert r.returncode == 1
        assert "sha256 mismatch" in r.stdout
    finally:
        shutil.copy(backup, font)
