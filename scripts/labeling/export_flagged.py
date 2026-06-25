"""
export_flagged.py — re-run classify() on FMA + NGE rows and write
all uncertain calls to review.csv for manual correction.

Columns: id, current_label, type, post_title, text, url
"""

import csv
from pathlib import Path
from auto_label import classify

CSV_PATH    = Path(__file__).parents[2] / "data" / "dataset.csv"
REVIEW_PATH = Path(__file__).parents[2] / "data" / "review.csv"
REVIEW_FIELDS = ["id", "current_label", "type", "post_title", "text", "url"]
NEW_SUBREDDITS = ("FullmetalAlchemist", "NeonGenesisEvangelion")

rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))

flagged = []
for r in rows:
    if not any(s in r.get("url", "") for s in NEW_SUBREDDITS):
        continue
    _, flag = classify(r.get("text", ""), r.get("post_title", ""))
    if flag:
        flagged.append({
            "id":            r["id"],
            "current_label": r["label"],
            "type":          r["type"],
            "post_title":    r.get("post_title", ""),
            "text":          r.get("text", ""),
            "url":           r.get("url", ""),
        })

with open(REVIEW_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=REVIEW_FIELDS)
    writer.writeheader()
    writer.writerows(flagged)

print(f"{len(flagged)} flagged rows written to review.csv")
