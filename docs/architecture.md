# TakeMeter — System Architecture

**Status:** Accepted  
**Date:** 2026-06-25  
**Project:** TakeMeter — Anime Discourse Quality Classifier

---

## Overview

TakeMeter is a two-track ML system. Track A classifies the *mode* of an anime take (what the author is doing). Track B measures the *validity* of that take (is it grounded and well-reasoned). Track A gates Track B: validity is only meaningful for claim-bearing posts, and the weighting between factual and logical scores is determined by the Track A label.

---

## Full System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          INPUT LAYER                                        │
│                                                                             │
│   Reddit post (text + subreddit metadata)                                  │
│   └─ series identified from subreddit:                                     │
│      r/attackontitan → AOT                                                 │
│      r/HunterXHunter → HXH                                                │
│      r/FullmetalAlchemist → FMA                                            │
│      r/evangelion → NGE                                                    │
└─────────────────────────────┬───────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TRACK A — DISCOURSE CLASSIFIER                           │
│                                                                             │
│   fine-tuned RoBERTa (or DeBERTa-v3 / ModernBERT, selected by CV)         │
│   input: raw post text                                                      │
│   output: {Analytical | Evaluative | Informational | Reactive}             │
│                                                                             │
│   Training data: ~550+ labeled Reddit posts across 4 subreddits           │
│   Evaluation: stratified 5-fold CV, primary metric = macro-F1             │
│   Target: mean CV macro-F1 ≥ 0.80                                         │
└──────────────────────────┬──────────────────────────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │  label == Reactive?     │
              └────┬──────────┬─────────┘
                   │ YES      │ NO
                   ▼          ▼
            ┌──────────┐  continue to Track B
            │  ABSTAIN │
            │  no score│
            └──────────┘
```

---

## Track B — Validity Pipeline

```
post + series + label
        │
        ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  STAGE 3 — RETRIEVAL                                                      │
│                                                                           │
│  embed post (sentence-transformers: bge-small-en-v1.5)                   │
│       │                                                                   │
│       ▼                                                                   │
│  FAISS index query → filter to take's series (metadata field)            │
│       │                                                                   │
│       └──► top-k canon chunks  [{text, series, page_title, section}]     │
└─────────────────────────────────┬─────────────────────────────────────────┘
                                  │
                    ┌─────────────┴──────────────┐
                    │                            │
                    ▼                            ▼
┌───────────────────────────┐   ┌────────────────────────────────────────┐
│  HEAD A — FACTUAL         │   │  HEAD B — LOGICAL                      │
│                           │   │                                        │
│  Groq (llama-3.3-70b)     │   │  Groq (llama-3.3-70b)                 │
│                           │   │                                        │
│  Prompt: given CANON      │   │  Prompt: extract premises +            │
│  passages and the TAKE,   │   │  conclusion; judge whether conclusion  │
│  label each factual claim │   │  follows; name any fallacies.          │
│  supported / contradicted │   │  Use ONLY the take itself —           │
│  / unverifiable.          │   │  no canon needed.                      │
│  Cite passage. No outside │   │                                        │
│  knowledge.               │   │  Output (JSON):                        │
│                           │   │  {sound: bool, issues: [str],          │
│  Output (JSON):           │   │   coherence_score: 0.0–1.0}           │
│  {claims: [{text, label,  │   │                                        │
│  evidence}],              │   └──────────────────┬─────────────────────┘
│  factual_score: 0.0–1.0}  │                      │
│                           │                      │
│  F = supported /          │   C = coherence_score│
│    (supported+contradicted│                      │
│    ) — unverifiable       │                      │
│    excluded, not penalized│                      │
└───────────┬───────────────┘                      │
            │                                      │
            └─────────────────┬────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  STAGE 5 — LABEL-WEIGHTED SCORE                                           │
│                                                                           │
│  Label from Track A determines weighting:                                 │
│                                                                           │
│  ┌───────────────┬──────────────────────────────────────────────────┐    │
│  │ Label         │ Formula                  │ Rationale             │    │
│  ├───────────────┼──────────────────────────┼───────────────────────┤    │
│  │ Informational │ 0.8·F  +  0.2·C          │ Fact retrieval first  │    │
│  │ Analytical    │ 0.5·F  +  0.5·C          │ Claims + reasoning    │    │
│  │ Evaluative    │ 0.3·F  +  0.7·C          │ Coherence of verdict  │    │
│  │ Reactive      │ ABSTAIN                  │ No claims to evaluate │    │
│  └───────────────┴──────────────────────────┴───────────────────────┘    │
│                                                                           │
│  validity_pct = round((label_weight(F, C)) * 100)                        │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## Track B — Knowledge Base Build (One-Time)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 1 — FANDOM WIKI INGESTION                                        │
│                                                                         │
│  Source: MediaWiki API (/api.php) — no scraping, no key required        │
│                                                                         │
│  4 wikis:                                                               │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  attackontitan.fandom.com   →  data/wiki_raw/aot/*.json          │  │
│  │  hunterxhunter.fandom.com   →  data/wiki_raw/hxh/*.json          │  │
│  │  fma.fandom.com             →  data/wiki_raw/fma/*.json          │  │
│  │  evangelion.fandom.com      →  data/wiki_raw/nge/*.json          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  Method:                                                                │
│  1. list=allpages (namespace 0 only) + continue token → full enumerate  │
│  2. prop=extracts&explaintext=1 → clean plaintext per page              │
│  3. Tag each doc: {series, page_title, url}                             │
│  4. Cache raw JSON — re-runs are free                                   │
│  5. Rate: ~2 req/s, real User-Agent header                             │
│                                                                         │
│  Scale: ~thousands of pages total across 4 wikis (not millions)        │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 2 — INDEX BUILD                                                  │
│                                                                         │
│  Input:  data/wiki_raw/<series>/*.json                                  │
│  Output: data/index/  (FAISS flat index + metadata list)               │
│                                                                         │
│  Steps:                                                                 │
│  1. Section-aware chunking (~400 tokens, preserve section header)       │
│  2. Metadata per chunk: {series, page_title, section, text}            │
│  3. Embed: sentence-transformers/bge-small-en-v1.5                     │
│     (fast, strong retrieval, runs locally, no API cost)                │
│  4. faiss.IndexFlatIP (cosine similarity via normalized vectors)        │
│  5. Save: index.faiss + metadata.jsonl                                 │
│                                                                         │
│  Scale: flat index is instant at this volume — no IVF/HNSW needed     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## File Layout

```
TakeMeter/
├── data/
│   ├── dataset.csv              # labeled posts (Track A training)
│   ├── wiki_raw/                # Stage 1 output
│   │   ├── aot/
│   │   ├── hxh/
│   │   ├── fma/
│   │   └── nge/
│   └── index/                  # Stage 2 output
│       ├── index.faiss
│       └── metadata.jsonl
├── scripts/
│   ├── scraping/
│   │   ├── dump_fandom.py       # Stage 1: MediaWiki API ingestion
│   │   └── ...existing scrapers
│   ├── labeling/
│   │   └── ...existing labelers
│   └── rag/
│       ├── build_index.py       # Stage 2: embed + FAISS build
│       ├── retrieve.py          # Stage 3: query + series filter
│       └── verify.py            # Stages 4–5: Groq heads + scoring
├── docs/
│   └── architecture.md          # this file
├── train.py                     # Track A training harness
├── planning.md
└── requirements.txt
```

---

## Key Design Decisions

### D1: Series routing from subreddit metadata, not entity linking
Posts are scraped per-subreddit, so `subreddit → series` is a deterministic lookup, not an NLP problem. Store as a column. Only cross-series posts (rare) would need entity linking — deferred until evidence of prevalence.

### D2: Two separate scoring heads, not one prompt
Factual accuracy and logical coherence are orthogonal: a take can be **factually correct but logically broken**, or **logically sound but factually wrong**. A single combined prompt destroys exactly the signal TakeMeter is designed to surface. Separate heads → separate scores → label-weighted combination.

### D3: Unverifiable claims excluded, not penalized
A factual claim the wiki doesn't cover is neither supported nor contradicted — it is unknown. Penalizing it would bias validity against niche or detailed takes. Only `supported / (supported + contradicted)` enters F; unverifiable claims are logged but excluded from the denominator.

### D4: Track A label gates Track B, and sets the F/C weighting
Running validity on a Reactive post is noise, not signal — there are no propositions to evaluate. The label also determines the F/C split, so **a Track A misclassification assigns the wrong validity weights**. This is why Track A must clear macro-F1 ≥ 0.72 before Track B work begins.

### D5: Local FAISS over managed vector DB
At 4-series scale (thousands of pages), a flat FAISS index on disk is instant to query, free to run, and reproducible. A managed DB (pgvector/Pinecone) adds infra complexity with no throughput benefit at this scale. Revisit if the corpus grows to 10+ series.

### D6: Groq over local NLI for verification
Reddit prose is informal, elliptical, and full of series-specific jargon. NLI models fine-tuned on formal text (MNLI/SNLI) are brittle here. A 70B LLM judge via Groq handles the register mismatch and outputs structured JSON with cited evidence. The free tier is sufficient at evaluation scale; cache verdicts by post ID so re-runs are free.

---

## Evaluation Plan (Track B)

| Step | Method | Target |
|---|---|---|
| Factual head accuracy | Hand-label 50–80 (claim, passage) pairs as supported/contradicted/unverifiable; compare to Groq output | Cohen's κ ≥ 0.65 |
| Coherence head accuracy | Hand-label 50–80 takes as sound/fallacious; compare to Groq output | Cohen's κ ≥ 0.65 |
| End-to-end validity correlation | Human score 30–40 takes 0–100; compare to pipeline output | Spearman ρ ≥ 0.70 |
| Downstream fine-tune (optional) | Distil pipeline into single DeBERTa regressor; evaluate with MAE + Spearman on held-out RAG scores | MAE ≤ 10 pts |

---

## Dependencies to Add

```
# requirements.txt additions for Track B
faiss-cpu>=1.8.0
sentence-transformers>=3.0.0
groq>=0.9.0
```
