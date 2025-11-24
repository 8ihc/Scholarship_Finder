#!/usr/bin/env python3
"""
Convert `data/raw/scholarships.csv` to JSON with English column names.
Outputs to `data/processed/scholarships.json`.

Usage:
    python scripts/convert_csv_to_json.py
"""
import csv
import json
import os
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(__file__))
CSV_PATH = os.path.join(ROOT, "data", "raw", "scholarships.csv")
OUT_PATH = os.path.join(ROOT, "data", "processed", "scholarships.json")

# Mapping from original CSV header -> new English key
COLUMN_MAP = {
    "ID": "id",
    "URL": "url",
    "類別名稱": "category",
    "開始日期": "start_date",
    "截止日期": "end_date",
    "獎學金名稱": "scholarship_name",
    "申請地點": "application_location",
    "附加檔案": "attachments",
    "獎學金金額": "amount",
    "獎學金名額": "quota",
    "申請資格": "eligibility",
    "繳交文件": "required_documents",
    # "爬取頁數": "pages_scraped",  # not needed in JSON output
    "爬取時間": "scraped_at",
}


def try_int(v):
    if v is None:
        return None
    v = v.strip()
    if v == "":
        return None
    try:
        return int(v)
    except Exception:
        return v


def main():
    if not os.path.exists(CSV_PATH):
        print(f"CSV not found: {CSV_PATH}")
        return

    rows = []
    # Use utf-8-sig to gracefully handle files that include a UTF-8 BOM
    with open(CSV_PATH, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            out = {}
            for orig_col, new_col in COLUMN_MAP.items():
                raw = r.get(orig_col, "")
                if raw is None:
                    raw = ""
                raw = raw.strip()
                # Convert / clean some known fields
                if new_col == "id":
                    out[new_col] = try_int(raw)
                elif new_col == "scraped_at":
                    out[new_col] = raw or None
                # (target_audience removed from output per user request)
                else:
                    out[new_col] = raw or None
            rows.append(out)

    # Write JSON
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH + ".tmp", "w", encoding="utf-8") as ofh:
        json.dump(rows, ofh, ensure_ascii=False, indent=2)
    os.replace(OUT_PATH + ".tmp", OUT_PATH)
    print(f"Wrote {len(rows)} records to {OUT_PATH}")


if __name__ == "__main__":
    main()
