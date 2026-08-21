# Walking-skeleton dependencies

Research date: 2026-08-18

## Goal

Identify the minimum additional runtime dependencies needed for the M0 live, backfill, DuckLake, and Streamlit path.

## Method

Review the official client and product documentation against the walking skeleton's separate long-lived processes and deliberately limited behavior.

## Evidence

### Live WebSocket client

The `websockets` package provides synchronous and asyncio clients. The synchronous client supports context-managed connections, message iteration, bounded `recv()` waits, WebSocket ping and pong, connection-close exceptions, and direct receipt of UTF-8 JSON as bytes.

The live worker is already isolated in its own process. A synchronous client keeps its first implementation linear. A bounded receive timeout allows the worker to observe control requests without adding an asyncio loop. Production reconnection and checkpoint hardening remain later work.

Recommended M0 dependency: `websockets`.

### Backfill HTTP client

HTTPX provides synchronous and asynchronous clients, request headers, status handling, timeouts, connection pooling, and streamed byte or line iteration. Streaming avoids loading an archive response into memory and supports the authenticated HTTP boundary.

The backfill worker is also isolated in its own process, so the synchronous API is sufficient for M0.

Recommended M0 dependency: `httpx`.

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

- `websockets` for synchronous live ingestion.
- `httpx` for synchronous streamed backfill requests.
- `streamlit` for the analytical child process.
- `platformdirs` for M0 raw and DuckLake paths.

The existing `duckdb` package supplies access to the DuckLake extension. No separate DuckLake Python package is required.

The project uses the `spawn` multiprocessing context on every supported platform. M0 stores raw files and DuckLake data under the resolved Spex application-data directory. Development resets remove only that validated application-specific directory.

## Next steps

- Add confirmed dependencies and refresh `uv.lock` during implementation.
- Define the M0 subdirectories beneath the resolved Spex application-data directory.
- Define a guarded development reset procedure for the resolved Spex directory.

## Sources

- [`websockets` synchronous client](https://websockets.readthedocs.io/en/stable/reference/sync/client.html)
- [HTTPX quick start and streaming](https://www.python-httpx.org/quickstart/)
- [HTTPX API](https://www.python-httpx.org/api/)
- [DuckDB DuckLake extension](https://duckdb.org/docs/current/core_extensions/ducklake)
- [DuckLake introduction](https://ducklake.select/docs/stable/duckdb/introduction)
- [Streamlit command-line interface](https://docs.streamlit.io/develop/api-reference/cli)
- [Running a Streamlit application](https://docs.streamlit.io/develop/concepts/architecture/run-your-app)
