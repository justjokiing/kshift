# Integration harness

Three tiers, increasing fidelity and risk. The unit tests in `tests/` stay the
fast default; these tests cover what mocks cannot.

| Tier | File | Needs | What it proves |
| --- | --- | --- | --- |
| 1 | `test_cli_recovery.py` | Python + `systemd-analyze` | real config parsing, log handler → parser round-trip, unit rendering, reload calls, sandbox environment, idempotent re-runs, calendar expressions, static unit verification |
| 2 | `test_private_systemd.py` | `KSHIFT_RUN_INTEGRATION=1`, `systemd`, `dbus-daemon` | daemon-reload, timer removal, persistent catch-up, ExecStart, service results |
| 3 | `test_plasma_live.py` | `KSHIFT_RUN_PLASMA=1`, live Plasma | the theme actually applies (colour scheme) and is restored |

## Run

```bash
# tier 1 (always safe, also runs under plain pytest)
python -m pytest tests/integration -q

# tiers 1 + 2
KSHIFT_RUN_INTEGRATION=1 python -m pytest tests/integration -q

# tiers 1 + 2 + 3 (changes and restores your colour scheme)
KSHIFT_RUN_PLASMA=1 KSHIFT_RUN_INTEGRATION=1 \
  python -m pytest tests/integration -q

# or the wrapper
scripts/e2e-kshift.sh
```

## CI

`python-package.yml` runs the unit tests plus Tier 1 on every push/PR (any
target branch, so stacked PRs get CI) and on pushes to `main`/`develop`, on
Python 3.11–3.13. Tier 1 needs no KDE, no systemd manager and no network.
Formatting is enforced once, by `yapf_check.yml`; the build matrix only runs
flake8 and pytest.

Tier 2 needs a user manager. **GitHub-hosted runners cannot provide one**: a
dispatched run on `ubuntu-latest` started `dbus-daemon` but `systemd --user`
never accepted a `daemon-reload`, so every test skipped (each after the 20 s
startup probe) and the job still reported success. To avoid that false green:

* the job is skipped unless the repository variable
  `KSHIFT_SYSTEMD_RUNNER` names a self-hosted runner label;
* when it does run it sets `KSHIFT_REQUIRE_INTEGRATION=1`, which turns a
  missing manager into a **failure** instead of a skip.

Enable it by registering a self-hosted runner (a Plasma host is ideal) and
setting `KSHIFT_SYSTEMD_RUNNER` under *Settings → Variables → Actions*. It then
runs nightly and on `workflow_dispatch`. Tier 3 is local or self-hosted only.

`tests/conftest.py` redirects `HOME`, `XDG_*`, `PATH` and `TZ` for the whole
session, so the suite cannot touch the developer's session or write to the
real cache. The sandbox for subprocess-based tests passes the same `TZ`
explicitly, because an environment dict without `TZ` falls back to the host
zone. Tests that need the live session read `KSHIFT_TEST_REAL_HOME`,
`KSHIFT_TEST_REAL_PATH` and `KSHIFT_TEST_REAL_RUNTIME`.

The live sun API test is marked `network` and skipped unless
`KSHIFT_RUN_NETWORK=1`.

`pytest-timeout` is a development dependency; the timeout is passed by CI
(`--timeout=180`, `--timeout=300` for Tier 2) rather than through `addopts`, so
a plain `pytest` run still works where the plugin is not installed.

## How Tier 1/2 isolate themselves

Each test gets a throwaway `HOME` with `XDG_CONFIG_HOME`, `XDG_DATA_HOME` and
`XDG_CACHE_HOME` inside it, plus a `bin/` containing:

* `kshift` — a wrapper around `sys.executable -m kshift.main`
* `plasma-apply-*` — shims that record applications in `applied.log`

Calendar-schedule tests additionally put a **fake `systemctl`** first on `PATH`
so nothing reaches the live user manager; it logs every call to
`systemctl.log`.

Tier 2 starts a private `systemd --user` on a private session bus with its own
`XDG_RUNTIME_DIR`, so enabling units and triggering timers never touches the
real manager.

## Gotchas that cost time when building this

* **Service `PATH` is not your shell `PATH`.** A user manager does not
  necessarily import `PATH`, so `which("kshift")` inside a unit can fail and
  `write_systemd()` rewrite `ExecStart=kshift` (then fail with `203/EXEC`).
  Tier 2 calls `systemctl --user set-environment PATH=...` and points units at
  the absolute fake `kshift` wrapper.
* **Persistent timers do not fire on their first start.** Write
  `$XDG_DATA_HOME/systemd/timers/stamp-<unit>.timer` with an old mtime, then
  restart the timer to simulate missed runs.
* **`journalctl --user` cannot see the private manager.** Assert through
  `systemctl show -p Result,ExecMainStatus` or the `command:` hook.
* **A fresh bus without a compositor can hang `plasma-apply-colorscheme -l`.**
  `kshift.conf` builds default themes at import, which runs the real binary;
  keep the shims first on `PATH` for headless tiers.
* **No display in the service environment.** `systemctl --user
  show-environment` on Plasma/Wayland may lack `WAYLAND_DISPLAY`/`DISPLAY`;
  verify GUI attributes through a timer separately from a manual run.
* **Tear the manager down explicitly** (`systemctl --user exit`, then
  terminate the bus). Otherwise `dbus-run-session`-style wrappers hang.
* **Timer units currently form an ordering cycle** (`After=` other themes'
  services on the timer). `systemd-analyze verify` catches it; the verify test
  is marked `xfail` until that is fixed separately.

## Known gaps

The additions this harness does not cover yet live in [`BACKLOG.md`](BACKLOG.md),
each with the test that would prove it and the change that has to land first.
Short version:

* ordering cycle in the generated timers (production fix; strict `xfail` today)
* log rotation, DST policy, mixed calendar/daytime configs (decisions first)
* failure injection, command quoting, concurrent runs, coverage (later passes)
* Tier 2 on a self-hosted runner (`KSHIFT_SYSTEMD_RUNNER`)
