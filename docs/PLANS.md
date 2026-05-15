# Plans

## Lifecycle

- `active`: current execution plans.
- `completed`: accepted plans with completion date.
- `tech-debt`: known deferred work.

## Active

_None._

## Completed

- [Mock Phone Tool Environment](exec-plans/completed/2026-05-14-mock-phone-tool-environment.md): completed 2026-05-15. Added deterministic Python mock Contacts, Calendar, and Messaging tools; combined runtime provider; Web Lab phone state inspector; SQLite persistence; and capture-worthy observation policy before Stage 2 mobile integration.

- [Documentation bootstrap](exec-plans/completed/2026-05-01-docs-bootstrap.md)
- [MVP local Personal Memory Service](exec-plans/completed/2026-05-04-mvp-local-memory-core.md): Stage 1 umbrella plan.
- [001 Package and event model](exec-plans/completed/2026-05-04-001-package-event-model.md)
- [002 Storage, audit, and governance](exec-plans/completed/2026-05-04-002-storage-audit-governance.md)
- [003 Retrieval and context assembly](exec-plans/completed/2026-05-04-003-retrieval-context-assembly.md)
- [004 Service API and lifecycle tests](exec-plans/completed/2026-05-04-004-service-api-lifecycle-tests.md)
- [Python reference maturation](exec-plans/completed/2026-05-05-python-reference-maturation.md): completed the reference usage, lifecycle, retrieval selector, file-backed SQLite, service error, explainability, and mobile contract fixture maturation track.
- [Python LLM Agent Runtime](exec-plans/completed/2026-05-05-python-llm-agent-runtime.md): completed the Stage 1.5 developer-machine runtime spike for real LLM chat over governed Python memory service APIs.
- [Python Web Lab](exec-plans/completed/2026-05-05-python-web-lab.md): completed the Stage 1.6 local developer Web Lab for real Agent chat, memory inspection, turn debugging, and file-backed SQLite exploration before mobile runtime work resumes.
- [Python Agentic Memory Lifecycle Maturation](exec-plans/completed/2026-05-09-python-agentic-memory-lifecycle-maturation.md): completed the Stage 1.7 Python-only maturation track for runtime memory protocol, governed session capture, hot capsules, hybrid retrieval, relation projections, maintenance workflows, quality metrics, and refreshed future-mobile fixtures before Stage 2 mobile work resumes.
- [Stage 1.7 Web Lab Alignment](exec-plans/completed/2026-05-10-stage-1-7-web-lab-alignment.md): aligned the local Python Web Lab with the completed Stage 1.7 Python oracle so runtime capture, hybrid retrieval explanations, hot capsules, relation context, maintenance reports, and quality metrics are inspectable before Stage 2 mobile work resumes.
- [Python Agent Session Multi-Turn Chat](exec-plans/completed/2026-05-10-python-agent-session-multi-turn-chat.md): added session-scoped multi-turn chat for the Python CLI demo and Web Lab while keeping durable memory behind governed service APIs.

## Tech Debt

- [Open architecture risks](exec-plans/tech-debt/open-architecture-risks.md)
- [Deferred Stage 2 mobile runtime prototype](exec-plans/tech-debt/deferred-stage2-mobile-runtime-prototype.md): parked until a separate Stage 2 execution plan is accepted.
- [OpenClaw-inspired memory optimizations](exec-plans/tech-debt/openclaw-inspired-memory-optimizations.md): original proposed track, completed through the Stage 1.7 Python Agentic Memory Lifecycle Maturation plan.
