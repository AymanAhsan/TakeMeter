"""
auto_label.py — label unlabeled rows in dataset.csv using taxonomy heuristics.

Taxonomy (tiebreaker order: Analytical > Informational > Evaluative > Reactive):
  Analytical   — argues an interpretation/theory/claim with textual evidence
  Informational — seeks or supplies factual/lore/production information
  Evaluative   — asserts a verdict/ranking/preference without substantive argument
  Reactive     — pure emotion/hype/humor, no claim or question
"""

import csv
import re
from pathlib import Path

CSV_PATH = Path(__file__).parents[2] / "data" / "dataset.csv"
FIELDS   = ["id", "type", "post_title", "text", "author", "score", "url", "flair", "label"]

# ---------------------------------------------------------------------------
# Signal word lists (tuned to the taxonomy + existing label examples)
# ---------------------------------------------------------------------------

ANALYTICAL_STRONG = [
    "foreshadow", "parallel", "mirror", "symbol", "represent", "motif",
    "juxtapos", "subvert", "theme", "narrative arc", "literary",
    "recontextuali", "implies", "suggests that", "this is why",
    "the reason is", "what this means", "the point is that",
    "not just", "deeper than", "more than just", "breakdown",
    "the show is saying", "argues", "argument", "commentary on",
    "allegor", "metaphor", "contrast", "ironically", "paradox",
]
ANALYTICAL_SUPPORT = [
    "because", "therefore", "which means", "this shows", "evidence",
    "specifically", "chapter", "episode", "scene", "panel",
    "notice that", "look at", "compare", "whereas", "however",
    "on the other hand", "that said", "in fact",
]

INFO_QUESTION_STARTS = (
    "why", "how", "what", "when", "where", "did", "does",
    "is ", "are ", "can ", "explain", "help ", "who ",
    "which", "was ", "were ", "has ", "have ", "should ",
    "could ", "would ", "any ",
)
INFO_KEYWORDS = [
    "watch order", "first time watching", "just started watching",
    "just began watching", "confused about", "clarif", "source material",
    "where can i watch", "lore", "adaptation", "blu-ray", "crunchyroll",
    "funimation", "is it canon", "continuity", "spoil", "did they cut",
    "anime vs manga", "vs the manga", "production", "dubbed", "subbed",
    "what happens to", "what happened to", "who is ", "who was ",
    "how does the", "when does", "where does", "should i watch",
    "which version", "what episode", "what chapter",
    "i don't understand", "i dont understand", "please explain",
    "can someone explain", "can anyone explain", "watch first",
    "read the manga", "missing something", "did i miss",
]

# Questions that look like info but are actually asking for opinions/rankings
EVAL_QUESTION_SIGNALS = [
    "how would you", "how do you", "what do you think", "what do you prefer",
    "what is your", "which do you", "who do you", "which is your",
    "rank", "ranking", "best ", "worst ", "favorite", "favourite",
    "better", "worse", "do you prefer", "would you rather",
    "what's your", "whats your", "in your opinion",
    "unpopular opinion", "hot take", "change my mind",
    "who wins", "who would win", "fight", "vs ",
    "morally", "thoughts on", "opinion on", "what are your thoughts",
]

EVALUATIVE_STRONG = [
    "best", "worst", "overrated", "underrated", "peak", "goat",
    "masterpiece", "garbage", "trash", "terrible", "awful",
    "superior", "inferior", "greatest", "most underrated",
    "most overrated", "hot take", "unpopular opinion",
    "fight me", "change my mind", "the best", "the worst",
    "all time", "of all time", "imo", "in my opinion",
    "personally i think", "i believe", "i feel like",
    "i would say", "disagree", "agree", "rank", "ranking",
    "tier", "favorite", "favourite", "prefer", "better than",
    "worse than", "more than", "less than",
]

REACTIVE_STRONG = [
    "omg", "oh my god", "oh my gosh", "i'm crying", "im crying",
    "i am crying", "sobbing", "screaming", "bruh", "bro ",
    "sending me", "vocal stim", "rent free", "roman empire",
    "deadass", "no cap", "unironically", "lmao", "lol ", "lmfao",
    "💀", "😭", "❤️", "🥹", "😂", "🤣", "💀💀",
    "that's it", "thats it", "that's the post", "no thoughts",
    "i cannot", "i can't", "i cant", "living in my head",
    "just finished", "just watched", "just completed",
    "not okay", "not ok", "im not okay",
]

# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

def _count(text_lower: str, signals: list[str]) -> int:
    return sum(1 for s in signals if s in text_lower)


def classify(text: str, post_title: str = "") -> tuple[str, bool]:
    """
    Returns (label, flag_for_review).
    flag=True on genuinely uncertain boundary calls.
    """
    tl   = text.lower()
    wc   = len(text.split())
    combined = f"{post_title.lower()} {tl}"

    has_question   = "?" in text
    starts_q       = any(tl.lstrip().startswith(s) for s in INFO_QUESTION_STARTS)

    ana_strong  = _count(tl, ANALYTICAL_STRONG)
    ana_support = _count(tl, ANALYTICAL_SUPPORT)
    info_kw     = _count(combined, INFO_KEYWORDS)
    eval_q_kw   = _count(combined, EVAL_QUESTION_SIGNALS)
    eval_kw     = _count(combined, EVALUATIVE_STRONG)
    react_kw    = _count(tl, REACTIVE_STRONG)

    # --- Analytical gate ---
    # Long text + strong interpretive language + reasoning connectors
    ana_score = ana_strong * 2 + (ana_support if ana_support >= 2 else 0)
    is_analytical = ana_score >= 3 and wc >= 60

    # --- Informational gate ---
    # "?" alone is not enough — must also have factual-info keywords
    # OR be a genuine factual question (not an opinion/ranking question)
    is_genuine_fact_q = (has_question or starts_q) and info_kw >= 1
    is_eval_question  = eval_q_kw >= 1 and info_kw == 0
    is_info = is_genuine_fact_q and not is_eval_question
    # Also trigger on pure info supply (long factual answer, no opinion signals)
    if not is_info and info_kw >= 2 and eval_kw == 0 and eval_q_kw == 0:
        is_info = True

    # --- TIEBREAKER: Analytical > Informational > Evaluative > Reactive ---

    if is_analytical:
        # Could still be Informational if it's a detailed factual answer to a question
        if is_info and ana_strong == 0:
            return "Informational", False
        # Borderline Analytical/Evaluative: Analytical wins by rule
        flag = (is_info and has_question) or (eval_kw >= 3 and ana_strong < 2)
        return "Analytical", flag

    if is_info:
        # Detailed info answer (long, no question) vs pure question
        # Either way → Informational
        flag = (ana_support >= 2 and wc > 80)  # could be Analytical
        return "Informational", flag

    # --- Evaluative ---
    is_evaluative = eval_kw >= 2
    if is_evaluative:
        flag = (ana_support >= 2 and wc > 80)
        return "Evaluative", flag

    # --- Reactive ---
    # Short OR has reactive signals OR single evaluative word
    if react_kw >= 1 or wc < 25:
        return "Reactive", False

    # Single evaluative word → Evaluative
    if eval_kw == 1:
        return "Evaluative", False

    # Medium-length ambiguous text with no strong signal
    if wc < 50:
        return "Reactive", True
    if wc < 120:
        return "Evaluative", True

    # Long with moderate analytical support but not enough to trigger Analytical gate
    if ana_support >= 2:
        return "Analytical", True

    return "Evaluative", True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))

    # Clear labels for any unlabeled rows (NGE rows arrive with no label)
    # Keep existing labels for AoT, HxH, FMA rows untouched

    unlabeled = [r for r in rows if not r.get("label")]
    print(f"Labeling {len(unlabeled)} rows...\n")

    flagged: list[dict] = []
    labeled_count = 0

    for r in rows:
        if r.get("label"):
            continue

        label, flag = classify(r.get("text", ""), r.get("post_title", ""))
        r["label"] = label
        labeled_count += 1

        status = "REVIEW" if flag else "ok    "
        line = f"{status}  [{label:<13}]  {r['text'][:80]!r}"
        print(line.encode("cp1252", errors="replace").decode("cp1252"))

        if flag:
            flagged.append({"id": r["id"], "label": label, "text": r["text"][:200]})

    print(f"\nLabeled {labeled_count} rows.")
    print(f"Flagged for review: {len(flagged)}")

    # Write back
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print("Saved to dataset.csv")

    # Print flagged summary
    if flagged:
        print("\n--- FLAGGED FOR REVIEW ---")
        for item in flagged:
            line1 = f"  [{item['label']:<13}] id={item['id']}"
            line2 = f"    {item['text'][:120]!r}"
            print(line1.encode("cp1252", errors="replace").decode("cp1252"))
            print(line2.encode("cp1252", errors="replace").decode("cp1252"))
            print()

    # Distribution
    from collections import Counter
    all_rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
    dist = Counter(r["label"] for r in all_rows)
    print("Final label distribution:")
    for lbl, cnt in sorted(dist.items()):
        print(f"  {lbl:<13} {cnt:>3}  ({cnt/len(all_rows)*100:.0f}%)")


if __name__ == "__main__":
    main()
