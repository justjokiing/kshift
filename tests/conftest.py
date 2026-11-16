"""Session-wide test isolation.

The suite must not depend on the developer's Plasma session, and it must not
write to the real HOME/cache. Before any test imports kshift, point HOME and
the XDG directories at a temporary tree and put small ``plasma-apply-*``
shims first on PATH.

Tests that genuinely need the live session read ``KSHIFT_TEST_REAL_HOME`` /
``KSHIFT_TEST_REAL_PATH`` / ``KSHIFT_TEST_REAL_RUNTIME``.
"""
import importlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

SESSION_HOME = None
REAL_HOME = None
REAL_PATH = None
REAL_RUNTIME = None

_LISTINGS = {
    "colorscheme": (" * BreezeClassic\n"
                    " * BreezeDark (current color scheme)\n"
                    " * BreezeLight\n"),
    "cursortheme": (" * BreezeDark [BreezeDark]\n"
                    " * Oxygen [Oxygen]\n"),
    "desktoptheme": (" * breeze\n"
                     " * breeze-dark (current)\n"),
}


def _write_shims(bin_dir: Path):
    for tool, listing in _LISTINGS.items():
        script = ("#!/bin/sh\n"
                  'case "$1" in\n'
                  "  -l|--list-themes)\n"
                  "    cat <<'EOF'\n"
                  f"{listing}"
                  "EOF\n"
                  "    ;;\n"
                  "  *)\n"
                  f'    [ -n "$KSHIFT_TEST_APPLIED" ] && '
                  f'echo "APPLIED {tool} $*" >> "$KSHIFT_TEST_APPLIED"\n'
                  "    ;;\n"
                  "esac\n"
                  "exit 0\n")
        path = bin_dir / f"plasma-apply-{tool}"
        path.write_text(script)
        path.chmod(0o755)

    wallpaper = bin_dir / "plasma-apply-wallpaperimage"
    wallpaper.write_text("#!/bin/sh\n"
                         '[ -n "$KSHIFT_TEST_APPLIED" ] && '
                         'echo "APPLIED wallpaperimage $*" '
                         '>> "$KSHIFT_TEST_APPLIED"\n'
                         "exit 0\n")
    wallpaper.chmod(0o755)


def pytest_configure(config):
    global SESSION_HOME, REAL_HOME, REAL_PATH, REAL_RUNTIME

    REAL_HOME = os.environ.get("HOME")
    REAL_PATH = os.environ.get("PATH", "")
    REAL_RUNTIME = os.environ.get("XDG_RUNTIME_DIR")

    SESSION_HOME = Path(tempfile.mkdtemp(prefix="kshift-tests-"))
    shim_bin = SESSION_HOME / "bin"
    shim_bin.mkdir()
    _write_shims(shim_bin)
    (SESSION_HOME / "run").mkdir(mode=0o700)

    os.environ.update({
        "HOME": str(SESSION_HOME),
        "XDG_CONFIG_HOME": str(SESSION_HOME / ".config"),
        "XDG_DATA_HOME": str(SESSION_HOME / ".local/share"),
        "XDG_CACHE_HOME": str(SESSION_HOME / ".cache"),
        "XDG_RUNTIME_DIR": str(SESSION_HOME / "run"),
        "PATH": f"{shim_bin}:{REAL_PATH}",
        "TZ": "UTC",
        "KSHIFT_TEST_APPLIED": str(SESSION_HOME / "applied.log"),
        "KSHIFT_TEST_REAL_HOME": REAL_HOME or "",
        "KSHIFT_TEST_REAL_PATH": REAL_PATH,
        "KSHIFT_TEST_REAL_RUNTIME": REAL_RUNTIME or "",
    })
    config._kshift_session_home = str(SESSION_HOME)


def pytest_unconfigure(config):
    home = getattr(config, "_kshift_session_home", None)
    if home:
        shutil.rmtree(home, ignore_errors=True)


def pytest_collection_modifyitems(config, items):
    if os.environ.get("KSHIFT_RUN_NETWORK") == "1":
        return
    skip = pytest.mark.skip(
        reason="set KSHIFT_RUN_NETWORK=1 to call the live sun API")
    for item in items:
        if item.get_closest_marker("network") is not None:
            item.add_marker(skip)


@pytest.fixture
def main_module(mocker):
    """Import ``kshift.main`` with its import-time side effects stubbed out.

    Importing the module builds default themes and asks for the sun data, which
    would otherwise reach the graphics stack and the network.
    """

    def run(command, **kwargs):
        if isinstance(command, str):
            command = command.split()
        if command[0] == "plasma-apply-colorscheme":
            return subprocess.CompletedProcess(
                command, 0, "  * BreezeLight\n  * BreezeDark\n")
        return subprocess.CompletedProcess(command, 0, "")

    from kshift.theme import Colorscheme

    mocker.patch.object(Colorscheme, "available", [])
    mocker.patch.object(Colorscheme, "current", None)
    mocker.patch.object(Colorscheme,
                        "fetch_colorschemes",
                        return_value=(["BreezeLight",
                                       "BreezeDark"], "BreezeDark"))
    mocker.patch("subprocess.run", side_effect=run)
    mocker.patch("requests.get", side_effect=ConnectionError("offline"))
    return importlib.import_module("kshift.main")
