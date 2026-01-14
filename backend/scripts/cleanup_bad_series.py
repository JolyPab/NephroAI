"""Cleanup script for bad series names in lab_results."""

from __future__ import annotations

import argparse
from collections import Counter
import re
from typing import Iterable

from backend.analyte_utils import normalize_analyte_name
from backend.database import SessionLocal, LabResult


UNIT_ONLY_RE = re.compile(
    r"^(?:"
    r"%|"
    r"MG/DL|MG/L|G/DL|"
    r"MMOL/L|UMOL/L|"
    r"NG/ML|UG/ML|PG/ML|"
    r"U/L|UI/L|MUI/L|MEQ/L|"
    r"MMHG|"
    r"ML/MIN(?:/1\.73M2)?|"
    r"/UL|UL|"
    r"X10\^?\d+/UL|10\^?\d+/UL"
    r")$"
)

UNIT_PREFIX_RE = re.compile(r"^(?:/|X10\^?\d+/UL|10\^?\d+/UL)")


def _has_letters(text: str) -> bool:
    return bool(re.search(r"[A-Z]", text))


def is_bad_series_name(name: str) -> bool:
    normalized = normalize_analyte_name(name)
    if not normalized:
        return True

    if not _has_letters(normalized):
        return True

    if len(normalized) <= 2:
        return True

    first_token = normalized.split()[0]
    if UNIT_ONLY_RE.match(first_token):
        return True

    if UNIT_PREFIX_RE.match(first_token):
        return True

    return False


def _chunked(values: Iterable[int], size: int) -> Iterable[list[int]]:
    chunk: list[int] = []
    for value in values:
        chunk.append(value)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup bad series names.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview how many rows would be deleted.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of top names to display.",
    )
    args = parser.parse_args()

    session = SessionLocal()
    try:
        rows = session.query(LabResult.id, LabResult.analyte_name).all()
        bad_rows = []
        name_counts = Counter()

        for row_id, name in rows:
            if is_bad_series_name(name or ""):
                bad_rows.append(row_id)
                norm_name = normalize_analyte_name(name) or "<EMPTY>"
                name_counts[norm_name] += 1

        total_bad = len(bad_rows)
        print(f"[CLEANUP] bad_series_count={total_bad} unique_names={len(name_counts)}")
        for name, count in name_counts.most_common(args.limit):
            print(f"{count}\t{name}")

        if args.dry_run:
            return 0

        deleted = 0
        for chunk in _chunked(bad_rows, 500):
            deleted += (
                session.query(LabResult)
                .filter(LabResult.id.in_(chunk))
                .delete(synchronize_session=False)
            )
        session.commit()
        print(f"[CLEANUP] deleted={deleted}")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
