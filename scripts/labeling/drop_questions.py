"""
drop_questions.py — remove pure question rows from dataset.csv.

A row is a "pure question" (not a take) if the text is primarily asking
rather than claiming, arguing, evaluating, or reacting. These have no
validity to measure and don't belong in the dataset.

Heuristics for "pure question":
  - Contains "?" AND word count < 80  (short question posts/comments)
  - Starts with a question word AND contains "?"  (regardless of length)
  - Does NOT contain strong claim/argument signals that override the question
"""

import csv
import re
from collections import Counter
from pathlib import Path

CSV_PATH = Path(__file__).parents[2] / "data" / "dataset.csv"
FIELDS   = ["id", "type", "post_title", "text", "author", "score", "url", "flair", "label"]

QUESTION_STARTERS = (
    "why ", "how ", "what ", "when ", "where ", "did ", "does ",
    "is ", "are ", "can ", "who ", "which ", "was ", "were ",
    "should ", "could ", "would ", "do ", "have ", "has ",
)

# If these appear, the text is making a claim/argument despite the "?"
# and should be kept
CLAIM_OVERRIDES = [
    "because", "therefore", "which means", "this is why", "the reason",
    "foreshadow", "parallel", "symbol", "represent", "theme",
    "i think that", "i argue", "my point is", "the point is",
    "not just", "deeper than", "actually means", "this shows",
    "in fact", "evidence", "proves", "demonstrates",
]


def is_pure_question(text: str) -> bool:
    t  = text.strip()
    tl = t.lower()
    wc = len(t.split())

    has_q     = "?" in t
    starts_q  = any(tl.startswith(s) for s in QUESTION_STARTERS)
    has_claim = any(s in tl for s in CLAIM_OVERRIDES)

    if not has_q:
        return False  # no question mark → not a question row

    # Has a claim signal → keep it even if it has a "?"
    if has_claim and wc > 60:
        return False

    # Short text with "?" → pure question
    if wc < 80:
        return True

    # Longer text that starts with a question word → still a question
    if starts_q:
        return True

    return False


def main() -> None:
    rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
    before = len(rows)

    kept    = [r for r in rows if not is_pure_question(r.get("text", ""))]
    dropped = [r for r in rows if     is_pure_question(r.get("text", ""))]

    print(f"Before: {before} rows")
    print(f"Dropped (pure questions): {len(dropped)}")
    print(f"Kept: {len(kept)}")

    # Show breakdown of what was dropped
    drop_by_label = Counter(r["label"] for r in dropped)
    print("\nDropped by label:")
    for lbl, cnt in sorted(drop_by_label.items()):
        print(f"  {lbl:<13} {cnt}")

    # Final distribution
    dist = Counter(r["label"] for r in kept)
    print("\nFinal distribution:")
    for lbl, cnt in sorted(dist.items()):
        pct = cnt / len(kept) * 100
        print(f"  {lbl:<13} {cnt:>3}  ({pct:.0f}%)")

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(kept)

    print(f"\nSaved {len(kept)} rows to dataset.csv")


if __name__ == "__main__":
    main()
