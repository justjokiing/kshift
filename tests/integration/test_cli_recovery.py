"""Tier 1: the real CLI against a throwaway HOME and fake desktop tools.

These tests run everywhere. They exercise config parsing, unit rendering and
the real log handler/parser without needing systemd or Plasma.
"""
import shlex
import shutil
import subprocess
from datetime import datetime

import pytest


def test_log_roundtrip_uses_the_real_handler(sandbox):
    sandbox.write_config(sandbox.themes(sandbox.past(2), sandbox.past(1)))

    result = sandbox.run("theme",
                         env={
                             **sandbox.base_env, "SOURCE": "systemd"
                         })

    assert result.returncode == 0, result.stderr
    assert sandbox.applied_themes() == ["night"]

    parsed = sandbox.parse_log()
    assert parsed is not None, "the handler's own log line was not parseable"
    theme, when = parsed
    assert theme == "night"
    assert isinstance(when, datetime)


def test_removed_timer_triggers_daemon_reload(sandbox):
    if shutil.which("systemd-analyze") is None:
        pytest.skip("systemd-analyze is required for calendar schedules")

    # Calendar schedules keep the service text stable, so removing one
    # schedule only changes the set of timer units.
    calendar = ["Mon..Fri *-*-* 08:00:00"]
    sandbox.write_config(sandbox.themes(calendar, ["Mon..Fri *-*-* 20:00:00"]))
    assert sandbox.run("theme").returncode == 0
    assert (sandbox.units / "kshift-day.timer").exists()

    sandbox.systemctl_log.unlink(missing_ok=True)
    sandbox.write_config(sandbox.themes([], ["Mon..Fri *-*-* 20:00:00"]))
    assert sandbox.run("theme").returncode == 0

    assert not (sandbox.units / "kshift-day.timer").exists()
    assert "daemon-reload" in "\n".join(sandbox.systemctl_calls())

    # A no-op re-run must not reload the daemon again.
    sandbox.systemctl_log.unlink(missing_ok=True)
    assert sandbox.run("theme").returncode == 0
    assert not [
        call for call in sandbox.systemctl_calls() if "daemon-reload" in call
    ]


def test_generated_calendar_expressions_are_valid(sandbox):
    if shutil.which("systemd-analyze") is None:
        pytest.skip("systemd-analyze is not installed")

    # Mix a calendar expression with a plain HH:MM time so both forms written
    # by write_systemd() go through systemd's own parser.
    sandbox.write_config(
        sandbox.themes(["Mon..Fri *-*-* 08:00:00"], [sandbox.past(1)]))
    assert sandbox.run("theme").returncode == 0

    expressions = []
    for timer in sorted(sandbox.units.glob("kshift-*.timer")):
        for line in timer.read_text().splitlines():
            if line.startswith("OnCalendar="):
                expressions.append(line.partition("=")[2])

    assert expressions
    for expression in expressions:
        result = subprocess.run(["systemd-analyze", "calendar", expression],
                                text=True,
                                capture_output=True)
        assert result.returncode == 0, (expression, result.stderr)


def test_legacy_activation_rewrites_service(sandbox):
    sandbox.write_config(sandbox.themes(sandbox.past(2), sandbox.past(1)))

    legacy = sandbox.units / "kshift-day.service"
    sandbox.units.mkdir(parents=True, exist_ok=True)
    legacy.write_text("[Service]\nExecStart=/usr/bin/kshift theme day\n")

    result = sandbox.run("theme",
                         "day",
                         env={
                             **sandbox.base_env, "SOURCE": "systemd"
                         })

    assert result.returncode == 0, result.stderr
    assert sandbox.applied_themes() == ["night"]
    assert legacy.read_text().rstrip().endswith("theme")


def test_cli_sees_the_sandboxed_environment(sandbox):
    """The isolation must reach the subprocess, not just the pytest process."""
    probe = sandbox.root / "env.txt"
    recorder = sandbox.root / "record-env.sh"
    recorder.write_text("#!/bin/sh\n"
                        f"printf '%s|%s|%s\\n' \"$HOME\" \"${{TZ:-unset}}\" "
                        f"\"$XDG_CONFIG_HOME\" > {shlex.quote(str(probe))}\n")
    recorder.chmod(0o755)
    sandbox.write_config(
        {"iso": {
            "time": [sandbox.past(1)],
            "command": str(recorder),
        }})

    result = sandbox.run("theme")

    assert result.returncode == 0, result.stderr
    home, tz, config_home = probe.read_text().strip().split("|")
    assert home == str(sandbox.home)
    assert tz == sandbox.base_env["TZ"] == "UTC"
    assert config_home == str(sandbox.home / ".config")


def test_second_run_does_not_rewrite_units(sandbox):
    sandbox.write_config(sandbox.themes(sandbox.past(2), sandbox.past(1)))

    assert sandbox.run("theme").returncode == 0
    before = {
        path.name: path.read_bytes()
        for path in sandbox.units.glob("kshift-*")
    }
    sandbox.systemctl_log.unlink(missing_ok=True)

    assert sandbox.run("theme").returncode == 0
    after = {
        path.name: path.read_bytes()
        for path in sandbox.units.glob("kshift-*")
    }

    assert after == before
    mutations = [
        call for call in sandbox.systemctl_calls()
        if any(word in call.split()
               for word in ("daemon-reload", "enable", "start"))
    ]
    assert mutations == []


@pytest.mark.xfail(
    reason="pre-existing After= ordering cycle between generated timers",
    strict=True)
def test_generated_units_pass_verify(sandbox):
    if shutil.which("systemd-analyze") is None:
        pytest.skip("systemd-analyze is not installed")

    sandbox.write_config(sandbox.themes(sandbox.past(2), sandbox.past(1)))
    assert sandbox.run("theme").returncode == 0

    units = sorted(str(path) for path in sandbox.units.glob("kshift-*"))
    result = subprocess.run(["systemd-analyze", "verify", *units],
                            text=True,
                            capture_output=True)

    assert result.returncode == 0, result.stderr
