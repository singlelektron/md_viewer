#!/usr/bin/env python3
"""Check this repository's documentation; stdlib only, no writes or network."""

from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "README.md",
    "AGENTS.md",
    "THIRD_PARTY_NOTICES.md",
    "docs/PRODUCT.md",
    "docs/OWNER_GUIDE.md",
    "docs/TECHNOLOGY_OPTIONS.md",
    ".github/pull_request_template.md",
)
# Intentionally scoped to simple inline links used by these documents.
LINK = re.compile(r"\[[^\]\n]+\]\(([^\s)]+)\)")


def main():
    errors = []
    for relative in REQUIRED:
        path = ROOT / relative
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            errors.append(f"{relative}: required document missing or empty")

    paths = sorted(set(ROOT.glob("*.md")) | set((ROOT / "docs").rglob("*.md"))
                   | set((ROOT / ".github").rglob("*.md")))
    link_count = 0
    for path in paths:
        relative = path.relative_to(ROOT)
        text = path.read_text(encoding="utf-8")
        if not text.endswith("\n"):
            errors.append(f"{relative}: missing final newline")
        in_fence = False
        for number, line in enumerate(text.splitlines(), 1):
            if line.rstrip() != line:
                errors.append(f"{relative}:{number}: trailing whitespace")
            if line.lstrip().startswith(("```", "~~~")):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for destination in LINK.findall(line):
                parsed = urlsplit(destination)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                link_count += 1
                target = (path.parent / unquote(parsed.path)).resolve()
                if not target.is_relative_to(ROOT) or not target.is_file():
                    errors.append(f"{relative}:{number}: missing/outside local file: {destination}")

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Documentation checks passed: {len(paths)} files, {link_count} local file links.")
    print("External URLs, anchors, and application behavior are not checked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
