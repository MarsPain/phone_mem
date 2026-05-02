from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PATHS = [
    "README.md",
    "AGENTS.md",
    "ARCHITECTURE.md",
    "docs/README.md",
    "docs/DESIGN.md",
    "docs/DATA.md",
    "docs/SECURITY.md",
    "docs/BACKEND.md",
    "docs/PLANS.md",
    "docs/PRODUCT_SENSE.md",
    "docs/ROADMAP.md",
    "docs/design-docs",
    "docs/exec-plans/active",
    "docs/exec-plans/completed",
    "docs/exec-plans/tech-debt",
    "docs/generated",
    "docs/product-specs",
    "docs/references",
]

REQUIRED_AGENT_LINKS = [
    "docs/README.md",
    "docs/DESIGN.md",
    "docs/DATA.md",
    "docs/SECURITY.md",
    "ARCHITECTURE.md",
]

REQUIRED_ARCH_LINKS = [
    "docs/DESIGN.md",
    "docs/design-docs/smartphone-agent-memory.md",
    "docs/design-docs/personal-memory-service.md",
    "docs/design-docs/memory-lifecycle-and-data-flow.md",
    "docs/design-docs/retrieval-and-context-assembly.md",
    "docs/design-docs/governance-permissions-audit.md",
    "docs/DATA.md",
    "docs/SECURITY.md",
]

LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
ACTIVE_PLAN_REQUIRED_HEADINGS = [
    "## Goal",
    "## Scope",
    "## Steps",
    "## Validation",
    "## Acceptance",
]


def strip_fenced_code(text: str) -> str:
    return re.sub(r"```.*?```", "", text, flags=re.DOTALL)


def markdown_files() -> list[Path]:
    return sorted(ROOT.rglob("*.md"))


def normalize_link_target(raw: str) -> str | None:
    target = raw.strip()
    if not target or target.startswith("#"):
        return None
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
        return None
    target = target.split("#", 1)[0]
    target = target.split("?", 1)[0]
    return target or None


def validate_links(errors: list[str]) -> None:
    for path in markdown_files():
        text = strip_fenced_code(path.read_text(encoding="utf-8"))
        for raw_target in LINK_RE.findall(text):
            target = normalize_link_target(raw_target)
            if target is None:
                continue
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                errors.append(f"{path.relative_to(ROOT)} links outside repository: {raw_target}")
                continue
            if not resolved.exists():
                errors.append(f"{path.relative_to(ROOT)} has broken link: {raw_target}")


def validate_required_paths(errors: list[str]) -> None:
    for rel in REQUIRED_PATHS:
        if not (ROOT / rel).exists():
            errors.append(f"Missing required path: {rel}")


def validate_root_maps(errors: list[str]) -> None:
    agents = ROOT / "AGENTS.md"
    if agents.exists():
        lines = agents.read_text(encoding="utf-8").splitlines()
        if len(lines) > 140:
            errors.append(f"AGENTS.md is too long: {len(lines)} lines")
        text = agents.read_text(encoding="utf-8")
        for rel in REQUIRED_AGENT_LINKS:
            if rel not in text:
                errors.append(f"AGENTS.md must link to {rel}")

    arch = ROOT / "ARCHITECTURE.md"
    if arch.exists():
        text = arch.read_text(encoding="utf-8")
        for rel in REQUIRED_ARCH_LINKS:
            if rel not in text:
                errors.append(f"ARCHITECTURE.md must link to {rel}")


def validate_plan_buckets(errors: list[str]) -> None:
    for bucket in ["active", "completed", "tech-debt"]:
        bucket_path = ROOT / "docs" / "exec-plans" / bucket
        plans = list(bucket_path.glob("*.md")) if bucket_path.exists() else []
        if not plans:
            errors.append(f"Plan bucket has no plans: docs/exec-plans/{bucket}")


def validate_active_plans(errors: list[str]) -> None:
    active_path = ROOT / "docs" / "exec-plans" / "active"
    for plan in sorted(active_path.glob("*.md")):
        text = plan.read_text(encoding="utf-8")
        rel = plan.relative_to(ROOT)
        if "Status: active" not in text:
            errors.append(f"Active plan is missing 'Status: active': {rel}")
        for heading in ACTIVE_PLAN_REQUIRED_HEADINGS:
            if heading not in text:
                errors.append(f"Active plan {rel} is missing required heading: {heading}")


def validate_docs_index_coverage(errors: list[str]) -> None:
    index_files = [
        ROOT / "README.md",
        ROOT / "AGENTS.md",
        ROOT / "ARCHITECTURE.md",
        ROOT / "docs" / "README.md",
        ROOT / "docs" / "PLANS.md",
    ]
    linked_text = "\n".join(
        path.read_text(encoding="utf-8") for path in index_files if path.exists()
    )
    for doc in markdown_files():
        rel = doc.relative_to(ROOT).as_posix()
        if rel.startswith("docs/exec-plans/"):
            continue
        if rel in {"README.md", "AGENTS.md", "ARCHITECTURE.md", "docs/README.md"}:
            continue
        if rel not in linked_text and doc.name not in linked_text:
            errors.append(f"Documentation page is not reachable from root/docs indexes: {rel}")


def main() -> int:
    errors: list[str] = []
    validate_required_paths(errors)
    validate_root_maps(errors)
    validate_plan_buckets(errors)
    validate_active_plans(errors)
    validate_links(errors)
    validate_docs_index_coverage(errors)

    if errors:
        print("Documentation validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Documentation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
