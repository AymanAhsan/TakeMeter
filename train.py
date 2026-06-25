"""
TakeMeter — discourse classifier fine-tuning harness.
5-fold stratified CV across four encoder candidates and three learning rates.
Primary metric: macro-F1 (mean ± std across folds).

Usage:
    python train.py                              # full bake-off (all models × all LRs)
    python train.py --model deberta-v3-base      # single model, all LRs
    python train.py --model roberta-base --lr 2e-5  # single run
    python train.py --quick                      # 1 fold, roberta-base, 2e-5 (pipeline smoke-test)
"""

import argparse
import json
import os
import random
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold
from sklearn.utils.class_weight import compute_class_weight

import torch
from datasets import Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    EarlyStoppingCallback,
    Trainer,
    TrainingArguments,
)

warnings.filterwarnings("ignore", category=FutureWarning)
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# ─── Config ───────────────────────────────────────────────────────────────────

LABEL2ID = {"Analytical": 0, "Evaluative": 1, "Informational": 2, "Reactive": 3}
ID2LABEL = {v: k for k, v in LABEL2ID.items()}
NUM_LABELS = len(LABEL2ID)

MODELS = {
    "deberta-v3-base": "microsoft/deberta-v3-base",
    "ModernBERT-base": "answerdotai/ModernBERT-base",
    "roberta-base": "roberta-base",
    "distilbert-base": "distilbert-base-uncased",
}

LR_GRID = [1e-5, 2e-5, 3e-5]
N_FOLDS = 5
SEED = 42
MAX_LEN = 256
BATCH_SIZE = 16
MAX_EPOCHS = 10
PATIENCE = 3
RESULTS_FILE = "cv_results.json"

# ─── Reproducibility ──────────────────────────────────────────────────────────

def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# ─── Data ─────────────────────────────────────────────────────────────────────

def build_input_text(row: pd.Series) -> str:
    type_tag = "[POST]" if row["type"] == "post" else "[COMMENT]"
    return f"{type_tag} {row['post_title']}\n{row['text']}"


def load_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df = df[df["label"].notna() & (df["label"].str.strip() != "")].copy()
    df["input_text"] = df.apply(build_input_text, axis=1)
    df["label_id"] = df["label"].map(LABEL2ID)
    return df.reset_index(drop=True)


def make_hf_dataset(texts: list, label_ids: list, tokenizer, max_length: int) -> Dataset:
    ds = Dataset.from_dict({"input_text": texts, "labels": label_ids})

    def tokenize(batch):
        return tokenizer(
            batch["input_text"],
            truncation=True,
            max_length=max_length,
            padding="max_length",
        )

    ds = ds.map(tokenize, batched=True, remove_columns=["input_text"])
    ds.set_format("torch")
    return ds


# ─── Weighted loss Trainer ────────────────────────────────────────────────────

class WeightedTrainer(Trainer):
    def __init__(self, class_weights: torch.Tensor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.class_weights = class_weights

    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        loss = torch.nn.CrossEntropyLoss(
            weight=self.class_weights.to(outputs.logits.device)
        )(outputs.logits, labels)
        return (loss, outputs) if return_outputs else loss


# ─── Metrics ─────────────────────────────────────────────────────────────────

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {"macro_f1": f1_score(labels, preds, average="macro", zero_division=0)}


# ─── Single fold ─────────────────────────────────────────────────────────────

def train_fold(
    model_hf_id: str,
    lr: float,
    fold_idx: int,
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    class_weights: torch.Tensor,
    out_dir: str,
) -> dict:
    tokenizer = AutoTokenizer.from_pretrained(model_hf_id)

    train_ds = make_hf_dataset(
        train_df["input_text"].tolist(), train_df["label_id"].tolist(), tokenizer, MAX_LEN
    )
    val_ds = make_hf_dataset(
        val_df["input_text"].tolist(), val_df["label_id"].tolist(), tokenizer, MAX_LEN
    )

    model = AutoModelForSequenceClassification.from_pretrained(
        model_hf_id,
        num_labels=NUM_LABELS,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        ignore_mismatched_sizes=True,
    )

    steps_per_epoch = max(1, len(train_ds) // BATCH_SIZE)
    warmup_steps = max(1, int(0.1 * steps_per_epoch * MAX_EPOCHS))

    args = TrainingArguments(
        output_dir=out_dir,
        num_train_epochs=MAX_EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE,
        learning_rate=lr,
        warmup_steps=warmup_steps,
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=1,
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        greater_is_better=True,
        seed=SEED,
        report_to="none",
        logging_steps=50,
        fp16=torch.cuda.is_available(),
    )

    trainer = WeightedTrainer(
        class_weights=class_weights,
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=PATIENCE)],
    )

    trainer.train()

    pred_out = trainer.predict(val_ds)
    preds = np.argmax(pred_out.predictions, axis=-1)
    true = pred_out.label_ids

    macro_f1 = f1_score(true, preds, average="macro", zero_division=0)
    per_class_f1 = f1_score(true, preds, average=None, zero_division=0)
    report = classification_report(
        true, preds, target_names=list(LABEL2ID.keys()), output_dict=True, zero_division=0
    )
    cm = confusion_matrix(true, preds).tolist()

    print(f"  Fold {fold_idx + 1} macro-F1: {macro_f1:.4f}")
    print(classification_report(true, preds, target_names=list(LABEL2ID.keys()), zero_division=0))

    return {
        "fold": fold_idx,
        "macro_f1": macro_f1,
        "per_class_f1": {k: float(per_class_f1[v]) for k, v in LABEL2ID.items()},
        "report": report,
        "confusion_matrix": cm,
    }


# ─── CV loop ─────────────────────────────────────────────────────────────────

def run_cv(model_name: str, model_hf_id: str, lr: float, df: pd.DataFrame, n_folds: int) -> dict:
    set_seed(SEED)
    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=SEED)

    class_weights = torch.tensor(
        compute_class_weight(
            "balanced", classes=np.arange(NUM_LABELS), y=df["label_id"].values
        ),
        dtype=torch.float32,
    )

    fold_results = []
    for fold_idx, (train_idx, val_idx) in enumerate(skf.split(df, df["label_id"])):
        print(f"\n{'='*65}")
        print(f"  {model_name}  |  lr={lr:.0e}  |  fold {fold_idx + 1}/{n_folds}")
        print(f"{'='*65}")
        result = train_fold(
            model_hf_id,
            lr,
            fold_idx,
            df.iloc[train_idx].reset_index(drop=True),
            df.iloc[val_idx].reset_index(drop=True),
            class_weights,
            out_dir=f"checkpoints/{model_name}_lr{lr:.0e}_fold{fold_idx}",
        )
        fold_results.append(result)

    macro_f1s = [r["macro_f1"] for r in fold_results]
    mean, std = float(np.mean(macro_f1s)), float(np.std(macro_f1s))
    print(f"\n>>> {model_name}  lr={lr:.0e}  macro-F1 = {mean:.4f} ± {std:.4f}")

    return {
        "model": model_name,
        "lr": lr,
        "mean_macro_f1": mean,
        "std_macro_f1": std,
        "folds": fold_results,
    }


# ─── Entry point ─────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--model", choices=list(MODELS.keys()), help="Run only this model")
    p.add_argument("--lr", type=float, choices=LR_GRID, help="Run only this learning rate")
    p.add_argument("--quick", action="store_true",
                   help="Smoke-test: 1 fold, roberta-base, lr=2e-5")
    return p.parse_args()


def main():
    args = parse_args()
    set_seed(SEED)

    df = load_data("data/dataset.csv")
    print(f"\nLoaded {len(df)} examples")
    print(df["label"].value_counts().to_string())

    if args.quick:
        model_filter, lr_filter, n_folds = "roberta-base", 2e-5, 1
    else:
        model_filter = args.model
        lr_filter = args.lr
        n_folds = N_FOLDS

    results = []
    for model_name, model_hf_id in MODELS.items():
        if model_filter and model_name != model_filter:
            continue
        for lr in LR_GRID:
            if lr_filter and abs(lr - lr_filter) > 1e-10:
                continue
            result = run_cv(model_name, model_hf_id, lr, df, n_folds)
            results.append(result)
            with open(RESULTS_FILE, "w") as f:
                json.dump(results, f, indent=2)

    if len(results) > 1:
        print("\n" + "=" * 65)
        print("LEADERBOARD")
        print("=" * 65)
        for r in sorted(results, key=lambda x: x["mean_macro_f1"], reverse=True):
            print(f"  {r['model']:30s}  lr={r['lr']:.0e}  "
                  f"macro-F1 = {r['mean_macro_f1']:.4f} ± {r['std_macro_f1']:.4f}")

    print(f"\nResults saved → {RESULTS_FILE}")


if __name__ == "__main__":
    main()
