"""Batch slug generator: turn lines of text into URL-safe slugs.

Reads lines from a file or stdin, emits one slug per line. Handles
accents (NFKD transliteration), lowercase, separator customization,
max length, dedup suffixing, and CI gates.

Exit codes: 0 ok | 1 I/O or CLI error | 2 gate failure
(--check, --require-change, --require-unchanged, --max-length, --require-unique).
"""

import argparse
import json
import re
import sys
import unicodedata
from typing import Any, Dict, List, Optional, Tuple


def slugify(
    text: str,
    separator: str = "-",
    max_length: Optional[int] = None,
    keep_case: bool = False,
) -> str:
    """Convert a single line of text to a URL-safe slug."""
    slug = unicodedata.normalize("NFKD", text)
    slug = slug.encode("ascii", "ignore").decode("ascii")
    if not keep_case:
        slug = slug.lower()
    # Replace any run of non-alphanumeric chars with separator
    slug = re.sub(r"[^a-zA-Z0-9]+", separator, slug)
    # Strip leading/trailing separators
    escaped = re.escape(separator)
    slug = re.sub(f"^{escaped}+|{escaped}+$", "", slug)
    # Collapse repeated separators
    slug = re.sub(f"{escaped}+", separator, slug)
    if max_length is not None and max_length > 0 and len(slug) > max_length:
        slug = slug[:max_length]
        # Don't end on a trailing separator after truncation
        slug = re.sub(f"{escaped}+$", "", slug)
    return slug


def dedup_slug(slug: str, used: set, separator: str) -> str:
    """Append -2, -3, ... if slug is already used."""
    if slug not in used:
        return slug
    counter = 2
    while f"{slug}{separator}{counter}" in used:
        counter += 1
    return f"{slug}{separator}{counter}"


def _read_lines(source: str, encoding: str = "utf-8") -> List[str]:
    if source == "-":
        raw = sys.stdin.read()
    else:
        with open(source, "r", encoding=encoding) as fh:
            raw = fh.read()
    return [line.rstrip("\r\n") for line in raw.splitlines()]


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="text-slug-batch",
        description="Batch slug generator: convert each line of text to a URL-safe slug.",
    )
    p.add_argument(
        "input",
        nargs="?",
        default="-",
        help="Input file (one title per line), or '-' for stdin (default).",
    )
    p.add_argument(
        "--separator",
        "-s",
        default="-",
        help="Separator character(s) used in slugs (default: '-').",
    )
    p.add_argument(
        "--max-length",
        type=int,
        default=None,
        metavar="N",
        help="Truncate slugs to N characters (word boundary tolerant).",
    )
    p.add_argument(
        "--keep-case",
        action="store_true",
        help="Preserve letter case instead of converting to lowercase.",
    )
    p.add_argument(
        "--no-dedup",
        action="store_true",
        help="Do not append -2/-3 suffixes for duplicate slugs.",
    )
    p.add_argument(
        "--skip-empty",
        action="store_true",
        help="Skip lines that produce an empty slug instead of emitting an empty line.",
    )
    p.add_argument(
        "--pairs",
        action="store_true",
        help="Emit 'original => slug' pairs instead of bare slugs.",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Emit a JSON report with mappings and stats.",
    )
    p.add_argument(
        "--check",
        action="store_true",
        help="Gate: exit 2 if any slug changed its input line (i.e. all lines must already be valid slugs).",
    )
    p.add_argument(
        "--require-change",
        action="store_true",
        help="Gate: exit 2 unless at least one line was changed by slugification.",
    )
    p.add_argument(
        "--require-unchanged",
        action="store_true",
        help="Gate: exit 2 if any line was changed by slugification.",
    )
    p.add_argument(
        "--require-unique",
        action="store_true",
        help="Gate: exit 2 if two lines produce the same slug.",
    )
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)

    try:
        lines = _read_lines(args.input)
    except OSError as exc:
        print(f"text-slug-batch: error reading input: {exc}", file=sys.stderr)
        return 1

    separator = args.separator
    if not separator:
        print("text-slug-batch: separator must not be empty", file=sys.stderr)
        return 1

    used: set = set()
    mappings: List[Dict[str, Any]] = []
    changed = 0
    duplicates = 0
    seen_slugs: set = set()

    for line_number, original in enumerate(lines, start=1):
        slug = slugify(
            original,
            separator=separator,
            max_length=args.max_length,
            keep_case=args.keep_case,
        )
        if not slug and args.skip_empty:
            continue
        is_dup = slug in seen_slugs
        if is_dup:
            duplicates += 1
        final_slug = slug
        if not args.no_dedup and slug:
            final_slug = dedup_slug(slug, used, separator)
        used.add(final_slug)
        seen_slugs.add(slug)
        if final_slug != original:
            changed += 1
        mappings.append({
            "line": line_number,
            "original": original,
            "slug": final_slug,
            "changed": final_slug != original,
            "duplicate": is_dup,
        })

    # ---- gates (exit 2) ----------------------------------------------------
    gate_failed = False
    if args.check and changed > 0:
        gate_failed = True
    if args.require_change and changed == 0:
        gate_failed = True
    if args.require_unchanged and changed > 0:
        gate_failed = True
    if args.require_unique and duplicates > 0:
        gate_failed = True

    # ---- output --------------------------------------------------------------
    if args.json:
        report = {
            "total": len(mappings),
            "changed": changed,
            "duplicates": duplicates,
            "mappings": mappings,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif args.pairs:
        for m in mappings:
            print(f"{m['original']} => {m['slug']}")
    else:
        for m in mappings:
            print(m["slug"])

    return 2 if gate_failed else 0


if __name__ == "__main__":
    sys.exit(main())
