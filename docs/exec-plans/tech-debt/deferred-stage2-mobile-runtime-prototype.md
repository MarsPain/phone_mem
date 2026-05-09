# Stage 2 Mobile Runtime Prototype

Status: deferred
Type: umbrella
Deferred: 2026-05-04

This plan is intentionally deferred until Stage 1.7 Python Agentic Memory Lifecycle Maturation stabilizes and a separate Stage 2 execution plan is accepted. No TypeScript boundary files are retained during Stage 1.7; the mobile workspace should be recreated from the refreshed Python oracle when Stage 2 restarts.

## Goal

Create the first mobile-runtime prototype plan that mirrors the post-Stage 1.7 Python Personal Memory Service boundary in a React Native and TypeScript app-internal local service.

## Scope

- Recreate a `mobile/` workspace with TypeScript source boundaries that match the stabilized Python reference domains.
- Define TypeScript event, permission, audit, retrieval, context, and service contracts aligned with post-Stage 1.7 Python reference behavior.
- Add shared JSON fixtures under `tests/fixtures/` for Python-to-TypeScript contract parity.
- Add a mobile storage adapter interface first, then an on-device SQLite adapter in a later Stage 2 subplan.
- Add contract tests for record, search, explain, correct, delete, grant, revoke, audit, and build-context behavior.
- Keep model runtime adapters, cloud sync, private compute, passive sensing, and third-party SDK packaging out of this stage.

## Design Inputs

- [Backend And Runtime Strategy](../../BACKEND.md)
- [Roadmap](../../ROADMAP.md)
- [Python Reference MVP](../completed/2026-05-04-mvp-local-memory-core.md)
- [Memory SDK Product Spec](../../product-specs/memory-sdk.md)
- [Personal Memory Service](../../design-docs/personal-memory-service.md)
- [Governance, Permissions, And Audit](../../design-docs/governance-permissions-audit.md)
- [Retrieval And Context Assembly](../../design-docs/retrieval-and-context-assembly.md)

## Out Of Scope

- Production iOS or Android background services.
- Always-on voice, camera, visual, or sensor ingestion.
- LLM provider integration or prompt execution.
- Vector databases, embedding services, graph databases, cloud sync, or private-compute integration.
- App Store packaging, native permissions UX, or third-party SDK distribution.

## Steps

- [x] Remove stale `mobile/README.md` and TypeScript boundary files from the pre-Stage 1.7 mobile workspace.
- [x] Add shared contract fixtures under `tests/fixtures/memory_service/` for canonical event JSON, permission grants, search results, context bundles, deletion tombstones, audit records, lifecycle explanations, and service errors.
- [x] Add a Python fixture validation test that proves current reference service output can generate or consume the shared fixtures.
5. Recreate `mobile/README.md`, `mobile/memory_core/`, `mobile/governance/`, `mobile/storage/`, `mobile/retrieval/`, `mobile/context/`, and `mobile/service/` only after Stage 1.7 stabilizes.
6. Add TypeScript project metadata only after selecting the minimal toolchain for tests and formatting.
7. Implement TypeScript value models and contract tests before storage or UI work.
8. Implement an in-memory TypeScript service adapter that passes the shared fixture contract tests.
9. Add a SQLite adapter subplan after the TypeScript service contract is stable.
10. Update [../../BACKEND.md](../../BACKEND.md), [../../ROADMAP.md](../../ROADMAP.md), and [../../PLANS.md](../../PLANS.md) when each Stage 2 subplan is accepted.

## Implementation Notes

- No TypeScript boundary files are retained during Stage 1.7. No npm, React Native, SQLite, or TypeScript test toolchain has been introduced.
- `tests/fixtures/memory_service/` contains future-mobile contract fixtures generated from the reference `PersonalMemoryService`, including lifecycle explanation and structured error payloads added after the Python API stabilized.
- `tests/test_stage2_mobile_contract_fixtures.py` validates that stale mobile boundary files are absent and keeps the fixture JSON aligned with deterministic Python reference output.

## Validation

- `uv run python scripts/validate_docs.py`
- `uv run python -m unittest discover -s tests`
- TypeScript validation command to be added in the first Stage 2 implementation subplan after the post-Stage 1.7 toolchain is selected.

## Acceptance

- Stage 2 has a documented restart point and no stale mobile workspace boundary from the pre-Stage 1.7 Python oracle.
- Shared fixtures define the future Python-to-TypeScript contract for memory service behavior.
- No mobile code path bypasses service-level permissions, audit, lifecycle, retrieval, or context assembly boundaries.
- The first TypeScript implementation target is local and deterministic before SQLite, React Native UI, or model runtime integration.
- Standard Python validation commands pass while Stage 2 planning docs remain deferred.
