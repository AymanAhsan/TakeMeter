# TakeMeter

A fine-tuned DistilBERT classifier that labels Reddit posts from r/attackontitan and r/HunterXHunter by discourse mode — Analytical, Evaluative, Informational, or Reactive — trained on 373 hand-labeled examples.

---

## Community Choice and Reasoning

TakeMeter draws from two subreddits: **r/attackontitan** and **r/HunterXHunter**.

### r/attackontitan

Attack on Titan is chosen over a general anime subreddit because the community operates on a closed canon — the manga is finished and the anime adaptation has concluded. This eliminates a major confound: posts aren't split between speculation and analysis modes depending on where the story currently is. Every post reasons about the same complete text.

The community is also unusually argumentative in a productive way. The ending is genuinely divisive, the adaptation choices generated real critical discourse, and the thematic content — genocide, cycles of violence, determinism — attracts posts that go beyond surface-level reaction. This means the label space is well-populated: you find real analytical posts, not just hype and memes. A subreddit for a lighter show would skew so heavily toward Reactive that the other classes would be underrepresented.

Finally, the community (~700k members) is large enough to supply 200+ labelable posts without scraping edge cases, but not so large as r/anime that signal drowns in noise.

### r/HunterXHunter

Hunter x Hunter complements AOT as a second source. Like AOT, it has a closed anime adaptation — the 2011 series is finished and covers the full Chimera Ant and Election arcs. Posts are not muddied by release-day hype tied to ongoing episodes.

The community's discourse profile is meaningfully different from AOT's, which improves classifier generalization. HxH debates tend to cluster around structural and thematic depth — the Chimera Ant arc's pacing, Gon's moral arc, Meruem's character — rather than adaptation controversy. This populates the Analytical and Informational classes through a different rhetorical register, making training data more diverse.

The subreddit (~400k members) is large enough to supply sufficient labelable posts but small enough that lower-quality content hasn't diluted discussion threads to noise.

---

## Label Taxonomy

The taxonomy classifies by **discourse mode** — what the author is primarily doing — not by quality. Mode is mutually exclusive; the annotation question for every post is: *"What is the author primarily doing here?"*

### 1. Analytical

The author argues a specific interpretation, theory, or causal claim about the story, characters, or themes, and supports it with evidence from the text.

> *"Eren's 'freedom' speech in S1 is deliberate foreshadowing — he's echoing inherited memories he hadn't yet consciously processed. The basement reveal recontextualizes the entire scene; Isayama staged it knowing exactly what it meant."*

> *"The Marley arc is structurally a mirror of the Shiganshina arc, with Reiner as the inverse-Eren. The cycle-of-hatred theme only lands if you read those two arcs as a diptych. Here's the parallel beat breakdown..."*

### 2. Evaluative

The author asserts a judgment, ranking, or preference — good/bad, best/worst, overrated/underrated — without substantive supporting argument. The conclusion is the point; any reasons are brief and prop up the verdict rather than constitute an argument.

> *"S4 Part 2 is peak fiction. The animation discourse was completely overblown."*

> *"Hot take: Gabi is a better-written character than most of this sub is willing to admit. She just is."*

### 3. Informational

The author seeks or supplies factual, lore, or production information — questions, manga-vs-anime comparisons, source clarifications, watch-order, continuity checks, "did I miss this."

> *"Did the anime cut the scene where the Paths mechanic is explained in detail? Just started the manga and I can't find the corresponding anime scene."*

> *"For everyone confused about the coordinate/Paths timeline — here's a chapter-by-chapter breakdown of how the memory inheritance actually works."*

### 4. Reactive

The author expresses emotion, hype, humor, or shared reaction with no claim or question. The post exists to vent, celebrate, or vibe — not to argue or inform.

> *"JUST FINISHED THE FINALE. I am physically unable to function. That's it. That's the post."*

> *"Rewatching the S2 OP for the 40th time. Peak human achievement. No notes."*

---

## Data Collection

### Source

Reddit posts from r/attackontitan and r/HunterXHunter scraped via Claude Playwright MCP

**Volume:** 373 posts from Discussion/Question and Ending Spoilers - Discussion/Question flairs, which are the most likely to contain Analytical and Informational content.

### Labeling Process

Each post is read in full and assigned exactly one label based on the primary discourse mode. When a post satisfies more than one label, a tiebreaker priority order is applied:

> **Analytical > Informational > Evaluative > Reactive**

Assign the highest-priority label the post genuinely satisfies.

### Label Distribution

| Label | Count | % of dataset |
|---|---|---|
| Reactive | 143 | 38% |
| Analytical | 90 | 24% |
| Informational | 73 | 20% |
| Evaluative | 67 | 18% |

Reactive is the plurality class but not overwhelmingly dominant thanks to deliberate seeding: Analytical posts were sourced from long-form Analysis/Theory flair; Informational from question posts and "?" titles; Evaluative from posts containing "best", "worst", "overrated", or "hot take". Without targeted seeding a raw Discussion/Question scrape would have been 60–70% Reactive.

### Difficult-to-Label Examples

**Example 1 — Analytical vs. Evaluative**

> *"The Levi vs. Beast Titan fight is the best in the series — the spinning maneuver, the timing, the music cue all land perfectly."*

This lists specific reasons, which looks Analytical. But the headline is a ranking and the reasons just support it; no standalone argument survives if you remove the conclusion. **Label: Evaluative.** Resolution rule: ask "if I removed the conclusion, does a standalone argument remain?" If not, it's Evaluative.

---

**Example 2 — Informational vs. Analytical**

> *"Why did Eren turn evil? I don't understand his motivation."*

Phrased as a question (Informational) but the answer requires interpretation, not fact retrieval. A genuine open question with no embedded claim, not a rhetorical setup for a debate. **Label: Informational.** Resolution rule: if the answer is a fact, it's Informational; if the answer requires argument and a reasonable person could disagree, check whether a claim is embedded — a genuine open question stays Informational.

---

**Example 3 — Reactive vs. Evaluative**

> *"This show ruined every other anime for me, nothing hits the same."*

Emotional in tone but contains an implicit comparative judgment. Remove the emotion: does a debatable claim survive? "Nothing hits the same" is a feeling, not a proposition someone can falsify. **Label: Reactive.** Contrast: "This is objectively the best-constructed long-form narrative in anime" — that survives as a claim and would be Evaluative.

---

## Baseline Classifier

**Model:** `llama-3.3-70b-versatile` via the Groq API, zero-shot (no labeled examples in the prompt).

**Prompt:** The system prompt defined each label with a one-sentence description and a single example, then instructed the model to output only the label name:

```
You are classifying posts from an online discussion community based on the quality
and nature of their discourse. Assign each post to exactly one of the following categories.

Reactive: A post driven primarily by emotional response, venting, or knee-jerk reaction,
with little supporting reasoning or evidence.
Example: "I can't believe they did this again, this is so frustrating and typical."

Analytical: A post that breaks down a topic, weighs causes/effects, or builds a structured
argument with reasoning.
Example: "The price increase is likely tied to the supply chain delays from last quarter,
here's why that connection makes sense..."

Informational: A post primarily sharing facts, data, links, or updates without much personal
interpretation or argument.
Example: "Here's the official announcement and the relevant dates from the press release."

Evaluative: A post that makes a judgment or assessment of something's quality, value, or merit,
typically with criteria or comparison.
Example: "This update is a clear improvement over the last one because it fixes the lag issue,
though the UI is still clunky."

Respond with ONLY the label name. Do not explain your reasoning.
Valid labels: Reactive, Analytical, Informational, Evaluative
```

**Collection:** The baseline was run on the same 56-example held-out test set used for the fine-tuned model. Calls used `temperature=0` and `max_tokens=20` with a 0.1s delay between requests. All 56 responses were parseable — the model output a valid label string every time.

---

## Evaluation Report

### Results Summary

| Model | Accuracy | Macro F1 |
|---|---|---|
| Zero-shot baseline (Groq `llama-3.3-70b-versatile`) | 0.589 | 0.54 |
| Fine-tuned DistilBERT | 0.554 | 0.53 |

The fine-tuned model underperformed the zero-shot baseline by 3.5 percentage points — roughly 2 examples on a 56-example test set. Both models fall well short of the macro F1 ≥ 0.72 target set in planning. The absolute accuracy gap is within noise at this test set size, but the more meaningful failure is that fine-tuning a smaller model on 261 examples did not beat a zero-shot prompt to a 70B parameter LLM.

### Per-Class Metrics

**Zero-shot baseline (Groq):**

| | Precision | Recall | F1 | Support |
|---|:---:|:---:|:---:|:---:|
| Analytical | 0.58 | 0.50 | 0.54 | 14 |
| Evaluative | 0.47 | 0.70 | 0.56 | 10 |
| Informational | 0.43 | 0.27 | 0.33 | 11 |
| Reactive | 0.73 | 0.76 | 0.74 | 21 |
| **Macro avg** | **0.55** | **0.56** | **0.54** | |

**Fine-tuned DistilBERT:**

| | Precision | Recall | F1 | Support |
|---|:---:|:---:|:---:|:---:|
| Analytical | 0.64 | 0.64 | 0.64 | 14 |
| Evaluative | 0.47 | 0.70 | 0.56 | 10 |
| Informational | 0.33 | 0.27 | 0.30 | 11 |
| Reactive | 0.67 | 0.57 | 0.62 | 21 |
| **Macro avg** | **0.53** | **0.55** | **0.53** | |

Fine-tuning improved Analytical F1 by 10 points (0.54 → 0.64) but degraded Reactive F1 by 12 points (0.74 → 0.62) and slightly worsened Informational (0.33 → 0.30). Evaluative was unchanged. The model traded strength on the majority class for marginal gains on the hardest minority class.

### Confusion Matrix (Fine-Tuned Model, Test Set)

|  | Pred: Analytical | Pred: Evaluative | Pred: Informational | Pred: Reactive |
|---|:---:|:---:|:---:|:---:|
| **True: Analytical** | **9** | 3 | 1 | 1 |
| **True: Evaluative** | 0 | **7** | 1 | 2 |
| **True: Informational** | 5 | 0 | **3** | 3 |
| **True: Reactive** | 0 | 5 | 4 | **12** |

The two largest off-diagonal clusters are Informational → Analytical (5 examples) and Reactive → Evaluative (5 examples). Together they account for 10 of 25 errors and point to the two hardest boundaries in the taxonomy: the Informational/Analytical line and the Reactive/Evaluative line.

### Error Analysis

Before writing this analysis, I pasted all 25 wrong predictions into Claude and asked it to identify recurring patterns across the misclassified examples. It surfaced three clusters: (1) Informational posts with detailed explanatory content predicted as Analytical, (2) Reactive posts using internet/meme language predicted as Evaluative, and (3) degenerate low-content inputs defaulting to the majority class. I verified each cluster by re-reading the examples. The meme-register pattern (#2 below) was not obvious when scanning the list one case at a time — it only becomes clear when you notice that multiple Reactive posts share the property of containing culturally-specific phrases that look like comparisons. I discarded Claude's suggestion that post length was a major factor; while longer posts do skew Analytical, the Informational/Analytical errors span a range of lengths.

---

**Case 1 — Informational/Analytical boundary failure (confidence: 1.00)**

> *"Most of the time different characters have described the aura surrounding people's bodies as appearing like a white light or glow. However there also is the one time that Gon described the aura freely..."*
>
> True: **Informational** — Predicted: **Analytical** (confidence: 1.00)

The model is completely certain and completely wrong. The text surveys evidence across multiple scenes and builds toward a point about how nen aura is described — which reads like Analytical. But the author is not defending a claim; they are reporting what the text contains, which is Informational. The model learned that "evidence + structured comparison" → Analytical and fires that pattern with no uncertainty.

This is the hardest boundary in the taxonomy: when information-sharing is thorough enough, surface features become indistinguishable from argumentation. The correct signal is whether a claim is being defended, but DistilBERT has no reliable way to detect argumentative intent vs. descriptive enumeration. To fix this, training data would need more Informational examples that are detailed and structured — the current Informational examples likely skew toward shorter, simpler questions, which leaves the model without enough signal that a long, organized post can still be Informational.

---

**Case 2 — Internet/meme register failure (confidence: 0.98)**

> *"Hange and Erwin being SO close to their goals before dying — that's my roman empire"*
>
> True: **Reactive** — Predicted: **Evaluative** (confidence: 0.98)

"That's my roman empire" is a meme phrase meaning "something I think about often without reason" — a pure emotional/humor reaction, not a judgment. The model sees a named subject (Hange, Erwin), a comparative framing ("SO close to their goals"), and fires Evaluative at near-certainty. It has no knowledge of the meme register and reads the sentence structure as an assessment.

This is a systematic weakness for the Reactive class. The same pattern appears in "Onyankopon is a fantastic vocal stim soo" (predicted Evaluative 0.97) and "That is unironically actually how nen works lmao" (predicted Evaluative 0.57). Each of these is a culturally-specific expression that superficially contains comparative or assertive syntax. The fix would require Reactive training examples that use this style of internet language — the current Reactive examples likely skew toward explicit emotional expression ("I can't believe...", "I am physically unable to function"), which leaves the model without coverage of deadpan or meme-style Reactive posts.

---

**Case 3 — Degenerate input / data quality problem (confidence: 0.99)**

> *"Title"*
>
> True: **Informational** — Predicted: **Reactive** (confidence: 0.99)

The text is literally the word "Title" — a post where no body was written and the title was a placeholder. The model has no content to work with and defaults to Reactive (the plurality class, 38% of training) at maximum confidence. This is a data quality problem, not a model problem. The label itself is questionable: a single-word placeholder has no classifiable discourse mode. Posts like this should be filtered out before training and evaluation — they provide no learnable signal and penalize the model for something that is genuinely not classifiable. Keeping it in the test set inflates the Reactive/Informational confusion cell without telling you anything meaningful about the model's ability to distinguish those classes.

---

### Sample Classifications

Five examples from the test set, showing predicted label and confidence. Confidence scores for incorrect predictions come from the notebook's inference output; the notebook does not print confidence for correct predictions by default.

| Text (truncated to 80 chars) | True | Predicted | Conf | Correct? |
|---|---|---|---|:---:|
| "Miche's death, especially with the season 2 ED playing immediately after." | Reactive | Reactive | — | ✓ |
| "Hange and Erwin being SO close to their goals before dying — that's my roman empire" | Reactive | Evaluative | 0.98 | ✗ |
| "Most of the time different characters have described the aura surrounding people's bodies..." | Informational | Analytical | 1.00 | ✗ |
| "Is A Real-Life Hunter Association Possible?" | Analytical | Evaluative | 0.75 | ✗ |
| "Title" | Informational | Reactive | 0.99 | ✗ |

**On the correct prediction:** "Miche's death, especially with the season 2 ED playing immediately after." is a clean Reactive example — it names a scene and expresses a feeling about it with no claim, question, or argument. There is no comparative judgment (which would push it toward Evaluative), no factual content (Informational), and no interpretive claim (Analytical). The model correctly identifies it as Reactive; a post this structurally simple should be one the model handles reliably.

---

## Reflection

The taxonomy was designed to capture authorial intent — what the author is primarily doing. The model learned surface patterns instead, and the gap between those two things explains most of the error.

**What the model likely captured:** Post length correlates loosely with Analytical; the model fires Analytical confidently on any detailed, multi-sentence explanation regardless of whether an argument is being made. Explicit question structures loosely associate with Informational, but the model struggles when explanatory comments don't contain questions. Superlatives and comparisons ("best", "SO close to their goals") consistently push predictions toward Evaluative.

**What it missed:** The core Informational/Analytical distinction is defined by whether a claim is being defended — a distinction that requires understanding discourse intent, not just matching vocabulary patterns. DistilBERT cannot reliably make this call from token sequences alone. The model also has no frame for internet/meme register: phrases like "that's my roman empire" or "vocal stim" carry meaning only within fandom internet culture, and the model misreads their syntax as Evaluative or Analytical.

**What the model overfit to:** The main learned shortcut appears to be: "does this text describe something in detail?" → Analytical. This collapses the Informational/Analytical boundary in a way that superficially resembles correct behavior but misses the taxonomy's core distinction. A model that understood the task would classify a thorough factual explanation as Informational; this model classifies it as Analytical because length and evidence-citing are the features it has access to.

**The underlying ceiling:** The project's definition-of-success metric was macro F1 ≥ 0.72. Reaching that on 261 training examples with a 110M-parameter model was ambitious for a 4-class task where two of the class boundaries (Analytical/Informational, Reactive/Evaluative) are defined by authorial intent that isn't reliably signaled by surface text. A realistic path to improvement would require either substantially more training data, a stronger pretrained encoder, or a collapsed 3-class taxonomy that merges Informational into Analytical (as the planning document anticipated as a possible remediation).

---

## Spec Reflection

**One way the spec helped:** The seeding strategy for each label — scraping by flair, keyword, and post length — prevented the class imbalance problem the planning document predicted. Reactive ended up at 38% of training data, which is dominant but workable. Without deliberate seeding, a raw Discussion/Question scrape would have been closer to 60–70% Reactive, making the other classes too sparse to train on.

**One way implementation diverged:** The planning document specified measuring Cohen's Kappa on a 50-post overlap sample before training, with Kappa ≥ 0.65 required to proceed. This inter-annotator agreement check was not completed — annotation was done by a single annotator. This is a meaningful gap. Without Kappa, it is impossible to know how much of the Informational/Analytical confusion comes from model failure versus annotation inconsistency. Looking at the error cases, several posts labeled Informational (e.g., the Eren cave scene explanation in Case 3 of the error analysis) read as Analytical under a reasonable application of the definitions. A second annotator would have forced that ambiguity to surface and be resolved before training, either sharpening the boundary or flagging these as inherently unlabelable. The spec's warning — "a classifier can't exceed the reliability of its labels" — turned out to be the most relevant sentence in the planning document.

---

## AI Usage

**Instance 1 — Hyperparameter debugging**

After the fine-tuned model underperformed the baseline, I pasted the training configuration into Claude Code and asked it to identify configuration problems. Claude identified that `warmup_steps=0.1` was a bug — the argument expects an integer and `0.1` silently casts to `0`, meaning the model trained with no learning rate warmup at all. It also flagged 12 epochs as high for 261 training examples given the risk of overfitting. I verified the `warmup_steps` type constraint in the Hugging Face TrainingArguments documentation before accepting the fix, and computed warmup as 10% of total training steps using an explicit integer formula rather than the deprecated `warmup_ratio` parameter.

**Instance 2 — Wrong prediction pattern analysis**

I pasted all 25 wrong predictions into Claude Code and asked it to identify recurring themes. Claude surfaced three clusters: Informational posts with detailed explanatory content predicted as Analytical, Reactive posts using internet/meme phrases predicted as Evaluative, and degenerate low-content inputs defaulting to the plurality class. I verified each cluster by re-reading the examples myself before including them in this analysis. Claude initially suggested post length as a fourth factor; I discarded this after checking — the Informational/Analytical errors span a range of lengths and the pattern doesn't hold consistently. The meme-register pattern was the most useful find: it wasn't visible when reviewing cases one at a time and only emerged as a pattern when the full list was analyzed together.

**Instance 3 — README drafting**

Claude Code was used to draft sections of this README, including the Error Analysis cases, the Configuration Changes section, and structural framing for the evaluation report. I provided the context (wrong predictions, confusion matrix, default vs. actual hyperparameters) and reviewed the output. The error analysis cases were revised to strengthen the "what would fix it" framing, which the initial drafts underemphasized. The Reflection section was written from scratch based on my own reading of the error patterns; Claude's drafts for that section were generic and were discarded.

---

## Configuration Changes

The following parameters were changed from the starter defaults.

**`num_train_epochs`: 3 → 12**

More epochs give the model more exposure to the training data, which matters when the dataset is small (261 examples). With `load_best_model_at_end=True` and per-epoch evaluation, the trainer restores the checkpoint with the best validation accuracy, so additional epochs don't risk degrading the final model — they just extend the search window.

**`learning_rate`: 2e-5 → 5e-5**

A slightly higher learning rate was used to speed up convergence on the small training set. The standard 2e-5 recommendation targets larger fine-tuning runs; with only ~17 steps per epoch, the optimizer needs a larger step size to make meaningful progress early in training.

**`weight_decay`: 0.01 → 0.15**

Increased to add stronger L2 regularization and reduce overfitting risk from training for 12 epochs on a small dataset.

**`warmup_steps`: 50 → computed as 10% of total steps**

The default `warmup_steps=50` is poorly matched to this dataset. With 261 examples, a batch size of 16, and 3 epochs, total training steps are only ~51 — meaning the warmup phase would cover nearly the entire run, and the learning rate would never stabilize. The fix computes warmup proportionally:

```python
import math
steps_per_epoch = math.ceil(len(train_df) / 16)
total_steps = steps_per_epoch * num_train_epochs
warmup_steps = int(0.1 * total_steps)
```

This keeps warmup at ~10% of training regardless of dataset size or epoch count, which is the conventional ratio for BERT-family fine-tuning.
