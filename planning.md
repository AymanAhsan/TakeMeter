# TakeMeter — Project Planning

## Community

The project draws from four anime subreddits selected against a consistent set of criteria: **closed canon** (finished anime adaptation, no ongoing-release confound), **substantive discourse** (community generates Analytical and Informational posts, not just hype), and **distinct rhetorical register** (each community reasons differently, improving classifier generalization).

### Selection criteria

A subreddit is eligible if:
1. The anime adaptation is **complete** — every post reasons about the same closed text.
2. The community is large enough to supply **100+ labelable posts** without scraping edge cases.
3. The dominant discourse mode is **not purely Reactive** — there must be enough Analytical and Informational content for those classes to be well-populated.

### r/attackontitan

Attack on Titan has a well-defined, complete canon. The ending is genuinely divisive, the adaptation choices generated real critical discourse, and the thematic content — genocide, cycles of violence, determinism — attracts posts that go beyond surface-level reaction. The community (~700k members) is large enough for strong coverage but not so large as r/anime that signal drowns in noise.

### r/HunterXHunter

HxH complements AOT with a meaningfully different discourse profile. Debates cluster around structural and thematic depth — the Chimera Ant arc's pacing, Gon's moral arc, Meruem's character — rather than adaptation controversy. This populates the Analytical and Informational classes through a different rhetorical register, improving diversity. The 2011 adaptation is complete (~400k members).

### r/FullmetalAlchemist

FMA: Brotherhood is a closed adaptation widely regarded as one of the strongest in the medium. Community discourse skews philosophical and moral — debates about equivalent exchange, Hohenheim's arc, the ending — which produces a different Analytical register than either AOT or HxH. This is the primary source for the targeted data expansion (~250k members).

### r/evangelion

Neon Genesis Evangelion has a closed adaptation and one of the most interpretively active communities in anime. Discourse is heavily psychological and thematic — instrumentality, character motivation, the End of Evangelion — producing dense Analytical content through a register unlike any of the other three sources. The unusually high ratio of Analytical to Reactive posts makes it valuable for addressing the minority-class imbalance (~200k members).

---

## Labels

The taxonomy classifies by **discourse mode** — what the author is primarily doing — not by quality. Mode is mutually exclusive in a way quality ratings are not. The annotation question for every post: *"What is the author primarily doing here?"*

### 1. Analytical
The author argues a specific interpretation, theory, or causal claim about the story, characters, or themes, and supports it with evidence from the text.

- *"Eren's 'freedom' speech in S1 is deliberate foreshadowing — he's echoing inherited memories he hadn't yet consciously processed. The basement reveal recontextualizes the entire scene; Isayama staged it knowing exactly what it meant."*
- *"The Marley arc is structurally a mirror of the Shiganshina arc, with Reiner as the inverse-Eren. The cycle-of-hatred theme only lands if you read those two arcs as a diptych. Here's the parallel beat breakdown..."*

### 2. Evaluative
The author asserts a judgment, ranking, or preference — good/bad, best/worst, overrated/underrated — without substantive supporting argument. The conclusion is the point; any reasons are brief and prop up the verdict rather than constitute an argument.

- *"S4 Part 2 is peak fiction. The animation discourse was completely overblown."*
- *"Hot take: Gabi is a better-written character than most of this sub is willing to admit. She just is."*

### 3. Informational
The author seeks or supplies factual, lore, or production information — questions, manga-vs-anime comparisons, source clarifications, watch-order, continuity checks, "did I miss this."

- *"Did the anime cut the scene where the Paths mechanic is explained in detail? Just started the manga and I can't find the corresponding anime scene."*
- *"For everyone confused about the coordinate/Paths timeline — here's a chapter-by-chapter breakdown of how the memory inheritance actually works."*

### 4. Reactive
The author expresses emotion, hype, humor, or shared reaction with no claim or question. The post exists to vent, celebrate, or vibe — not to argue or inform.

- *"JUST FINISHED THE FINALE. I am physically unable to function. That's it. That's the post."*
- *"Rewatching the S2 OP for the 40th time. Peak human achievement. No notes."*

---

## Hard Edge Cases

**Analytical vs. Evaluative** — the most common collision.

Both labels can contain judgments and reasons. The boundary: in an Analytical post, the *reasoning is the point* and the judgment is downstream of it. In an Evaluative post, the *verdict is the point* and reasons (if present) are brief decoration.

*Hard case:* "The Levi vs. Beast Titan fight is the best in the series — the spinning maneuver, the timing, the music cue all land perfectly." This lists specific reasons, but the headline is a ranking and the reasons just support it. → **Evaluative.**

*Resolution rule:* Ask "if I removed the conclusion, does a standalone argument remain?" If yes → Analytical. If you're left with a list of observations with no connecting claim → Evaluative.

**Informational vs. Analytical** — triggered by "why" questions.

*Hard case:* "Why did Eren turn evil? I don't understand his motivation." This is phrased as a question (Informational) but the answer requires interpretation, not fact retrieval.

*Resolution rule:* If the answer is a fact (yes/no, a date, a plot event), it's Informational. If the answer requires argument and a reasonable person could disagree, label by what the post is *doing*: a genuine open question → Informational; a rhetorical question baiting a debate → Analytical or Evaluative depending on whether a claim is embedded.

**Reactive vs. Evaluative** — triggered by emotional superlatives.

*Hard case:* "This show ruined every other anime for me, nothing hits the same." Emotional in tone but contains an implicit comparative judgment.

*Resolution rule:* Remove the emotion. Does a debatable claim survive? "Nothing hits the same" is a feeling, not a proposition someone can falsify → **Reactive.** Contrast: "This is objectively the best-constructed long-form narrative in anime" — that survives as a claim → **Evaluative.**

**Tiebreaker priority order (apply when genuinely uncertain):**

> Analytical > Informational > Evaluative > Reactive

Assign the highest-priority label the post *genuinely satisfies*. This resolves every multi-label case to exactly one label and is applied consistently across all annotators.

---

## Data Collection Plan

**Source:** Reddit posts and top-level comments from four subreddits (r/attackontitan, r/HunterXHunter, r/FullmetalAlchemist, r/evangelion), scraped via Playwright browser automation against old.reddit.com.

**Existing data:** 373 labeled examples from r/attackontitan and r/HunterXHunter (v1 scrape).

**v2 expansion:** ~150–200 additional examples from r/FullmetalAlchemist and r/evangelion via targeted scraping (`scrape_targeted.py`), focused on the two class boundaries the v1 model failed at.

### Targeted scraping passes

Error analysis on the v1 model identified two systematic failure modes that targeted collection directly addresses:

**Pass 1 — Meme-register Reactive** (fixes: Reactive predicted as Evaluative)

The v1 model consistently misclassified internet-slang and meme-language Reactive posts (e.g. "that's my roman empire", "vocal stim", deadpan humor) as Evaluative because their syntax superficially resembles comparative judgment. Remediation: search each subreddit for posts and comments containing meme-signal vocabulary (`unironically`, `roman empire`, `rent free`, `ngl`, `cope`, `lmao`, etc.) and short posts (<80 words). These are accepted into the dataset regardless of whether they contain explicit emotional language — the meme register itself is the signal.

**Pass 2 — Detailed Informational** (fixes: Informational predicted as Analytical)

The v1 model classified thorough, structured factual explanations as Analytical because it learned "detailed + evidence-citing → Analytical." The correct signal is whether a claim is being *defended*, but surface features are indistinguishable. Remediation: search for question-titled posts (`?`, `why`, `how`, `what`, `explain`) and collect long top-level comments (≥80 words) replying to them. These are typically detailed factual answers that the model needs to learn are Informational, not Analytical.

**Pass 3 — General Discussion** (balanced coverage for new subreddits)

A standard top-posts scrape from each new subreddit to provide general class coverage and expose the model to FMA- and NGE-specific vocabulary and rhetorical patterns.

### Seeding strategy summary

| Pass | Target class | Filter |
|---|---|---|
| Meme-register | Reactive | Meme-signal vocabulary OR post length <80 words |
| Detailed Informational | Informational | Question title + comment length ≥80 words |
| General Discussion | All | Top discussion posts, no filter |

### Labeling

All scraped rows are labeled manually after collection. The same tiebreaker priority order applies: Analytical > Informational > Evaluative > Reactive.

**If a label is still underrepresented after the v2 expansion:**
1. Increase targeted pass depth (more search queries, more posts per query).
2. If Informational remains below 15% of the dataset after remediation, consider merging it into Analytical (interpretation questions) and Reactive (validation questions), collapsing to a 3-label taxonomy before retraining.

---

## Evaluation Metrics

**Primary: Macro F1**

Accuracy is insufficient because the label distribution will not be uniform — Reactive and Evaluative posts are more common than Analytical ones on Reddit. A model that labels everything Evaluative would achieve high accuracy but be useless. Macro F1 weights each class equally regardless of frequency, which penalizes the model for ignoring minority classes.

**Secondary: Per-class F1 and confusion matrix**

The confusion matrix between Analytical and Evaluative is the most diagnostically important output. If those two classes are bleeding into each other, the model hasn't learned the core distinction the taxonomy is built around. Per-class F1 lets you see this directly; aggregate metrics hide it.

**Secondary: Cohen's Kappa on the annotation set**

Before training anything, measure inter-annotator agreement on a 50-post overlap sample. If Kappa < 0.65, the label definitions are insufficiently sharp and the model will learn noise. Fix the definitions before proceeding. A classifier can't exceed the reliability of its labels.

**Not used: AUC-ROC**

AUC is appropriate for binary tasks or when calibrated probabilities matter. This is a 4-class task where the deployment output is a discrete label, not a score, so AUC adds interpretive complexity without actionable signal.

---

## Definition of Success

**Minimum viable:** Macro F1 ≥ 0.72 on a held-out test set, with no individual class F1 below 0.60. Below this, the classifier is worse than a human reading the post for 10 seconds, and deploying it would actively mislead anyone using it.

**Good enough for deployment:** Macro F1 ≥ 0.80, Analytical/Evaluative confusion rate below 15% (measured from the confusion matrix), and inter-annotator Kappa on the training set ≥ 0.70 (confirming the labels are learnable, not just that the model found a shortcut).

**What "deployment" means here:** The classifier would be used as a quality signal — surfacing Analytical posts for community highlights, flagging Reactive-only posts for potential removal from discussion threads, or providing post authors with a label to encourage more substantive writing. At F1 ≥ 0.80, false positives are infrequent enough that the tool adds value without requiring a human in the loop for every decision.

**What would invalidate the project:** If Analytical and Evaluative cannot be separated above F1 = 0.65 after hyperparameter tuning, the boundary defined in this plan is not learnable from text features alone, and the taxonomy should be collapsed to 3 labels (merging them into a single "Opinion" class) before retraining.

---

## v2 — Fine-Tuning Redesign (Track A: Discourse Classifier)

This supersedes the earlier fine-tuning approach. Prior results are not carried forward — the redesign starts from a clean slate. The focus is the **evaluation protocol first, model second**, because at 373 labeled examples a single train/test split is statistically meaningless (the prior run's entire gap was ~2 examples).

### Evaluation protocol

- **Stratified 5-fold cross-validation** is the primary harness. Report macro-F1 as **mean ± std across folds** — not a single number from one split.
- A small **final hold-out set (~40 examples, stratified)** is set aside and touched exactly once, at the very end, to sanity-check the CV estimate. It is never used for model or hyperparameter selection.
- **Primary metric:** macro-F1 (class imbalance makes accuracy misleading — Reactive is 38%).
- **Secondary:** per-class F1 and a confusion matrix aggregated across folds. The Analytical↔Evaluative and Informational↔Analytical cells are the diagnostic focus.
- All runs are **seed-pinned** for reproducibility.

### Model selection — bake-off

Run the *same* CV harness across several encoders and select by mean CV macro-F1. The harness is written so the model is a one-line swap; compute is negligible (full bake-off is well under an hour on a free GPU).

| Candidate | Params | Why try it |
|---|---|---|
| `microsoft/deberta-v3-base` | 184M | strongest small-data encoder; expected front-runner |
| `answerdotai/ModernBERT-base` | 149M | modern long-context encoder, strong recent benchmarks |
| `roberta-base` | 125M | robust, well-understood baseline |
| `distilbert-base-uncased` | 66M | speed reference point |

### Training discipline (small-data)

- **Class-weighted cross-entropy** (inverse-frequency) to handle the imbalance.
- **Early stopping** on validation macro-F1 instead of a fixed epoch count.
- Light hyperparameter search inside CV: learning rate ∈ {1e-5, 2e-5, 3e-5}; warmup = 10% of total steps computed as an integer.
- Optional minority-class text augmentation (LLM paraphrase / back-translation) — adopted only if it improves CV macro-F1, not assumed.

### Hugging Face integration

- Built on `transformers` `Trainer` + `datasets`.
- The winning configuration is retrained on all available data and pushed to the **HF Hub** with a model card documenting the CV results (mean ± std, per-class F1, confusion matrix).

### Success criteria (unchanged target, stronger measurement)

- **Minimum viable:** mean CV macro-F1 ≥ 0.72 with no class below 0.60.
- **Good:** mean CV macro-F1 ≥ 0.80 with Analytical/Evaluative confusion < 15%.
- Because the estimate is now a CV mean ± std rather than one split, "we beat the target" must mean the *lower* end of the spread clears it, not a lucky single run.

### Out of scope (deferred)

Track B (validity model) is not part of this phase. It depends on the RAG pipeline existing first to bootstrap validity labels, and is documented separately when that work begins.

---

## v2 — Validity Meter (Track B: deferred)

**This section documents the planned design. No implementation begins until Track A clears the macro-F1 ≥ 0.72 target.**

See `docs/architecture.md` for the full system diagram.

### What validity measures

For each take, validity outputs a single percentage (0–100) combining two sub-scores:

- **Factual accuracy (F):** how well the take's verifiable claims match evidence retrieved from the wiki knowledge base.
- **Logical coherence (C):** whether the take's argument follows from its own stated premises, independent of whether the claims are true.

Opinions are inherently subjective, so validity does not ask whether a take is "correct." It asks whether the take is *grounded* (factually) and *consistent* (logically). A post can have low factual accuracy and high coherence (a well-argued wrong claim) or high factual accuracy and low coherence (accurate facts, incoherent argument). These are orthogonal axes — collapsing them into one prompt destroys exactly the signal TakeMeter is designed to surface.

### Discourse label gates the validity weighting

The discourse label from Track A feeds directly into the validity pipeline. Reactive posts produce no validity score (they contain no claims or arguments to evaluate). For all other labels, the weighting between F and C shifts based on what the label tells us the post is primarily doing:

| Label | Validity formula | Rationale |
|---|---|---|
| Informational | 0.8·F + 0.2·C | Almost pure fact retrieval; coherence is secondary |
| Analytical | 0.5·F + 0.5·C | Claims and reasoning both matter equally |
| Evaluative | 0.3·F + 0.7·C | Judgment post; coherence of the verdict matters more than factual precision |
| Reactive | N/A (abstain) | No verifiable claims, no argument to evaluate |

This means **Track A must be reliable before Track B is meaningful** — a misclassified label assigns the wrong weights, and a Reactive misclassification wastes a Groq call or silently skips a real take.

### Pipeline architecture (5 stages)

```
take + series + label (from Track A)
        │
        ├─ label == Reactive → ABSTAIN (no score)
        │
        ▼
[Stage 1] CORPUS (one-time batch)
  MediaWiki API → 4 Fandom wikis (AOT, HXH, FMA, NGE)
  allpages + extracts → data/wiki_raw/<series>/*.json

[Stage 2] INDEX BUILD (one-time batch)
  section-aware chunking (~400 tok) → embed (bge-small-en-v1.5)
  → faiss.IndexFlatIP + metadata.jsonl → data/index/

[Stage 3] RETRIEVAL (per-take, real-time)
  embed take → FAISS query → filter to take's series
  → top-k canon chunks

[Stage 4] TWO PARALLEL VERIFICATION HEADS (Groq, llama-3.3-70b-versatile)
  ┌─ Head A FACTUAL: claims vs retrieved canon
  │    F = supported / (supported + contradicted)
  │    unverifiable → excluded, not penalized
  │    output: JSON {claims[{text, label, evidence}], factual_score}
  │
  └─ Head B LOGICAL: argument structure (no retrieval needed)
       "do the premises support the conclusion?"
       output: JSON {sound, issues[], coherence_score}

[Stage 5] WEIGHTED SCORE
  validity_pct = round(label_weight(F, C) * 100)
```

### Knowledge base

The KB is a **frozen snapshot** of wiki pages for AOT, HxH, FMA, and NGE sourced from Fandom wikis via the MediaWiki API (`/api.php`). No HTML scraping, no API key required. Closed canon means the snapshot is correct and does not need live updates.

**Series routing:** posts are scraped per-subreddit, so `subreddit → series` is a deterministic lookup stored as a column. No entity linking needed.

**Critical rule:** a claim not covered by the KB is excluded from scoring — not penalized as false. Penalizing missing wiki coverage would bias validity against niche or detailed claims.

### Implementation build order

1. `scripts/scraping/dump_fandom.py` — MediaWiki `allpages` + `extracts` ingest → `data/wiki_raw/`
2. `scripts/rag/build_index.py` — chunk, embed, FAISS build → `data/index/`
3. `scripts/rag/retrieve.py` — series-filtered query wrapper
4. `scripts/rag/verify.py` — Groq two-head verifier, cached by post ID
5. Eval: hand-label 50–80 examples per head, measure Cohen's κ before any fine-tuning

### Judge: Groq (llama-3.3-70b-versatile)

Groq is used for both heads. Reasons over local NLI (e.g. DeBERTa-MNLI):
- Reddit prose is informal and jargon-heavy; NLI models trained on formal text (MNLI/SNLI) are brittle in this register.
- A 70B LLM handles elliptical phrasing and series-specific vocabulary without fine-tuning.
- `response_format={"type":"json_object"}` enforces parseable output.
- Verdicts cached by post ID so re-runs are free. Groq free tier is sufficient at evaluation scale.

### Bootstrap process for validity labels

No validity-labeled data exists. Labels are generated as follows:
1. Run the full pipeline over all labeled examples → auto-generate `validity_pct`, `factual_score`, `coherence_score` for each.
2. Human-review a stratified sample of ≥50 rows per head, checking the cited evidence and the pipeline's scoring decision. Measure Cohen's κ — same discipline as the discourse labeling phase.
3. If κ ≥ 0.65, fine-tune on auto-labels. If κ < 0.65, the pipeline has a systematic error (bad retrieval or bad prompt) that must be fixed before any fine-tuning.

### Fine-tuning targets (Track B)

- **Validity regressor** — distill the full pipeline into a single DeBERTa regression head (MSE loss, 1 output) for fast serve-time scoring without live Groq calls. Evaluate with MAE + Spearman correlation against held-out RAG-generated scores, using the same 5-fold CV protocol as Track A.
- **NLI cross-encoder (optional)** — fine-tune a DeBERTa cross-encoder on `(claim, evidence)` pairs for the factual head. Adopt only if zero-shot Groq agreement is below κ 0.65 on the hand-labeled eval set.

### New dependencies (Track B)

```
faiss-cpu>=1.8.0
sentence-transformers>=3.0.0
groq>=0.9.0
```
