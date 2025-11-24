#!/usr/bin/env python3
"""
Merge `data/processed/scholarships.json` with
`data/processed/attachments_parsed_texts.json`.

Produces `data/processed/scholarships_with_attachments.json` where each
scholarship dict has a new key `attachment_details` (list).

Matching is performed by normalizing both IDs to strings using
Unicode NFKC normalization and `casefold()` so numeric/string mixes
still match.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import tempfile
import unicodedata
from collections import defaultdict
from typing import Any, Dict, List


def normalize_key(x: object) -> str:
    if x is None:
        return ""
    s = str(x)
    return unicodedata.normalize("NFKC", s).casefold()


def atomic_write(path: str, data: object, ensure_ascii: bool = False) -> None:
    dirpath = os.path.dirname(path)
    os.makedirs(dirpath, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=dirpath, prefix=".tmp-", suffix=".json")
    try:
        with io.open(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=ensure_ascii)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def load_json(path: str) -> object:
    with io.open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def merge(scholarships_path: str, attachments_path: str, out_path: str, preview: int = 8) -> None:
    scholarships = load_json(scholarships_path)
    attachments = load_json(attachments_path)

    # Build mapping id -> [attachments]
    by_id: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for a in attachments:
        key = normalize_key(a.get("id") or a.get("ID"))
        by_id[key].append(a)

    attached_count = 0
    for s in scholarships:
        key = normalize_key(s.get("id") or s.get("ID"))
        items = by_id.get(key, [])
        s["attachment_details"] = items
        if items:
            attached_count += 1

    total_s = len(scholarships)
    total_a = len(attachments)

    atomic_write(out_path, scholarships, ensure_ascii=False)

    # Print a concise preview (ASCII-safe) to avoid Windows console encoding issues
    print(json.dumps({
        "scholarships_total": total_s,
        "attachments_total": total_a,
        "scholarships_with_attachments": attached_count,
    }, ensure_ascii=True))

    print("Preview (first {} scholarships):".format(preview))
    for s in scholarships[:preview]:
        sid = s.get("id") or s.get("ID")
        name = s.get("scholarship_name") or s.get("name") or ""
        count = len(s.get("attachment_details", []))
        print(json.dumps({"id": sid, "name": name, "attachments": count}, ensure_ascii=True))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--scholarships", default="data/processed/scholarships.json")
    p.add_argument("--attachments", default="data/processed/attachments_parsed_texts.json")
    p.add_argument("--out", default="data/processed/scholarships_with_attachments.json")
    p.add_argument("--preview", type=int, default=8)
    args = p.parse_args()

    if not os.path.exists(args.scholarships):
        raise SystemExit(f"Scholarships file not found: {args.scholarships}")
    if not os.path.exists(args.attachments):
        raise SystemExit(f"Attachments file not found: {args.attachments}")

    merge(args.scholarships, args.attachments, args.out, preview=args.preview)


if __name__ == "__main__":
    main()
