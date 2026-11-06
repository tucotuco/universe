#!/usr/bin/env python3
"""Regenerate/check heading-derived table of contents inside ENCOUNTERS-TOC tags.

Usage:
    python tools/update_encounters_toc.py
    python tools/update_encounters_toc.py --check
    python tools/update_encounters_toc.py path/to/encounters-working-draft-adopted-r60.md

Target rendering: GitHub-flavored Markdown heading fragments, including duplicate
heading suffixes. For exact parity with third-party markdown renderers, use
GitHub or verify that the renderer implements compatible anchor normalization.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from pathlib import Path
import re
import sys
import unicodedata

BEGIN = '<!-- ENCOUNTERS-TOC:START -->'
END = '<!-- ENCOUNTERS-TOC:END -->'
DEFAULT = Path(__file__).resolve().parents[1] / 'encounters-working-draft-adopted-r60.md'


def plain_heading(s: str) -> str:
    s = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', s)  # inline links
    s = re.sub(r'<[^>]*>', '', s)
    s = s.replace('`', '').replace('*', '').replace('_', '')
    s = re.sub(r'\s+#+\s*$', '', s).strip()
    return s


def github_slug(text: str) -> str:
    # GitHub heading-anchor convention: lower-case, remove punctuation except
    # hyphens/underscores, turn spaces into hyphens. Preserve unicode letters.
    slug = plain_heading(text).lower()
    slug = ''.join(c for c in slug if c in '-_ ' or c.isalnum() or unicodedata.category(c) in ('Mn', 'Mc'))
    return slug.replace(' ', '-')


def extract_headings(doc: str):
    in_fence = False
    fence_char = None
    fence_width = 0
    headings = []
    for line in doc.splitlines():
        f = re.match(r'^\s{0,3}(`{3,}|~{3,})', line)
        if f:
            delim = f.group(1)
            if not in_fence:
                in_fence, fence_char, fence_width = True, delim[0], len(delim)
            elif delim[0] == fence_char and len(delim) >= fence_width:
                in_fence = False
            continue
        if in_fence:
            continue
        match = re.match(r'^(#{1,6})[ \t]+(.+?)[ \t]*$', line)
        if match:
            level, text = len(match.group(1)), plain_heading(match.group(2))
            if not text or text == 'Table of contents' or level == 1:
                continue
            headings.append((level, text))
    return headings


def build_toc(doc: str) -> str:
    seen = defaultdict(int)
    lines = []
    for level, name in extract_headings(doc):
        slug = github_slug(name)
        suffix = seen[slug]
        seen[slug] += 1
        if suffix:
            slug += '-' + str(suffix)
        # GitHub-style Markdown links: escape literal ] and add angle-free anchors.
        label = name.replace('\\', '\\\\').replace('[', '\\[').replace(']', '\\]')
        lines.append('  ' * (level - 2) + '- [' + label + '](#' + slug + ')')
    return '\n'.join(lines)


def rewrite(doc: str) -> str:
    if doc.count(BEGIN) != 1 or doc.count(END) != 1:
        raise ValueError('Exactly one pair of ENCOUNTERS-TOC markers is required')
    a = doc.index(BEGIN) + len(BEGIN)
    b = doc.index(END)
    if b < a:
        raise ValueError('TOC end marker precedes its start marker')
    message = '\n<!-- Auto-generated from headings; edit the headings, not the list. -->\n'
    return doc[:a] + message + build_toc(doc) + '\n' + doc[b:]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path, nargs='?', default=DEFAULT)
    parser.add_argument('--check', action='store_true', help='Exit nonzero if contents is stale')
    args = parser.parse_args()
    doc = args.path.read_text(encoding='utf-8')
    updated = rewrite(doc)
    if args.check:
        if doc != updated:
            print(f'TOC out of date: {args.path}', file=sys.stderr)
            return 1
        print(f'TOC current: {args.path}')
    elif doc != updated:
        args.path.write_text(updated, encoding='utf-8')
        print(f'TOC regenerated: {args.path}; {len(extract_headings(doc))} headings')
    else:
        print(f'TOC already current: {args.path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
