#!/usr/bin/env python3
"""Offline staged-content and Git-history publication safety audit.

Run before a commit with ``python tools/check_publication_safety.py --staged``.
Run before an approved push with ``python tools/check_publication_safety.py
--range <verified-upstream>..<proposed-tip>``. Findings report locations and
categories, never the matched content. ``<...>`` placeholders are intentional.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    category: str
    count: int


# Narrow patterns for personal/local paths and high-confidence secret formats.
# Generic repository-relative paths and explicit <PLACEHOLDER> examples pass.
PATTERNS: tuple[tuple[str, re.Pattern[bytes]], ...] = tuple(
    (name, re.compile(pattern))
    for name, pattern in (
        ("mac-home", rb"(?<![A-Za-z0-9_])/(?:Users|home)/(?!(?:<|\[|example(?:/|\b)|user(?:/|\b)))[A-Za-z0-9._-]+(?:/[A-Za-z0-9._ @+,-]+)*"),
        ("mac-temp", rb"(?<![A-Za-z0-9_])/(?:private/)?tmp/(?!<)[A-Za-z0-9._-]+(?:/[A-Za-z0-9._ @+,-]+)*"),
        ("volume-path", rb"(?<![A-Za-z0-9_])/Volumes/(?!<)[A-Za-z0-9._-]+(?:/[A-Za-z0-9._ @+,-]+)*"),
        ("run-user-path", rb"(?<![A-Za-z0-9_])/run/user/[0-9]+(?:/[A-Za-z0-9._ @+,-]+)*"),
        ("windows-home", rb"(?i)(?:[A-Z]:\x5cUsers\x5c(?!<)[A-Za-z0-9._-]+(?:\x5c[^\x5c\r\n\"<>|?*]+)*|\x5c\x5c[^\x5c]+\x5cUsers\x5c(?!<)[A-Za-z0-9._-]+(?:\x5c[^\x5c\r\n\"<>|?*]+)*)"),
        ("local-file-url", rb"(?i)file:\x2f\x2f(?:\x2fUsers\x2f|\x2fhome\x2f|\x2fprivate\x2ftmp\x2f|\x2ftmp\x2f|[A-Z]:\\Users\\)[^\s\"<>]+"),
        ("aws-access-key", rb"\bAKIA[0-9A-Z]{16}\b"),
        ("github-token", rb"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
        ("gitlab-token", rb"\bglpat-[A-Za-z0-9_-]{20,}\b"),
        ("slack-token", rb"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
        ("private-key", rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        ("secret-assignment", rb"(?i)\b(?:api[_-]?key|client[_-]?secret|password|access[_-]?token)\s*[:=]\s*[\"']?(?!<|\{|\[|example\b|changeme\b|redacted\b)[A-Za-z0-9_./+=-]{16,}"),
    )
)

SENSITIVE_NAMES = (".env", ".pem", ".key", ".p12", ".pfx", ".sqlite", ".db")
MAX_REVIEWED_BLOB = 2_000_000


def _git(args: list[str], *, data: bytes | None = None, check: bool = True) -> bytes:
    result = subprocess.run(
        ["git", *args], input=data, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )
    if check and result.returncode:
        message = result.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(message or f"git command failed: {args[0]}")
    return result.stdout


def inspect_bytes(data: bytes) -> list[Finding]:
    found = []
    for category, pattern in PATTERNS:
        count = sum(1 for _ in pattern.finditer(data))
        if count:
            found.append(Finding(category, count))
    return found


def _relative_label(path: bytes) -> str:
    findings = inspect_bytes(path)
    if findings:
        return "<path name redacted>"
    return path.decode("utf-8", "replace")


def _sensitive_name_category(path: bytes) -> str | None:
    lower = path.lower().replace(b"\\", b"/")
    parts = lower.split(b"/")
    leaf = parts[-1]
    if leaf.endswith(tuple(item.encode() for item in SENSITIVE_NAMES)):
        return "sensitive-filename-review"
    if any(part in (b"credentials", b"secrets") for part in parts):
        return "sensitive-filename-review"
    if len(parts) > 1 and parts[0] == b"workspace" and leaf.endswith(b".json"):
        return "workspace-state-review"
    if any(part in (b"saved", b"sessions", b"checkpoints") for part in parts[:-1]) and not (
        b"tests" in parts and b"fixtures" in parts
    ) and leaf.endswith((b".json", b".bin", b".pickle", b".pkl")):
        return "saved-state-review"
    return None


def _print_findings(location: str, findings: list[Finding]) -> int:
    if not findings:
        return 0
    print("FINDING", location, " ".join(f"{item.category}={item.count}" for item in findings))
    return sum(item.count for item in findings)


def scan_staged() -> int:
    paths = _git(["diff", "--cached", "--no-renames", "--name-only", "-z"]).split(b"\0")
    paths = [path for path in paths if path]
    count = 0
    reviewed = 0
    for path in paths:
        reviewed += 1
        count += _print_findings(f"staged path {_relative_label(path)}", inspect_bytes(path))
        spec = b":" + path
        content = _git(["cat-file", "blob", spec.decode("utf-8", "surrogateescape")], check=False)
        if content:
            count += _print_findings(f"staged content {_relative_label(path)}", inspect_bytes(content))
            if len(content) > MAX_REVIEWED_BLOB:
                count += _print_findings(f"staged content {_relative_label(path)}", [Finding("large-opaque-review", 1)])
        name_category = _sensitive_name_category(path)
        if name_category:
            count += _print_findings(f"staged path {_relative_label(path)}", [Finding(name_category, 1)])
    print(f"staged-audit files={reviewed} findings={count} result={'FAIL' if count else 'PASS'}")
    return 1 if count else 0


def _read_object_batch(object_ids: list[str]):
    if not object_ids:
        return
    process = subprocess.Popen(["git", "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    assert process.stdin and process.stdout
    for object_id in object_ids:
        process.stdin.write(object_id.encode("ascii") + b"\n")
    process.stdin.close()
    for object_id in object_ids:
        header = process.stdout.readline().split()
        if len(header) != 3:
            raise RuntimeError("unable to read Git object batch")
        object_type, size = header[1], int(header[2])
        content = process.stdout.read(size)
        process.stdout.read(1)
        yield object_id, object_type, size, content
    if process.wait():
        raise RuntimeError("Git object batch failed")


def _scan_history(base: str, tip: str) -> int:
    base_oid = _git(["rev-parse", base]).decode().strip() if base else "<root>"
    tip_oid = _git(["rev-parse", tip]).decode().strip()
    revision_args = [tip, "^" + base] if base else [tip]
    commits = _git(["rev-list", "--reverse", "--topo-order", *revision_args]).decode().splitlines()
    findings = 0
    pathnames: set[bytes] = set()
    for commit in commits:
        raw = _git(["cat-file", "commit", commit])
        findings += _print_findings(f"commit {commit[:12]} metadata/message", inspect_bytes(raw))
        paths = _git(["diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "-m", "-z", commit]).split(b"\0")
        changed_paths = {path for path in paths if path}
        for path in changed_paths:
            pathnames.add(path)
            findings += _print_findings(f"commit {commit[:12]} path {_relative_label(path)}", inspect_bytes(path))
            # A newly changed path can point to a blob already reachable from
            # the reviewed base (for example, a copied historical file). Scan
            # the version introduced by every commit in the range, not only
            # objects that are globally new to the range.
            path_text = os.fsdecode(path)
            content = _git(["cat-file", "blob", f"{commit}:{path_text}"], check=False)
            if content:
                label = _relative_label(path)
                findings += _print_findings(
                    f"commit {commit[:12]} content {label}", inspect_bytes(content)
                )
                if len(content) > MAX_REVIEWED_BLOB:
                    findings += _print_findings(
                        f"commit {commit[:12]} content {label}",
                        [Finding("large-opaque-review", 1)],
                    )
    object_rows = _git(["rev-list", "--objects", *revision_args]).splitlines()
    object_paths: dict[str, bytes] = {}
    for row in object_rows:
        parts = row.split(b" ", 1)
        object_paths.setdefault(parts[0].decode("ascii"), parts[1] if len(parts) == 2 else b"<object>")
    object_ids = list(object_paths)
    large_count = 0
    blob_count = 0
    for object_id, object_type, size, content in _read_object_batch(object_ids):
        if object_type != b"blob":
            continue
        blob_count += 1
        label = _relative_label(object_paths[object_id])
        findings += _print_findings(f"blob {object_id[:12]} {label}", inspect_bytes(content))
        if size > MAX_REVIEWED_BLOB:
            large_count += 1
            findings += _print_findings(f"blob {object_id[:12]} {label}", [Finding("large-opaque-review", 1)])
    suspicious = []
    for path in pathnames:
        category = _sensitive_name_category(path)
        if category:
            suspicious.append((path, category))
    for path, category in sorted(set(suspicious)):
        findings += _print_findings(f"changed path {_relative_label(path)}", [Finding(category, 1)])
    range_label = f"{base_oid[:12]}..{tip_oid[:12]}" if base else f"all..{tip_oid[:12]}"
    print(f"history-audit range={range_label} commits={len(commits)} blobs={blob_count} large-blobs={large_count} findings={findings} result={'FAIL' if findings else 'PASS'}")
    return 1 if findings else 0


def scan_history(spec: str) -> int:
    if spec.count("..") != 1:
        raise ValueError("--range must be exactly BASE..TIP")
    return _scan_history(*spec.split(".."))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--staged", action="store_true", help="audit staged paths and content only")
    group.add_argument("--range", metavar="BASE..TIP", help="audit all commits and objects newly reachable in this range")
    group.add_argument("--history", metavar="TIP", help="audit all commits and objects reachable from TIP")
    args = parser.parse_args(argv)
    try:
        if args.staged:
            return scan_staged()
        if args.range:
            return scan_history(args.range)
        return _scan_history("", args.history)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"publication-audit result=ERROR detail={type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
