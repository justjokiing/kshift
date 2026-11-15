"""Fixtures for kshift's opt-in integration tests.

There are two tiers:

* The CLI tests (no marker) run everywhere and exercise the real command line
  against a throwaway HOME and fake ``plasma-apply-*``/``systemctl`` binaries.
* The systemd tests are marked ``integration`` and need
  ``KSHIFT_RUN_INTEGRATION=1``. They start a private ``systemd --user`` on a
  private session bus, so the live user manager is never touched.

Live Plasma tests live in ``test_plasma_live.py`` and need
``KSHIFT_RUN_PLASMA=1``. See ``tests/integration/README.md``.
"""
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src"

SYSTEMD = next(
    (path for path in (Path("/usr/lib/systemd/systemd"),
                       Path("/lib/systemd/systemd")) if path.exists()), None)


def _unavailable(reason):
    """Skip the tier, or fail it when the run asked for it explicitly.

    A CI job that silently skips every test is worse than no job: it reports
    success while proving nothing. ``KSHIFT_REQUIRE_INTEGRATION=1`` turns a
    missing user manager into a failure so the harness cannot pass by skipping.
    """
    if os.environ.get("KSHIFT_REQUIRE_INTEGRATION") == "1":
        pytest.fail(reason)
    pytest.skip(reason)


def pytest_collection_modifyitems(config, items):
    skip_integration = pytest.mark.skip(
        reason="set KSHIFT_RUN_INTEGRATION=1 to start a private systemd --user"
    )
    skip_plasma = pytest.mark.skip(
        reason="set KSHIFT_RUN_PLASMA=1 to touch the live Plasma session")

    for item in items:
        if item.get_closest_marker("integration") is not None:
            if os.environ.get("KSHIFT_RUN_INTEGRATION") != "1":
                item.add_marker(skip_integration)
        if item.get_closest_marker("plasma") is not None:
            if os.environ.get("KSHIFT_RUN_PLASMA") != "1":
                item.add_marker(skip_plasma)


class Sandbox:
    """A throwaway HOME plus fake desktop tools for one test."""

    def __init__(self, root: Path):
        self.root = root
        self.home = root / "home"
        self.bin = root / "bin"
        self.stub_bin = root / "stub-bin"
        self.runtime = root / "run"
        self.applied = root / "applied.log"
        self.systemctl_log = root / "systemctl.log"

        for directory in (self.home, self.bin, self.stub_bin, self.runtime):
            directory.mkdir(parents=True)
        self.runtime.chmod(0o700)

        shutil.copytree(SRC / "kshift/templates",
                        self.home / ".config/kshift/templates",
                        dirs_exist_ok=True)
        (self.home / ".local/share/systemd/user").mkdir(parents=True)

        self._write_desktop_shims()
        self._write_kshift_wrapper()
        self._write_systemctl_stub()

        self.base_env = {
            "HOME": str(self.home),
            "XDG_CONFIG_HOME": str(self.home / ".config"),
            "XDG_DATA_HOME": str(self.home / ".local/share"),
            "XDG_CACHE_HOME": str(self.home / ".cache"),
            "XDG_RUNTIME_DIR": str(self.runtime),
            "PATH": f"{self.stub_bin}:{self.bin}:/usr/local/bin:/usr/bin:/bin",
            "PYTHONPATH": str(SRC),
            "TZ": os.environ.get("TZ", "UTC"),
            "KSHIFT_TEST_APPLIED": str(self.applied),
            "KSHIFT_TEST_SYSTEMCTL_LOG": str(self.systemctl_log),
            "NO_COLOR": "1",
        }

    @property
    def units(self) -> Path:
        return self.home / ".local/share/systemd/user"

    @property
    def config_path(self) -> Path:
        return self.home / ".config/kshift/kshift.yml"

    def write_config(self, themes):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            yaml.safe_dump({
                "webdata": False,
                "themes": themes
            },
                           sort_keys=False))

    def hook(self, name: str) -> str:
        """A theme command that records which theme was applied."""
        return f"sh -c 'echo {name} >> {shlex.quote(str(self.applied))}'"

    def themes(self, day_time, night_time):
        return {
            "day": {
                "time": day_time,
                "command": self.hook("day")
            },
            "night": {
                "time": night_time,
                "command": self.hook("night")
            },
        }

    @staticmethod
    def past(hours: int) -> str:
        """An HH:MM time that already happened today (modulo midnight)."""
        return (datetime.now() - timedelta(hours=hours)).strftime("%H:%M")

    def run(self, *args, env=None, input=None, timeout=120):
        return subprocess.run([sys.executable, "-m", "kshift.main", *args],
                              cwd=self.root,
                              env=env or self.base_env,
                              input=input,
                              text=True,
                              capture_output=True,
                              timeout=timeout)

    def applied_themes(self):
        if not self.applied.exists():
            return []
        lines = (line.strip()
                 for line in self.applied.read_text().splitlines())
        return [
            line for line in lines if line and not line.startswith("APPLIED")
        ]

    def systemctl_calls(self):
        if not self.systemctl_log.exists():
            return []
        return self.systemctl_log.read_text().splitlines()

    def parse_log(self):
        """Run the real parser against the log written by the real handler."""
        code = (
            "import json\n"
            "from kshift.main import log_file, parse_theme_logs\n"
            "parsed = parse_theme_logs(log_file)\n"
            "print('KSHIFT_PARSED=' + json.dumps(\n"
            "    [parsed[0], parsed[1].isoformat()] if parsed else None))\n")
        result = subprocess.run([sys.executable, "-c", code],
                                cwd=self.root,
                                env=self.base_env,
                                text=True,
                                capture_output=True,
                                timeout=120)
        assert result.returncode == 0, result.stderr
        for line in result.stdout.splitlines():
            if line.startswith("KSHIFT_PARSED="):
                parsed = json.loads(line.partition("=")[2])
                if parsed is None:
                    return None
                return parsed[0], datetime.fromisoformat(parsed[1])
        raise AssertionError(f"parser produced no output: {result.stdout!r}")

    def _write_desktop_shims(self):
        listings = {
            "colorscheme": (" * BreezeClassic\n"
                            " * BreezeDark (current color scheme)\n"
                            " * BreezeLight\n"),
            "cursortheme": (" * BreezeDark [BreezeDark]\n"
                            " * Oxygen [Oxygen]\n"),
            "desktoptheme": (" * breeze\n"
                             " * breeze-dark (current)\n"),
        }
        for tool, listing in listings.items():
            script = (
                "#!/bin/sh\n"
                'case "$1" in\n'
                "  -l|--list-themes)\n"
                "    cat <<'EOF'\n"
                f"{listing}"
                "EOF\n"
                "    ;;\n"
                "  *)\n"
                f'    echo "APPLIED {tool} $*" >> "$KSHIFT_TEST_APPLIED"\n'
                "    ;;\n"
                "esac\n"
                "exit 0\n")
            path = self.bin / f"plasma-apply-{tool}"
            path.write_text(script)
            path.chmod(0o755)

        wallpaper = self.bin / "plasma-apply-wallpaperimage"
        wallpaper.write_text("#!/bin/sh\n"
                             'echo "APPLIED wallpaperimage $*" '
                             '>> "$KSHIFT_TEST_APPLIED"\n')
        wallpaper.chmod(0o755)

    def _write_kshift_wrapper(self):
        wrapper = self.bin / "kshift"
        wrapper.write_text("#!/bin/sh\n"
                           f"exec {shlex.quote(sys.executable)} "
                           '-m kshift.main "$@"\n')
        wrapper.chmod(0o755)

    def _write_systemctl_stub(self):
        stub = self.stub_bin / "systemctl"
        stub.write_text("#!/bin/sh\n"
                        'echo "systemctl $*" >> "$KSHIFT_TEST_SYSTEMCTL_LOG"\n'
                        'case "$*" in\n'
                        "  *is-enabled*) echo enabled ;;\n"
                        "esac\n"
                        "exit 0\n")
        stub.chmod(0o755)


class PrivateUserManager:
    """A disposable ``systemd --user`` that never sees the live manager."""

    def __init__(self, root: Path, sandbox: Sandbox):
        self.root = root
        self.sandbox = sandbox
        self.runtime = root / "run"
        self.runtime.mkdir(parents=True, mode=0o700)
        self.bus = None
        self.proc = None
        self.env = None

    def start(self):
        if SYSTEMD is None or shutil.which("dbus-daemon") is None:
            _unavailable("dbus-daemon or the systemd binary is unavailable")

        self.bus = subprocess.Popen([
            shutil.which("dbus-daemon"), "--session", "--nofork",
            "--print-address=1"
        ],
                                    stdout=subprocess.PIPE,
                                    text=True)
        address = self.bus.stdout.readline().strip()
        assert address, "dbus-daemon did not print an address"

        self.env = {
            **self.sandbox.base_env,
            "DBUS_SESSION_BUS_ADDRESS": address,
            "XDG_RUNTIME_DIR": str(self.runtime),
            "PATH": f"{self.sandbox.bin}:/usr/local/bin:/usr/bin:/bin",
        }
        self.proc = subprocess.Popen([str(SYSTEMD), "--user"],
                                     env=self.env,
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL,
                                     start_new_session=True)

        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if self.systemctl("daemon-reload").returncode == 0:
                break
            time.sleep(0.1)
        else:
            self.stop()
            _unavailable(
                "private systemd --user did not start; hosted runners usually "
                "forbid a user manager, so run this tier on a self-hosted "
                "runner or a workstation")

        self.systemctl("set-environment", f"PATH={self.env['PATH']}",
                       f"HOME={self.env['HOME']}",
                       f"PYTHONPATH={self.env['PYTHONPATH']}")

    def stop(self):
        if self.proc is not None and self.proc.poll() is None:
            try:
                self.systemctl("exit", timeout=10)
            except (subprocess.TimeoutExpired, OSError):
                pass
        for process in (self.proc, self.bus):
            if process is None or process.poll() is not None:
                continue
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        if self.bus is not None and self.bus.stdout is not None:
            self.bus.stdout.close()

    def systemctl(self, *args, timeout=30):
        return subprocess.run(["systemctl", "--user", *args],
                              env=self.env,
                              text=True,
                              capture_output=True,
                              timeout=timeout)

    def install(self):
        result = self.sandbox.run("install",
                                  env=self.env,
                                  input="y\n",
                                  timeout=120)
        assert result.returncode == 0, result.stderr
        self.wait_services(["kshift-startup.service"])

    def run(self, *args):
        result = self.sandbox.run(*args, env=self.env, timeout=120)
        assert result.returncode == 0, result.stderr
        return result

    def write_stamps(self, units, age_seconds=86400):
        stamps = self.sandbox.home / ".local/share/systemd/timers"
        stamps.mkdir(parents=True, exist_ok=True)
        timestamp = time.time() - age_seconds
        for unit in units:
            stamp = stamps / f"stamp-{unit}"
            stamp.touch()
            os.utime(stamp, (timestamp, timestamp))

    def wait_services(self, units, timeout=60):
        """Wait until every unit has run and is no longer transitioning.

        ``is-active`` alone is not enough: a unit that has not started yet also
        reports ``inactive``, so the first poll after a timer restart can look
        settled before the service ever ran.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if all(self._settled(unit) for unit in units):
                return
            time.sleep(0.2)
        raise AssertionError(f"services did not settle: {units}")

    def _settled(self, unit):
        info = self.show(unit)
        if not info.get("ActiveEnterTimestamp"):
            return False
        return info.get("ActiveState") not in ("active", "activating",
                                               "reloading", "deactivating")

    def show(self, unit):
        output = self.systemctl("show", unit, "-p", "LoadState", "-p",
                                "ActiveState", "-p", "ActiveEnterTimestamp",
                                "-p", "Result", "-p", "ExecMainStatus").stdout
        return dict(
            line.split("=", 1) for line in output.splitlines() if "=" in line)


@pytest.fixture
def sandbox(tmp_path):
    return Sandbox(tmp_path / "sandbox")


@pytest.fixture
def private_manager(tmp_path, sandbox):
    manager = PrivateUserManager(tmp_path / "manager", sandbox)
    manager.start()
    try:
        yield manager
    finally:
        manager.stop()
