# Integration test backlog

Everything the #32 review found that is **not** in the harness yet. The harness
is deliberately scoped to tests and CI; items that need a product decision or a
production change are listed here with the smallest test that would prove them
and the change that has to land first.

Use this list when planning work: an item is done when the named test exists,
fails against the old behaviour, and passes against the new one.

## Priority 1 — production change or decision required

### 1. Remove the cross-theme `After=` from the timer template

- **Problem**: every generated `kshift-<theme>.timer` declares
  `After=` the *other* themes' services. Because a timer is implicitly ordered
  before the service it activates, the units form an unfixable ordering cycle:

  ```
  kshift-night.timer/start after kshift-day.service/start
    after kshift-day.timer/start after kshift-night.service/start
    after kshift-night.timer
  ```

  `systemd-analyze verify` rejects it, and the Tier 1 verify test is a strict
  `xfail` because of it.

- **Why not in #32**: the fix is in `src/kshift/main.py` / the timer template;
  #32 changes tests and CI only.
- **Change**: drop `unit_options` (`After=...`) from the timer substitution, or
  move the ordering to the services if serialization is actually needed. The
  catch-up fix in #31 re-evaluates in every service, so cross-theme ordering is
  no longer required.
- **Test**: remove the `xfail` from `test_generated_units_pass_verify`; add a
  Tier 2 assertion that starting both timers in one transaction succeeds
  (`systemctl --user start kshift-day.timer kshift-night.timer`) and that both
  services still converge.
- **Done when**: `systemd-analyze verify` exits 0 and the un-xfailed test runs
  green on Tier 1 and Tier 2.

### 2. Decide what the log parser does after rotation

- **Problem**: `parse_theme_logs()` reads only the current `kshift.log`. The
  rotating handler keeps one backup, so an event that rotated into
  `kshift.log.1` between the timer catch-up and the recheck is invisible and
  the selector silently loses the "last applied" hint.
- **Why not in #32**: a test would either codify today's limitation or fail
  pending a decision.
- **Decision**: either read `kshift.log.1` as a fallback when the current file
  has no matching event, or accept the gap and document it as a known
  limitation with a reason (the schedule itself is still in the selector).
- **Test**: rotate with a small `RotatingFileHandler`, write only the backup,
  and assert the chosen behaviour. Add a truncated-final-line case either way.
- **Done when**: the behaviour is explicit and tested, not accidental.

### 3. Pick a DST policy for the selector

- **Problem**: `_select_current_theme` compares wall-clock minutes for "today"
  and "yesterday". A DST transition moves real elapsed time by an hour, so the
  previous day's occurrence can look an hour early or late.
- **Why not in #32**: correctness depends on the intended policy (wall clock
  probably is right for theme switching, but it should be stated).
- **Test**: pass an explicit `reference_time` across a spring-forward and a
  fall-back boundary (the selector already accepts one) and assert the
  documented choice. No `libfaketime` needed.
- **Done when**: the policy is in the docstring and covered by two tests.

### 4. Support, or explicitly reject, mixed calendar/daytime configs

- **Problem**: `_daily_schedules()` returns `False` when any timed theme uses a
  calendar expression or a mix of calendar and `datetime` entries. That keeps
  the named systemd activation for those configs, so the #31 catch-up fix does
  not apply to them. It is a silent behaviour switch.
- **Why not in #32**: whether mixed configs should be re-evaluated is a product
  question (comparing calendar occurrences is harder than comparing minutes).
- **Options**: (a) support mixed by evaluating each theme's next/previous
  occurrence, or (b) keep the legacy path but log a one-line warning at install
  time and document it.
- **Test**: the truth table in `tests/test_theme_selection.py` already pins the
  current policy; extend it with the chosen behaviour and an end-to-end Tier 1
  case.
- **Done when**: the behaviour is a decision, not a side effect of `all()`.

## Priority 2 — robustness and failure behaviour

### 5. Failure injection

- **Problem**: missing/corrupt templates, an unwritable `XDG_DATA_HOME`, and
  invalid YAML are untested. They likely surface as tracebacks or leave a
  partially written unit set.
- **Why not in #32**: asserting "clear error" first requires error handling in
  `write_systemd()` / config loading.
- **Tests**: make the templates directory read-only, point `XDG_DATA_HOME` at
  a file, write invalid YAML, and assert a non-zero exit with a message and no
  half-written units (write to a temp file and rename, or clean up).
- **Done when**: failures are user-visible and the unit set is either old or
  new, never mixed.

### 6. Command quoting and shell injection

- **Problem**: theme `command` values run through `os.system`, so paths with
  spaces or quotes break and shell metacharacters execute.
- **Why not in #32**: this is a security question, not a harness gap.
- **Tests**: a command path containing a space, a single quote, and a `;`
  should still execute as intended once the call site moves to an argv list.
- **Done when**: commands are executed without a shell, and the test proves it.

### 7. Concurrent activations

- **Problem**: two `kshift theme` runs at once are the neighbourhood of the
  original race. Today there is no defined end state.
- **Why not in #32**: undefined expectations cannot be asserted.
- **Test**: start both runs against the same config and assert a single stable
  final theme and no duplicated log entries; then decide whether a lock file
  is needed.
- **Done when**: the expected outcome is documented and enforced.

### 8. Coverage reporting

- **Problem**: no measurement of which branches are exercised, especially in
  `write_systemd()`.
- **Test**: run `pytest --cov=kshift --cov-report=term-missing` in the build
  job (not a gate at first) and use it to find untested branches.
- **Done when**: coverage is visible on PRs and the backlog items above are
  chosen from the gaps rather than from guesswork.

## Priority 3 — suite economics

### 9. Share the shim writer

`tests/conftest.py` and `tests/integration/conftest.py` both write
`plasma-apply-*` shims (~20 duplicated lines). Extract one helper once the
layout settles.

### 10. Reduce mock/Tier 1 overlap

`tests/test_theme_recovery.py` and `tests/integration/test_cli_recovery.py`
assert some of the same wiring. Keep the fast unit tests for logic and leave
subprocess/log/unit rendering to Tier 1, so a failure points at one layer.

### 11. Mark and split slow tests

Tier 2 is ~35 s because the startup service is `OnStartupSec=5`. Add a `slow`
marker, keep it out of the default run, and let a separate job own it. Do not
make it required until it runs on a runner that can actually provide a user
manager (see #12).

### 12. Turn Tier 2 on

Register a self-hosted runner (a Plasma workstation is ideal), set the
repository variable `KSHIFT_SYSTEMD_RUNNER`, and let the nightly job run with
`KSHIFT_REQUIRE_INTEGRATION=1`. Today the job is correctly reported as
`skipping` because GitHub-hosted runners cannot start a private
`systemd --user`; enabling it is the last step to real nightly coverage.

## Adding an item

Copy the shape above: **problem**, **why not now**, **change**, **test**,
**done when**. If an item needs a production change, it does not belong in a
tests-only PR; link the PRs instead.
