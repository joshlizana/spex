# Walking-Skeleton Control-Plane Review

Review date: 2026-09-21

## Scope

- Revision: working tree at commit `31a2e4f`, plus this review's docstring, comment, and formatting corrections
- Files: `src/spex/` (all ten modules)
- Exclusions: documentation accuracy beyond the control-plane contracts in `docs/design/process-control.md`

## Summary

The control plane holds together: lock acquisition, spawn-time pipe transfer, the readiness handshake, EOF-driven shutdown, and concurrent join escalation all behave as `docs/design/process-control.md` specifies. Three defects are demonstrated rather than theoretical.

Findings 1 through 3 are the priority. Finding 1 breaks the documented "Hub loss closes Textual" contract inside a real window. Finding 2 leaks a thread past the pipe close and swallows the resulting `OSError`. Finding 3 makes every worker cycle run at 2.5 times its intended period and churns one thread per cycle.

Findings 4 through 6 are latent: the worker `state` path is dead code today, so its contract mismatches do not yet produce wrong behavior.

## Verification

- `python -m compileall -q src/spex` succeeds, and all ten modules import under the project environment.
- Pydantic 2.13.4 accepts both `model_validate(..., extra="forbid")` and `model_dump(exclude_computed_fields=True)`. `config.py` uses both correctly.
- `App.call_from_thread` raises `RuntimeError("App is not running")` before `App.run()` because `App._loop` is `None`. Textual 8.2.8 does not reset `_loop` to `None` after `run()` returns; it leaves a closed loop, so the same call from a non-app thread raises `RuntimeError("Event loop is closed")`.
- A probe mirroring `Hub._reporter`, `reporter.cancel()`, and `Hub.__aexit__`'s pipe close reproduces `OSError: handle is closed` in the reporter thread. The awaiting task is already cancelled, so the exception is discarded.
- Driving `IngestionService._run_cycle` directly measures 12 cycles in 3.005 seconds, or 0.250 seconds per cycle, against a 0.100-second sleep budget.
- `_spawn_service` performs one initial attempt and four retries with 1, 2, 4, and 8-second delays, matching the standard retry policy.
- `/run/user` is `drwxr-xr-x root:root`, so creating `/run/user/<uid>` requires root.
- Ruff 0.16.4 (`E,W,F,B,SIM,RUF`, preview) reports 26 findings. The project checks in no lint configuration.

## Findings

### [High] Hub loss goes unreported when the TUI event loop is absent

- Location: `src/spex/services/tui.py:85`
- Category: functionality
- Impact: The pipe monitor starts in `Spex.__enter__`, before `Spex.run()` calls `App.run()`. A Hub that dies in that window drives the monitor into `call_from_thread` while `App._loop` is `None`. The `RuntimeError` escapes the `except (EOFError, OSError)` clause and kills the monitor thread, which has already set `_shutdown = True`. Textual then starts and runs indefinitely against a dead Hub with no remaining path to learn of the loss. This contradicts `process-control.md`: "The TUI exits through Textual's thread-safe boundary on Hub EOF."
- Evidence: Textual 8.2.8 raises `RuntimeError("App is not running")` when `_loop is None`. After `run()` returns, `_loop` holds a closed loop, so a late EOF instead raises `RuntimeError("Event loop is closed")` and prints a thread traceback to a just-restored terminal.
- Discussion: The monitor needs to handle the app-not-running case. The required outcome is that Hub loss before the event loop exists still ends the session deterministically, and that Hub loss after Textual exits stays silent. Consider whether the monitor should start after Textual is running, or whether `Spex` should record the loss in a flag that the startup path checks.

### [High] The Hub telemetry reporter outlives its pipe

- Location: `src/spex/services/hub.py:187`, `src/spex/services/hub.py:198`, `src/spex/services/hub.py:138`
- Category: functionality
- Impact: `reporter.cancel()` cancels the awaiting task, not the thread `asyncio.to_thread` started. Nothing joins that thread, so `Hub.__aexit__` closes the pipe while the reporter sleeps. The reporter wakes, sends, and raises `OSError: handle is closed`. Because the task is already cancelled, the exception reaches no handler and no log. Shutdown-time telemetry loss is therefore invisible, and this is an IPC failure boundary the project guards deliberately.
- Evidence: A probe reproducing the exact sequence reports `OSError: handle is closed` from the reporter thread with `task.cancelled()` true. Two causes compound: cancellation does not stop the thread, and the post-sleep `send` at line 198 never rechecks `self._running`.
- Discussion: `ServiceProcess.run` already solves this correctly at `service.py:34-38` by setting `_shutdown`, joining both threads, and only then closing the pipe. The Hub needs the same ordering guarantee. The required outcome is that no send can follow the pipe close.

### [High] The per-cycle telemetry thread inflates every worker cycle to 250 milliseconds

- Location: `src/spex/services/ingest.py:36`, `src/spex/services/pipeline.py:34`
- Category: performance
- Impact: `_run_cycle` sleeps 0.1 seconds, sets `_cycle_stop`, then joins the snapshot thread. That thread observes `_cycle_stop` only after its own `time.sleep(0.25)` returns, so the join blocks a further 0.15 seconds. Each cycle costs 0.250 seconds instead of 0.100, and the scaffold creates and destroys one thread every cycle. The thread also serves no purpose within a cycle: it writes exactly one snapshot before sleeping past the cycle's end.
- Evidence: Driving `_run_cycle` directly measures 0.250 seconds per cycle across 12 cycles.
- Discussion: The snapshot is a two-field dict built from attributes the cycle already owns. The required outcome is that the cycle runs at its intended period and the snapshot stays current within the documented 250-millisecond staleness budget. Consider whether the per-cycle thread is needed at all, or whether one long-lived snapshot thread per service, started alongside the base reporter, fits the documented design better.

### [Medium] The Hub stores the worker's self-reported `running` verbatim

- Location: `src/spex/services/hub.py:214`
- Category: design
- Impact: `_handle_message` replaces the role's entire state payload with the worker's, including its `running` field. `process-control.md` assigns that field to the Hub: "the Hub derives authoritative running or unavailable state from process handles and sentinels." A worker that reports `running: True` shortly before exiting overwrites the Hub's authoritative `False` from the restart path at `hub.py:176`.
- Evidence: The restart path sets `running` to `False`, then `_handle_message` can overwrite the whole dict on the next pass.
- Discussion: Latent while finding 5 holds. The required outcome is that the Hub preserves the worker's role-specific fields such as `phase` while `running` always reflects the process handle.

### [Medium] No worker ever sends a `state` message

- Location: `src/spex/services/ingest.py:38`, `src/spex/services/service.py:55`
- Category: tests
- Impact: `_phase_change` has no caller, so `_phase` stays `"live"` for the process lifetime and the `phase != self._phase` comparison never fires. `Hub._current_state` therefore never changes except through the restart path, so the Hub's own change detection at `hub.py:197` also never fires. The entire `state` path from worker through Hub to TUI is unexercised.
- Evidence: `_phase_change` appears once in the source, at its definition.
- Discussion: Expected for the scaffold, and recorded here because it explains why findings 4 and 6 are latent. The required outcome is that the phase transition drives this path once ingestion is real, and that findings 4 and 6 are settled before it does.

### [Medium] `_phase` belongs to ingestion but lives on the base service

- Location: `src/spex/services/service.py:18`
- Category: design
- Impact: `ServiceProcess` gives every worker a `_phase`, and its `_reporter` sends `phase` in every `state` message. `process-control.md` states: "Ingestion state contains `running` and `phase`; pipeline state contains `running`." A pipeline phase change would emit a payload the documented contract does not allow, and the Hub would forward it unchanged.
- Evidence: `service.py:56-61` sends `phase` unconditionally; `hub.py:114` initializes pipeline state as `{"running": True}` alone.
- Discussion: The required outcome is that the base class carries only what every worker reports, and ingestion adds its phase. Consider whether the base reporter should send a subclass-supplied state payload rather than assembling one itself.

### [Medium] A corrupt configuration file is deleted but not replaced

- Location: `src/spex/config.py:79`
- Category: functionality
- Impact: The creation branch writes defaults to disk; the recovery branch only removes the bad file and returns an in-memory default. The session then runs with no configuration file, which the rest of the module treats as impossible. The next start recreates it, so the states converge, but any component reading the file during that session finds nothing.
- Evidence: `config.py:78-81` removes the file and assigns `ConfigSchema()` without a write, unlike `config.py:83-88`.
- Discussion: The required outcome is that both paths leave the same on-disk state. Consider whether recovery should also preserve the corrupt file for diagnosis.

### [Low] Runtime directory creation may fail for non-root users on WSL

- Location: `src/spex/bootstrap.py:9`
- Category: functionality
- Impact: `runtime_dir` resolves to `/run/user/<uid>/spex`. `/run/user` is root-owned and mode 0755, so creating `/run/user/<uid>` requires root. WSL images without systemd do not always pre-create it, and `bootstrap_spex` would then raise `PermissionError` before the TUI starts. Linux and WSL are the supported platforms.
- Evidence: `stat` reports `drwxr-xr-x root:root /run/user`. Verified as a permission fact; not reproduced as a non-root user, because this environment runs as root.
- Discussion: Worth confirming against a real non-root WSL setup before treating it as a defect. The required outcome, if it reproduces, is a deterministic startup error or a documented fallback rather than an unhandled `PermissionError`.

### [Low] Spawn failures discard the real exception

- Location: `src/spex/services/hub.py:242`
- Category: functionality
- Impact: The handler appends a freshly constructed `Exception` carrying a fixed string instead of the caught exception. After exhaustion, `hub.py:250-253` raises a message listing five identical strings and no cause. A launch failure that ends the application session therefore arrives with no diagnostic information, and launch exhaustion is a documented session-ending path.
- Evidence: `except BaseException:` binds no name; the appended object is unrelated to the failure.
- Discussion: The required outcome is that the raised error names what actually failed. Consider `raise ... from` to preserve the final cause.

### [Low] `except BaseException` around `process.start()` absorbs interrupts

- Location: `src/spex/services/hub.py:240`
- Category: functionality
- Impact: `KeyboardInterrupt` and `SystemExit` become retry attempts. During `Hub.__aenter__` the loop's signal handlers are not yet installed, so a `SIGINT` in that window raises `KeyboardInterrupt` in the main thread, gets absorbed, and the Hub sleeps and retries up to four more times.
- Evidence: `run()` installs handlers at `hub.py:147-156`, after `__aenter__` has already spawned every service.
- Discussion: The required outcome is that interrupts end startup rather than feeding the retry loop. `Exception` is the narrower catch that still covers spawn failures.

### [Low] The readiness payload duplicates the Hub's initial state

- Location: `src/spex/services/hub.py:56`
- Category: design
- Impact: `HubProcess._run_hub` builds the `ready` payload as a literal that restates `Hub._current_state` at `hub.py:109-118`. The two can drift, and `process-control.md` requires readiness to carry "the complete initial `services` state mapping."
- Evidence: Both literals list the same three roles with the same fields.
- Discussion: The required outcome is one source of truth for the initial mapping.

### [Low] Role names are hardcoded in three places

- Location: `src/spex/services/hub.py:94`, `src/spex/services/hub.py:109`
- Category: design
- Impact: `SERVICE_TYPES` at `hub.py:16` already names the roles, and both aggregate dictionaries restate them. Adding a role means editing three literals. `_current_telemetry` also omits `dashboard` while `_current_state` includes it, with nothing explaining the asymmetry.
- Evidence: Three separate role lists in one module.
- Discussion: The asymmetry is correct today, since the dashboard reports no metrics. The required outcome is that the reason is visible in the code rather than inferred.

### [Low] Unknown message types raise a context-free error and end the Hub

- Location: `src/spex/services/hub.py:216`
- Category: functionality
- Impact: `raise ValueError(f"{message.get('type')}")` produces a message containing only the unexpected type, with no role and no indication of what rejected it. The `ValueError` also escapes the `(EOFError, OSError)` handler in `run()` and ends the whole session, whereas `process-control.md` specifies that an invalid post-readiness message "closes the connection and marks the TUI degraded."
- Evidence: `hub.py:172` calls `_handle_message` inside a handler that catches only `EOFError` and `OSError`.
- Discussion: The required outcome is an error that identifies the role and the rejected type, and a failure scope matching the documented contract.

### [Low] The restart sequence is duplicated verbatim

- Location: `src/spex/services/hub.py:176`, `src/spex/services/hub.py:182`
- Category: complexity
- Impact: The sentinel branch and the pipe-error branch contain identical four-line replacement sequences. A change to replacement behavior needs both edits, and a partial edit produces two different restart paths.
- Evidence: Lines 173-178 and 179-184 match except for the triggering condition.
- Discussion: The required outcome is one replacement routine with two callers.

### [Low] Phase-change detection straddles the reporter's sleep

- Location: `src/spex/services/service.py:46`
- Category: complexity
- Impact: `_reporter` captures `_phase` at the top of the iteration and compares it after the sleep. Coverage is continuous across iterations, so the logic is correct, but the correctness depends on where the read sits relative to the sleep, which is easy to break during later edits.
- Evidence: `service.py:46` reads the phase; `service.py:55` compares it after `time.sleep(0.25)`.
- Discussion: `Hub._reporter` solves the same problem more directly with a `reported_state` variable updated after each send. The required outcome is that the comparison survives reordering.

### [Low] Throughput divides by a fixed ten-second window during warm-up

- Location: `src/spex/services/ingest.py:51`, `src/spex/services/pipeline.py:46`
- Category: functionality
- Impact: The rate divides the window's length by 10.0 regardless of how long the process has run, so the reported rate ramps up from zero over the first ten seconds rather than reflecting the real rate. A restarted worker under-reports for ten seconds after every replacement.
- Evidence: A probe recording 12 events across 3.0 seconds, an actual 4.0 per second, reports 1.2 per second.
- Discussion: Acceptable for a rolling average if intended. The required outcome is that the TUI does not present a warm-up artifact as a real throughput drop.

### [Low] `HubLock` loads the whole configuration to read one path

- Location: `src/spex/services/lock.py:15`
- Category: design
- Impact: The constructor builds a `SpexConfig`, which reads or creates `config.json` on disk. A lock object performs unrelated configuration I/O, and constructing one can create a file.
- Evidence: `lock.py:15-17` calls `SpexConfig().config.runtime_dir`.
- Discussion: The required outcome is that the lock receives the path it needs rather than discovering it.

### [Low] Computed path properties create directories on every read

- Location: `src/spex/config.py:16`
- Category: design
- Impact: Each of the six computed fields constructs `PlatformDirs(..., ensure_exists=True)`, so reading a property is a filesystem write. `model_copy(deep=True)` in the `config` property and `model_dump` in `update` therefore perform directory creation as a side effect of reading configuration. The six bodies are also identical except for the final attribute.
- Evidence: `config.py:16-56`; `SpexConfig.config` deep-copies on every access.
- Discussion: `bootstrap_spex` already owns directory creation. The required outcome is that reading a path stays free of side effects and that directory creation has one owner.

### [Low] The project checks in no lint configuration

- Location: `pyproject.toml`
- Category: style
- Impact: `.ruff_cache/` shows ruff runs locally, but no `[tool.ruff]` section or `ruff.toml` records the settings, so line length and rule selection are whatever each agent's invocation happens to use. Ruff 0.16.4 with `E,W,F,B,SIM,RUF` reports 26 findings, including three unused `message` variables, four `raise ... from` sites, and two `deque([])` calls.
- Evidence: `pyproject.toml` contains only `[project]`, `[project.scripts]`, and `[build-system]`.
- Discussion: The unused `message` assignments are deliberate reads that discard their result; a checked-in configuration makes that intent explicit rather than leaving a recurring lint hit. The required outcome is a recorded style policy.

## Coverage

- [x] Design
- [x] Functionality and edge cases
- [x] Complexity
- [ ] Tests
- [x] Naming
- [x] Comments
- [x] Style and consistency
- [x] Documentation
- [x] Security and privacy
- [x] Performance and concurrency

Tests remain uncovered because the project has no test suite.

## Corrections applied during review

These are documentation and formatting changes within the agent's ownership, not application behavior.

- `start_spex`, `Spex.run`, `ServiceProcess`, `ServiceProcess._reporter`, `HubProcess._run_hub`, `Hub._reporter`, and `HubLock.write_metadata` carry docstrings matching their current behavior.
- The scaffold pacing comment in `ingest.py` and `pipeline.py` sits above the `time.sleep` it describes, and reads identically in both services.
- `config.py` uses PEP 8 blank-line spacing around `SpexConfig` and its methods.

## Open questions

1. Does `bootstrap_spex` succeed on your WSL setup as a non-root user, and does `/run/user/<uid>` exist there?
2. Should the base `ServiceProcess` reporter assemble the state payload, or send a payload each subclass supplies?
3. Should an invalid worker message degrade one service, as `process-control.md` specifies for the TUI, or end the session as it does now?
4. Do you want a checked-in ruff configuration, and at what line length?
