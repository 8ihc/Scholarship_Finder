#!/usr/bin/env python3
"""Analyze `full_text_for_llm` lengths and estimate token counts.

Writes JSON to `data/analysis/full_text_length_analysis.json` with fields:
['ID', '獎學金名稱', '字元長度 (Char_Length)', '估算 Token 數 (Tokens_Estimate)']

Heuristic for token estimate:
- If >50% characters are CJK (Chinese/Japanese/Korean) assume ~1 token per character.
- Otherwise assume ~1 token per 4 characters (rough English heuristic).

This script uses atomic writes when saving the output.
"""
import io
import json
import math
import os
import re
import tempfile


def estimate_tokens(char_len: int, text: str) -> int:
    """Estimate tokens using a conservative 1.5 chars-per-token heuristic.

    tokens_estimate = round(length / 1.5)
    """
    if char_len == 0:
        return 0
    return int(round(char_len / 1.5))


def atomic_write(path: str, data: str, encoding: str = "utf-8"):
    dirpath = os.path.dirname(path)
    os.makedirs(dirpath, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=dirpath, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def main():
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    # Use absolute paths so the script works from any CWD
    input_path = os.path.join(base, "data", "processed", "scholarships_with_full_text_for_llm.json")
    output_path = os.path.join(base, "data", "analysis", "full_text_length_analysis.json")

    if not os.path.exists(input_path):
        print(f"ERROR: input file not found: {input_path}")
        raise SystemExit(1)

    with io.open(input_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    results = []
    total_tokens = 0
    max_len = 0
    max_id = None

    for rec in records:
        rec_id = rec.get("id")
        name = rec.get("scholarship_name") or rec.get("scholarship") or ""
        full_text = rec.get("full_text_for_llm") or ""
        char_len = len(full_text)
        tokens = estimate_tokens(char_len, full_text)
        total_tokens += tokens
        if char_len > max_len:
            max_len = char_len
            max_id = rec_id

        results.append({
            "ID": rec_id,
            "獎學金名稱": name,
            "字元長度 (Char_Length)": char_len,
            "估算 Token 數 (Tokens_Estimate)": tokens,
        })

    # Save results as JSON (UTF-8, keep unicode)
    dumped = json.dumps(results, ensure_ascii=False, indent=2)
    atomic_write(output_path, dumped, encoding="utf-8")

    # Also write CSV export (UTF-8 with BOM for Excel compatibility on Windows)
    try:
        import csv
        from io import StringIO

        csv_buffer = StringIO()
        writer = csv.writer(csv_buffer)
        header = ["ID", "獎學金名稱", "字元長度 (Char_Length)", "估算 Token 數 (Tokens_Estimate)"]
        writer.writerow(header)
        for r in results:
            writer.writerow([r["ID"], r["獎學金名稱"], r["字元長度 (Char_Length)"], r["估算 Token 數 (Tokens_Estimate)"]])

        csv_text = csv_buffer.getvalue()
        # Prepend UTF-8 BOM so Excel on Windows will open it with UTF-8 correctly
        bom = '\ufeff'
        atomic_write(os.path.join(base, "data", "analysis", "full_text_length_analysis.csv"), bom + csv_text, encoding="utf-8")
    except Exception as e:
        print(f"Warning: failed to write CSV export: {e}")

    print(f"Wrote {len(results)} records to {output_path}")
    print(f"Total estimated tokens: {total_tokens}")
    if max_id is not None:
        print(f"Max chars: {max_len} (ID={max_id})")


if __name__ == "__main__":
    main()
