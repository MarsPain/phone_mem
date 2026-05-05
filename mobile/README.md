# Mobile Runtime Prototype

Stage 2 mirrors the completed Python reference Personal Memory Service as an app-internal TypeScript service boundary. This workspace is not a production React Native app yet; it defines contracts and module boundaries before selecting a mobile toolchain, SQLite adapter, UI shell, or model runtime.

## Boundary Map

- `memory_core`: canonical event, lifecycle, source, privacy, quality, and selector models.
- `governance`: permission grants, memory views, and audit records.
- `storage`: storage adapter contracts; the first implementation should be in-memory, with on-device SQLite added later.
- `retrieval`: governed local retrieval result contracts.
- `context`: runtime-neutral context bundle and budget contracts.
- `service`: facade contract mirroring the Python reference operations.

## Contract Source

The Python reference under `phone_mem/` remains the executable oracle for Stage 2. Shared fixtures live in `tests/fixtures/memory_service/` and define the cross-runtime behavior that TypeScript implementations must preserve, including lifecycle explanations and structured service error payloads.
