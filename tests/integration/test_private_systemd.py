"""Tier 2: real systemd units inside a private ``systemd --user``.

Run with ``KSHIFT_RUN_INTEGRATION=1``. See ``tests/integration/README.md``.
"""
import pytest

pytestmark = pytest.mark.integration


def _install(sandbox, manager, day=None, night=None):
    sandbox.write_config(
        sandbox.themes(day if day is not None else sandbox.past(2),
                       night if night is not None else sandbox.past(1)))
    manager.install()


def test_install_generates_daily_services(sandbox, private_manager):
    _install(sandbox, private_manager)

    for name in ("day", "night"):
        service = (sandbox.units / f"kshift-{name}.service").read_text()
        assert f"ExecStart={sandbox.bin}/kshift theme\n" in service
        enabled = private_manager.systemctl("is-enabled",
                                            f"kshift-{name}.timer")
        assert enabled.stdout.strip() == "enabled"


def test_catch_up_converges_on_current_theme(sandbox, private_manager):
    _install(sandbox, private_manager)

    # Simulate a machine that was off over both schedules: the stamp files
    # record the last run, so restarting the timers fires them immediately.
    private_manager.write_stamps(["kshift-day.timer", "kshift-night.timer"])
    sandbox.applied.unlink(missing_ok=True)
    private_manager.systemctl("restart", "kshift-day.timer",
                              "kshift-night.timer")
    private_manager.wait_services(
        ["kshift-day.service", "kshift-night.service"])

    assert set(sandbox.applied_themes()) == {"night"}
    for unit in ("kshift-day.service", "kshift-night.service"):
        assert private_manager.show(unit)["Result"] == "success"


def test_removed_timer_unloads_from_manager(sandbox, private_manager):
    _install(sandbox, private_manager)
    assert private_manager.show("kshift-day.timer")["LoadState"] == "loaded"

    sandbox.write_config(sandbox.themes([], sandbox.past(1)))
    private_manager.run("theme")

    assert not (sandbox.units / "kshift-day.timer").exists()
    assert private_manager.show("kshift-day.timer")["LoadState"] == "not-found"
