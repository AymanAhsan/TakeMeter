# TakeMeter — Project Planning

## Community

The Anime community, specifically the subreddits **r/attackontitan** and **r/HunterXHunter**, is the target for this project.

### r/attackontitan

Attack on Titan is chosen over a general anime subreddit because the community has a well-defined, complete canon — the manga is finished and the anime adaptation has concluded. This is important for a classifier because it eliminates a major confound: posts aren't split between "speculation" and "analysis" modes depending on where the story currently is. Every post is operating on the same closed text.

The community is also unusually argumentative in a *productive* way. The ending is genuinely divisive, the adaptation choices (especially the final season's studio switch) generated real critical discourse, and the thematic content — genocide, cycles of violence, determinism — attracts posts that go beyond surface-level reaction. This means the label space will be well-populated: you'll find real analytical posts, not just hype and memes. A subreddit for a lighter show would skew so heavily toward Reactive that the other classes would be underrepresented.

Finally, the community is large enough (~700k members) to provide 200+ labelable posts without scraping edge cases, but not so large (like r/anime) that the signal drowns in noise.

### r/HunterXHunter

Hunter x Hunter complements AOT as a second source for several reasons. Like AOT, it has a closed anime adaptation — the 2011 series is finished and covers the full Chimera Ant and Election arcs, giving the community a complete text to reason about. Posts are not muddied by release-day hype cycles tied to ongoing episodes.

The community's discourse profile is meaningfully different from AOT's, which improves classifier generalization. HxH debates tend to cluster around structural and thematic depth — the Chimera Ant arc's pacing, Gon's moral arc, Meruem's character — rather than adaptation controversy. This populates the Analytical and Informational classes through a different rhetorical register than AOT, making the training data more diverse.

The subreddit (~400k members) is large enough to supply sufficient labelable posts but small enough that lower-quality content hasn't diluted the discussion threads to noise.

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

**Source:** Reddit posts from r/attackontitan scraped via the Pushshift API or the official Reddit API (`praw`). Target post text only (title + selftext); exclude pure image/video posts with no text body.

**Volume:** 373 posts from the Discussion/Question and Ending Spoilers - Discussion/Question flairs, which are the most likely to contain Analytical and Informational content. This is a manageable size for manual annotation while providing enough data for initial model training and evaluation.

**Seeding strategy per label:**

| Label | Search/filter strategy |
|---|---|
| Analytical | Flair: "Analysis/Theory" posts; long-form posts (>300 words) |
| Evaluative | Flair: "Discussion"; posts containing "best", "worst", "overrated", "hot take" |
| Informational | Posts ending in "?"; flair: "Question" |
| Reactive | Short posts (<100 words); posts within 24h of episode/chapter release dates |

**If a label is underrepresented after 200 examples:**

The most likely underrepresented label is Informational — many question posts are deleted or answered in comments rather than becoming standalone posts. Remediation options in priority order:
1. Scrape comment threads, not just top-level posts — Informational discourse happens there.
2. Lower the minimum word count threshold for Informational only.
3. If still underrepresented at <15% of the dataset, consider merging Informational into Analytical (questions seeking interpretation) and Reactive (questions seeking validation), and redefining the taxonomy as 3 labels before annotation is complete.

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
