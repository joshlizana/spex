# Walking-skeleton dependencies

Research date: 2026-08-18

## Goal

Identify the minimum additional runtime dependencies needed for the M0 ingestion, DuckLake, and Streamlit path.

## Method

Review the official client and product documentation against the walking skeleton's long-lived processes and deliberately limited behavior. The Jetstream selection below is superseded by the later discovery of `atproto_jetstream` in `atproto==0.0.71`.

## Evidence

### Jetstream ingestion client

The original walking-skeleton selection used `websockets` for live traffic and HTTPX for archive traffic. `atproto==0.0.71` now includes `atproto_jetstream`, which provides Jetstream v2 archive planning and decoding, synchronous and asynchronous replay, cursor tracking, reconnect deduplication, and the replay-to-live transition.

One ingestion worker follows that combined lifecycle. Spex does not use `websockets` and HTTPX directly at the ingestion boundary or implement the replay plan itself.

Recommended M0 dependency: `atproto`, pinned to a release that contains `atproto_jetstream`.

### DuckLake

DuckLake support ships as a DuckDB core extension. DuckDB installs or autoloads the extension and attaches a DuckLake catalog with an `ATTACH 'ducklake:...'` statement. Spex already depends on the DuckDB Python package.

Recommended M0 Python dependency: none beyond `duckdb`. M0 still needs to install or autoload the `ducklake` extension and create its metadata and data paths.

### Streamlit

Streamlit runs an application script through `streamlit run` or the equivalent `python -m streamlit run`. The walking skeleton needs the Python package so the supervised dashboard process uses the same environment as Spex.

Recommended M0 dependency: `streamlit`.

### Dependencies outside M0

- Zstandard support belongs to the raw-retention benchmark and selected compressed JSON Lines design.
- Pool libraries remain outside orchestration and require profiling evidence inside a service.

## Conclusions

The recommended additions are:

- `atproto` for Jetstream v2 replay and live ingestion.
- `streamlit` for the analytical child process.
- `platformdirs` for M0 raw and DuckLake paths.

The existing `duckdb` package supplies access to the DuckLake extension. No separate DuckLake Python package is required.

The project uses the `spawn` multiprocessing context on every supported platform. M0 stores raw files and DuckLake data under the resolved Spex application-data directory. Development resets remove only that validated application-specific directory.

## Next steps

- Add confirmed dependencies and refresh `uv.lock` during implementation.
- Define the M0 subdirectories beneath the resolved Spex application-data directory.
- Define a guarded development reset procedure for the resolved Spex directory.

## Sources

- [`atproto` Python SDK](https://github.com/MarshalX/atproto)
- [DuckDB DuckLake extension](https://duckdb.org/docs/current/core_extensions/ducklake)
- [DuckLake introduction](https://ducklake.select/docs/stable/duckdb/introduction)
- [Streamlit command-line interface](https://docs.streamlit.io/develop/api-reference/cli)
- [Running a Streamlit application](https://docs.streamlit.io/develop/concepts/architecture/run-your-app)
