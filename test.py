"""
TakeMeter — boundary-case test suite + Groq classifier boilerplate.

Labels:
  ANALYTICAL   - argues a claim with text evidence; reasoning is the point
  EVALUATIVE   - asserts a verdict; reasons (if any) prop up the conclusion
  INFORMATIONAL - seeks or supplies factual/lore/production information
  REACTIVE     - expresses emotion, hype, or humor; no claim or question
"""

import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

# ---------------------------------------------------------------------------
# Boundary posts — the hard cases that stress-test label definitions
# ---------------------------------------------------------------------------

BOUNDARY_POSTS = [
    {
        "id": "B01",
        "collision": "ANALYTICAL vs EVALUATIVE",
        "text": (
            "The Levi vs. Beast Titan fight is the best in the series. "
            "The spinning ODM sequence, the music cue, the complete silence "
            "before impact — every craft decision lands. Nothing else in AoT "
            "is paced this well."
        ),
        "expected": "EVALUATIVE",
        "note": (
            "Lists reasons, but the verdict is the headline and the reasons "
            "prop it up. No standalone argument survives removing the conclusion."
        ),
    },
    {
        "id": "B02",
        "collision": "ANALYTICAL vs EVALUATIVE",
        "text": (
            "People say the ending is bad writing, but that reading misses the "
            "point entirely. Eren's choice *has* to feel hollow — a genocide "
            "that saves 80% of humanity is still a genocide. The emptiness IS "
            "the theme. Isayama didn't fumble, he stuck the landing in the only "
            "way that was thematically honest."
        ),
        "expected": "ANALYTICAL",
        "note": (
            "The reasoning is the point. Remove the conclusion and a full "
            "interpretive argument about intentionality remains."
        ),
    },
    {
        "id": "B03",
        "collision": "INFORMATIONAL vs ANALYTICAL",
        "text": "Why did Eren turn evil? I genuinely don't understand his motivation.",
        "expected": "INFORMATIONAL",
        "note": (
            "Phrased as a genuine question, not a rhetorical setup. "
            "Even though the answer requires interpretation, the post is "
            "seeking information, not making a claim."
        ),
    },
    {
        "id": "B04",
        "collision": "INFORMATIONAL vs ANALYTICAL",
        "text": (
            "Why does everyone act like Eren 'went evil'? He never changed — "
            "the show told you exactly who he was in episode 1. "
            "The audience just didn't want to read it."
        ),
        "expected": "ANALYTICAL",
        "note": (
            "Rhetorical 'why' baiting a debate. A claim is embedded: "
            "Eren's character was always consistent and the audience misread it."
        ),
    },
    {
        "id": "B05",
        "collision": "REACTIVE vs EVALUATIVE",
        "text": (
            "This show ruined every other anime for me. "
            "Nothing hits the same. I've tried, it just doesn't."
        ),
        "expected": "REACTIVE",
        "note": (
            "'Nothing hits the same' is a feeling, not a falsifiable claim. "
            "Remove the emotion and no debatable proposition remains."
        ),
    },
    {
        "id": "B06",
        "collision": "REACTIVE vs EVALUATIVE",
        "text": (
            "AoT is objectively the best long-form narrative in anime. "
            "The thematic coherence from episode 1 to the finale is unmatched. "
            "I will die on this hill."
        ),
        "expected": "EVALUATIVE",
        "note": (
            "'Objectively best' and 'unmatched' are comparative judgments "
            "a reasonable person could dispute. The claim survives stripping "
            "the emotional framing."
        ),
    },
    {
        "id": "B07",
        "collision": "ANALYTICAL vs EVALUATIVE",
        "text": (
            "The final season's shift to MAPPA was the right call. "
            "WIT could not have animated the Rumbling at that scale — "
            "the crowd simulations and environmental destruction in EP 87 alone "
            "justify the switch."
        ),
        "expected": "EVALUATIVE",
        "note": (
            "Has a supporting reason, but it's a single production fact "
            "propping up a verdict. The post isn't building an interpretive "
            "argument; it's justifying a preference."
        ),
    },
    {
        "id": "B08",
        "collision": "INFORMATIONAL vs EVALUATIVE",
        "text": (
            "Is the manga ending actually different from the anime? "
            "I heard Isayama revised it — which version is considered canon?"
        ),
        "expected": "INFORMATIONAL",
        "note": (
            "Contains a value-adjacent question ('which is canon') but it's "
            "asking for a factual/community-consensus answer, not soliciting "
            "a debate. Clear Informational."
        ),
    },
    {
        "id": "B09",
        "collision": "REACTIVE vs ANALYTICAL",
        "text": (
            "Just finished the series. I feel nothing. "
            "I think that might actually be the correct response — "
            "Isayama designed the ending to leave you numb, not satisfied."
        ),
        "expected": "ANALYTICAL",
        "note": (
            "Opens as Reactive but pivots to an interpretive claim about "
            "authorial intent. The claim is the dominant purpose by the end. "
            "Priority rule: ANALYTICAL > REACTIVE."
        ),
    },
    {
        "id": "B10",
        "collision": "EVALUATIVE vs INFORMATIONAL",
        "text": (
            "Does anyone else think Armin was completely useless in S4? "
            "He had like three scenes and accomplished nothing."
        ),
        "expected": "EVALUATIVE",
        "note": (
            "Framed as a question but 'completely useless' is a judgment, "
            "not a request for information. The 'does anyone else think' "
            "framing is a social softener, not a genuine information seek."
        ),
    },
]

# ---------------------------------------------------------------------------
# Groq classifier
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a discourse classifier for r/attackontitan posts.

Classify the post into exactly one of these labels:

ANALYTICAL   — argues a specific interpretation, theory, or causal claim about
               the story/characters/themes, backed by evidence. Reasoning is the
               point; the conclusion is downstream of it.

EVALUATIVE   — asserts an object-level judgment about THE WORK that others could
               dispute: good/bad/best/worst/overrated, rankings, comparative
               claims ("unmatched", "better than X"). The verdict is the point;
               any reasons are brief and prop up the conclusion. The claim must
               be about the show/characters/craft, not about the speaker.

INFORMATIONAL — seeks or supplies factual, lore, or production information:
               questions, manga-vs-anime comparisons, watch-order, continuity
               checks, "did I miss this."

REACTIVE     — expresses the speaker's emotion, hype, humor, or personal
               experience. First-person felt states ("nothing hits the same",
               "I can't enjoy anything else", "I feel nothing") are REACTIVE
               even when the grammar points at a show — they are autobiography,
               not claims about the work. No disputable proposition survives
               stripping the feeling.

Tiebreaker priority (apply ONLY after the boundary tests below; do not use as
  a shortcut):
  ANALYTICAL > INFORMATIONAL > EVALUATIVE > REACTIVE

Key boundary rule — ANALYTICAL vs EVALUATIVE:
  Ask: "If I removed the conclusion, does a standalone argument remain?"
  Yes → ANALYTICAL. No → EVALUATIVE.

Key boundary rule — EVALUATIVE vs REACTIVE:
  Ask: "Could a reasonable person dispute this claim ON THE MERITS of the work?"
  - Claim is about the show/craft/characters and is rankable or rebuttable
    → EVALUATIVE.  Example: "AoT is the best long-form narrative in anime."
  - Claim is about what the show did TO THE SPEAKER (their feelings, their
    ability to enjoy other things) → REACTIVE, even if phrased as a verdict.
    Example: "This show ruined every other anime for me."

Respond with a JSON object and nothing else:
{
  "label": "<LABEL>",
  "confidence": <0.0–1.0>,
  "reasoning": "<one sentence explaining the dominant function of the post>"
}"""


def classify(post_text: str, client: Groq, model: str = "llama-3.3-70b-versatile") -> dict:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": post_text},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    import json
    return json.loads(response.choices[0].message.content)


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

def run_boundary_tests(client: Groq) -> None:
    print(f"\n{'='*70}")
    print("TakeMeter — Boundary Case Evaluation")
    print(f"{'='*70}\n")

    results = {"pass": 0, "fail": 0}

    for post in BOUNDARY_POSTS:
        result = classify(post["text"], client)
        predicted = result["label"]
        expected = post["expected"]
        passed = predicted == expected
        status = "PASS" if passed else "FAIL"
        results["pass" if passed else "fail"] += 1

        print(f"[{status}] {post['id']} ({post['collision']})")
        print(f"  Expected : {expected}")
        print(f"  Predicted: {predicted}  (confidence {result['confidence']:.2f})")
        print(f"  Reasoning: {result['reasoning']}")
        if not passed:
            print(f"  Note     : {post['note']}")
        print()

    total = len(BOUNDARY_POSTS)
    print(f"{'='*70}")
    print(f"Result: {results['pass']}/{total} passed")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY not set. Export it before running:\n"
            "  $env:GROQ_API_KEY = 'gsk_...'"
        )

    client = Groq(api_key=api_key)
    run_boundary_tests(client)
