#!/usr/bin/env python3
"""Source-only structural gate for OpenRemaster dev-build README files."""
from __future__ import annotations

import argparse
import datetime
import pathlib
import re
import sys

HEADINGS = (
    "Launch instructions",
    "Movement / navigation",
    "Interaction / gameplay",
    "Menus / inventory / save-load",
    "Graphics / display / camera",
    "Text / language / subtitles",
    "Debug / diagnostics / QA",
    "Other shortcuts",
    "Known limitations and unavailable features",
    "Verification",
)
CONTROL_HEADINGS = HEADINGS[1:8]
FIELDS = (
    "Project", "Build ID", "Build date", "Platform", "Launcher",
    "Verification status", "Reviewed by", "Reviewed at",
    "Verification method", "Source/InputMap evidence",
    "Runtime test evidence",
)


def field(contents, name):
    match = re.search(
        r"^\*\*" + re.escape(name) + r":\*\*[ \t]*(.+)[ \t]*$",
        contents, flags=re.MULTILINE,
    )
    return match.group(1).strip() if match else ""


def section(contents, heading):
    match = re.search(
        r"^## " + re.escape(heading) + r"[ \t]*\r?\n(.*?)(?=^## |\Z)",
        contents, flags=re.MULTILINE | re.DOTALL,
    )
    return match.group(1).strip() if match else None


def has_mapping(section_text):
    rows = [
        line.strip() for line in section_text.splitlines()
        if line.strip().startswith("|")
    ]
    data_rows = [
        row for row in rows if not row.startswith("| Device")
        and not re.match(r"^\|\s*:?-{3,}", row)
        and row.count("|") >= 5
    ]
    return bool(data_rows)


def scan(build_dir, project, build_id):
    problems = []
    path = build_dir / "README.md"
    if not path.is_file():
        return [str(path) + " missing"]
    contents = path.read_text(encoding="utf-8-sig")
    if re.search(r"\[[A-Z][A-Z0-9_/-]*\]|\b(TODO|TBD|UNVERIFIED|DRAFT)\b", contents, flags=re.IGNORECASE):
        problems.append("README contains template placeholders or draft markers")
    for name in FIELDS:
        if not field(contents, name):
            problems.append("Missing field: " + name)
    if field(contents, "Project") != project:
        problems.append("Project does not match expected project")
    if field(contents, "Build ID") != build_id:
        problems.append("Build ID does not match expected build")
    if field(contents, "Verification status") != "VERIFIED":
        problems.append("Verification status must be VERIFIED")
    for name in ("Build date", "Reviewed at"):
        try:
            datetime.date.fromisoformat(field(contents, name))
        except ValueError:
            problems.append("Invalid ISO date in " + name)
    launcher = field(contents, "Launcher")
    if launcher:
        resolved_root = build_dir.resolve()
        target = (build_dir / launcher).resolve()
        if not target.is_relative_to(resolved_root):
            problems.append("Launcher must be inside the supplied build directory")
        elif not target.is_file():
            problems.append("Launcher is absent from the build package: " + launcher)
    for heading in HEADINGS:
        body = section(contents, heading)
        if body is None or not body.strip():
            problems.append("Empty or missing section: " + heading)
            continue
        if heading in CONTROL_HEADINGS and not has_mapping(body):
            negative = re.search(r"Not implemented in this build:\s*(.+)", body)
            if not negative or len(negative.group(1).strip()) < 20:
                problems.append(heading + ": provide mapped keys or an explicit absence reason")
            elif "Evidence:" not in body:
                problems.append(heading + ": absent feature must cite supporting evidence")
    if "Replace the placeholder table" in contents:
        problems.append("Template editing instructions remain; finish the README")
    if len(section(contents, "Launch instructions") or "") < 12:
        problems.append("Launch instructions too short")
    if field(contents, "Source/InputMap evidence").lower() in ("none", "not performed", "n/a"):
        problems.append("Source/InputMap evidence is required")
    if not field(contents, "Reviewed by").strip():
        problems.append("Missing reviewer")
    return problems


def main():
    parser = argparse.ArgumentParser(
        description="Fail closed when a project-specific dev-build README is missing or incomplete."
    )
    parser.add_argument("--build-dir", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--build-id", required=True)
    args = parser.parse_args()
    problems = scan(pathlib.Path(args.build_dir), args.project, args.build_id)
    for problem in problems:
        print("README_HOLD:", problem, file=sys.stderr)
    if problems:
        print("README_HOLD: " + str(len(problems)) + " issue(s).", file=sys.stderr)
        return 2
    print("README_GATE_PASS: completeness verified; functional accuracy requires reviewer evidence.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
