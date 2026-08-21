# Application filesystem layout

Status: accepted

## Stakeholders

| Role | Stakeholder |
| --- | --- |
| Owner and developer | Joshua |

## Problem statement

Spex needs stable logical locations for durable data, configuration, service state, runtime artifacts, logs, and disposable cache content on Linux and WSL.

## Goals

- Resolve every filesystem root through `platformdirs`.
- Keep durable data, configuration, state, runtime artifacts, logs, and cache content separate.
- Give M0 an explicit minimal directory layout.

## Non-goals

- Fix one literal path across operating systems.
- Define every filename or artifact schema.
- Store development benchmark results beneath a `platformdirs` root.

## Design

Spex creates `PlatformDirs("spex")` and uses its default per-user roots. Application-specific paths append to those resolved roots.

Configuration loading creates `user_config_path/config.json` with validated defaults when the file does not exist. Configuration updates replace the file atomically.

Application bootstrap resolves one validated configuration snapshot and creates the complete logical directory tree before the orchestrator starts its child processes.

The complete logical layout is:

```text
user_data_path/
├── raw/
│   ├── live/
│   └── backfill/
├── ducklake/
├── rejected/
└── credentials/

user_config_path/
└── config.json

user_state_path/
├── checkpoints/
└── services/

user_runtime_path/
├── locks/
└── ipc/

user_log_path/
└── spex.jsonl

user_cache_path/
```

The `ipc` name covers Unix-domain sockets and related runtime endpoint metadata. Windows named pipes do not require filesystem socket entries.

The M0 subset is:

```text
user_data_path/
├── raw/live/
├── raw/backfill/
└── ducklake/

user_runtime_path/
├── locks/
└── ipc/

user_config_path/config.json
```

Development resets resolve and validate the Spex application-data path before removing it. Benchmark results remain in the project-scoped, Git-ignored `benchmarks/` directory.

## API

The path-resolution interface remains an implementation detail. It returns `pathlib.Path` values derived from one `PlatformDirs("spex")` configuration.

## Dependencies

- `platformdirs`
- Python `pathlib`

## Testing

### Functional testing

Path creation and isolation require validation on Linux and WSL.

### Performance testing

Performance testing does not apply to path resolution.

### Scale testing

Scale testing does not apply to path resolution.
