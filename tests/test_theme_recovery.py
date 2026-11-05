import importlib
import json
import subprocess
from datetime import datetime
from types import SimpleNamespace

import pytest


@pytest.fixture
def main_module(mocker):

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


def _themes(sunrise, sunset):
    return {
        "day": SimpleNamespace(time=[sunrise]),
        "night": SimpleNamespace(time=[sunset]),
    }


def test_caught_up_day_and_night_timers_converge_to_current_theme(
        main_module, tmp_path, monkeypatch):
    # Both persistent timers can run together after downtime. Each service must
    # make the same current-time decision instead of applying its named theme.
    themes = _themes(datetime(2026, 11, 5, 6, 42, 0),
                     datetime(2026, 11, 5, 16, 26, 4))
    now = datetime(2026, 11, 5, 18, 22, 51)

    assert main_module._select_current_theme(themes, now) == "night"
    assert main_module._select_current_theme(themes, now) == "night"

    systemd_dir = tmp_path / "systemd"
    template_dir = tmp_path / "templates"
    systemd_dir.mkdir()
    template_dir.mkdir()
    for template in ("template.service", "template.timer"):
        source = main_module.files("kshift") / "templates" / template
        (template_dir / template).write_text(source.read_text())
    config = SimpleNamespace(
        themes=themes,
        systemd_loc=systemd_dir,
        config_loc_base=tmp_path,
    )
    monkeypatch.setattr(main_module, "c", config)
    monkeypatch.setattr(main_module, "which", lambda _: "/usr/bin/kshift")
    monkeypatch.setattr(main_module, "system", lambda _: 0)
    main_module.write_systemd()
    for name in ("day", "night"):
        service = (systemd_dir / f"kshift-{name}.service").read_text()
        assert "ExecStart=/usr/bin/kshift theme\n" in service


def test_recovery_before_sunrise_after_midnight_uses_previous_sunset(
        main_module):
    themes = _themes(datetime(2026, 11, 5, 6, 42, 0),
                     datetime(2026, 11, 5, 16, 26, 4))

    assert main_module._select_current_theme(themes,
                                             datetime(2026, 11, 6, 0,
                                                      15)) == "night"
    assert main_module._select_current_theme(themes,
                                             datetime(2026, 11, 6, 6,
                                                      41)) == "night"
    assert main_module._select_current_theme(themes,
                                             datetime(2026, 11, 6, 6,
                                                      43)) == "day"


def test_oncalendar_minute_boundary_matches_solar_time_with_seconds(
        main_module):
    themes = _themes(datetime(2026, 11, 5, 6, 42, 0),
                     datetime(2026, 11, 5, 16, 26, 4))

    assert main_module._select_current_theme(themes,
                                             datetime(2026, 11, 5, 16, 26,
                                                      0)) == "night"


def test_parse_theme_logs_strips_timestamp_whitespace(tmp_path, monkeypatch,
                                                      main_module):
    monkeypatch.setattr(main_module, "c",
                        SimpleNamespace(themes={"night": object()}))
    log_file = tmp_path / "kshift.log"
    log_file.write_text("2026-11-05 18:22:57  - INFO - " +
                        json.dumps({
                            "event": "theme_change",
                            "theme": "night",
                            "source": "systemd"
                        }) + "\n")

    assert main_module.parse_theme_logs(log_file) == ("night",
                                                      datetime(
                                                          2026, 11, 5, 18, 22,
                                                          57))


def test_calendar_expression_services_keep_named_theme(main_module, tmp_path,
                                                       monkeypatch):
    systemd_dir = tmp_path / "systemd"
    template_dir = tmp_path / "templates"
    systemd_dir.mkdir()
    template_dir.mkdir()
    for template in ("template.service", "template.timer"):
        source = main_module.files("kshift") / "templates" / template
        (template_dir / template).write_text(source.read_text())

    themes = {
        "night":
        SimpleNamespace(time=["Mon..Fri *-*-* 20:00:00"]),
        "mixed":
        SimpleNamespace(
            time=[datetime(2026, 11, 5, 16, 26), "Mon..Fri *-*-* 20:00:00"]),
    }
    monkeypatch.setattr(
        main_module, "c",
        SimpleNamespace(themes=themes,
                        systemd_loc=systemd_dir,
                        config_loc_base=tmp_path))
    monkeypatch.setattr(main_module, "which", lambda _: "/usr/bin/kshift")
    monkeypatch.setattr(main_module, "system", lambda _: 0)
    main_module.write_systemd()

    for name in ("night", "mixed"):
        service = (systemd_dir / f"kshift-{name}.service").read_text()
        assert f"ExecStart=/usr/bin/kshift theme {name}\n" in service


def test_legacy_systemd_theme_argument_is_rechecked(main_module, monkeypatch):
    applied = []
    themes = {
        "day":
        SimpleNamespace(time=[datetime(2026, 11, 5, 6, 42)],
                        kshift=lambda: applied.append("day")),
        "night":
        SimpleNamespace(time=[datetime(2026, 11, 5, 16, 26, 4)],
                        kshift=lambda: applied.append("night")),
    }
    monkeypatch.setattr(main_module, "c", SimpleNamespace(themes=themes))
    monkeypatch.setattr(main_module,
                        "getenv",
                        lambda key, default=None: "systemd"
                        if key == "SOURCE" else default)
    monkeypatch.setattr(
        main_module.subprocess, "run", lambda *args, **kwargs: subprocess.
        CompletedProcess(args[0], 0, stdout=b"enabled"))
    monkeypatch.setattr(main_module, "parse_theme_logs", lambda *args: None)
    monkeypatch.setattr(main_module, "write_systemd", lambda: None)
    monkeypatch.setattr(main_module,
                        "_select_current_theme",
                        lambda configs, last_log_theme=None: "night")

    from click.testing import CliRunner

    result = CliRunner().invoke(main_module.cli, ["theme", "day"])

    assert result.exit_code == 0
    assert applied == ["night"]


def test_legacy_mixed_calendar_theme_keeps_named_activation(
        main_module, monkeypatch, tmp_path):
    applied = []
    now = datetime.now()
    themes = {
        "day":
        SimpleNamespace(time=[now.replace(hour=(now.hour - 2) % 24)],
                        kshift=lambda: applied.append("day")),
        "night":
        SimpleNamespace(time=[
            now.replace(hour=(now.hour - 1) % 24), "Mon..Fri *-*-* 20:00:00"
        ],
                        kshift=lambda: applied.append("night")),
    }
    monkeypatch.setattr(main_module, "c", SimpleNamespace(themes=themes))
    monkeypatch.setattr(main_module,
                        "getenv",
                        lambda key, default=None: "systemd"
                        if key == "SOURCE" else default)
    monkeypatch.setattr(
        main_module.subprocess, "run", lambda *args, **kwargs: subprocess.
        CompletedProcess(args[0], 0, stdout=b"enabled"))
    monkeypatch.setattr(main_module, "write_systemd", lambda: None)

    from click.testing import CliRunner

    result = CliRunner().invoke(main_module.cli, ["theme", "night"])

    assert result.exit_code == 0
    assert applied == ["night"]
