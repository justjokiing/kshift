"""Tier 3: apply a real theme to the live Plasma session (opt-in).

Run with ``KSHIFT_RUN_PLASMA=1``. Only the colour scheme is touched and it is
restored in a ``finally`` block; kshift's config file is backed up as well.

The session-wide test fixtures redirect HOME/PATH for isolation, so this test
opts back into the real session via ``KSHIFT_TEST_REAL_*``.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.plasma

SRC = Path(__file__).resolve().parents[2] / "src"

REAL_HOME = Path(os.environ.get("KSHIFT_TEST_REAL_HOME") or os.environ["HOME"])
REAL_PATH = os.environ.get("KSHIFT_TEST_REAL_PATH") or os.environ["PATH"]
REAL_RUNTIME = os.environ.get("KSHIFT_TEST_REAL_RUNTIME") or os.environ.get(
    "XDG_RUNTIME_DIR", "")


def _current_scheme(env):
    return subprocess.run([
        "kreadconfig6", "--file", "kdeglobals", "--group", "General", "--key",
        "ColorScheme"
    ],
                          env=env,
                          text=True,
                          capture_output=True,
                          check=True).stdout.strip()


def test_live_colorscheme_roundtrip(tmp_path):
    for tool in ("kreadconfig6", "plasma-apply-colorscheme"):
        if shutil.which(tool, path=REAL_PATH) is None:
            pytest.skip(f"{tool} is not installed")

    # Keep kshift away from the live user manager: the stub reports the
    # startup timer as disabled, so `kshift theme` never rewrites units.
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "systemctl"
    stub.write_text("#!/bin/sh\n"
                    'case "$*" in\n'
                    "  *is-enabled*) echo disabled ;;\n"
                    "esac\n"
                    "exit 0\n")
    stub.chmod(0o755)

    env = {
        **os.environ,
        "HOME": str(REAL_HOME),
        "XDG_CONFIG_HOME": str(REAL_HOME / ".config"),
        "XDG_DATA_HOME": str(REAL_HOME / ".local/share"),
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
        "XDG_RUNTIME_DIR": REAL_RUNTIME,
        "PATH": f"{bin_dir}:{REAL_PATH}",
        "PYTHONPATH": str(SRC),
    }

    original = _current_scheme(env)
    target = "BreezeLight" if original != "BreezeLight" else "BreezeDark"

    config = REAL_HOME / ".config/kshift/kshift.yml"
    backup = config.read_text() if config.exists() else None

    try:
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(
            yaml.safe_dump({
                "webdata": False,
                "themes": {
                    "it": {
                        "colorscheme": target
                    }
                }
            }))

        result = subprocess.run(
            [sys.executable, "-m", "kshift.main", "theme", "it"],
            env=env,
            text=True,
            capture_output=True,
            timeout=120)
        assert result.returncode == 0, result.stderr
        assert _current_scheme(env) == target
    finally:
        subprocess.run(["plasma-apply-colorscheme", original],
                       env=env,
                       capture_output=True)
        if backup is None:
            config.unlink(missing_ok=True)
        else:
            config.write_text(backup)
