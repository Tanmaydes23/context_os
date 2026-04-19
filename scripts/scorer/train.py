"""
Trains MLP + XGBoost importance scorers on data_gen/scored_dataset.jsonl.
Saves trained models to scorer/artifacts/.

Usage:
    python scorer/train.py

Outputs:
    scorer/artifacts/mlp_model.pt
    scorer/artifacts/xgb_model.json
    scorer/artifacts/embedder_cache.pkl
    scorer/artifacts/training_stats.json
"""

import json
import pickle
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, classification_report
from tqdm import tqdm
import xgboost as xgb

from scorer.model import ImportanceMLP

DATASET_PATH = Path("data_gen/scored_dataset.jsonl")
ARTIFACTS_DIR = Path("scorer/artifacts")
ARTIFACTS_DIR.mkdir(exist_ok=True)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
BATCH_SIZE = 256
EPOCHS = 30
LR = 1e-3
TEST_SIZE = 0.2
RANDOM_SEED = 42

VALIDATION_CASES = [
    ("I react badly to anything from the sea", 1),
    ("shellfish makes me really sick", 1),
    ("I can't do anything from the ocean", 1),
    ("no raw fish please, it upsets my stomach", 1),
    ("I'm sensitive to seafood in general", 1),
    ("my budget is around $2,500 total", 1),
    ("I have a client meeting Wednesday at 2pm near the Eiffel Tower", 1),
    ("I prefer a relaxing pace, max 2 activities per day", 1),
    ("That sounds great!", 0),
    ("The hotel has a rooftop pool and spa", 0),
    ("Sure, let me look into that for you", 0),
    ("Okay, I'll check availability right away", 0),
    ("The flight departs at 09:15 from Terminal 2", 0),
]


def load_dataset():
    print(f"\n[1/6] Loading dataset from {DATASET_PATH}...")
    rows = []
    with open(DATASET_PATH) as f:
        for line in f:
            try:
                rows.append(json.loads(line.strip()))
            except Exception:
                continue
    print(f"  Loaded {len(rows):,} rows")
    label1 = sum(1 for r in rows if r["label"] == 1.0)
    print(f"  Label=1: {label1:,} ({100*label1//len(rows)}%)  Label=0: {len(rows)-label1:,}")
    return rows


def build_features(rows):
    print("\n[2/6] Building MiniLM embeddings...")
    print(f"  Device: {DEVICE}")

    from sentence_transformers import SentenceTransformer
    embedder = SentenceTransformer("all-MiniLM-L6-v2", device=str(DEVICE))

    cache_path = ARTIFACTS_DIR / "embedder_cache.pkl"
    if cache_path.exists():
        print("  Loading cached embeddings...")
        with open(cache_path, "rb") as f:
            cache = pickle.load(f)
    else:
        cache = {}

    sentences    = [r["sentence"]                    for r in rows]
    contexts     = [r.get("context", "")[:400]       for r in rows]
    queries      = [r.get("future_query", "")[:300]  for r in rows]
    turn_numbers = [r.get("turn_number", 0)          for r in rows]

    def get_embeddings(texts, label):
        unique = list(set(t for t in texts if t not in cache))
        if unique:
            print(f"  Embedding {len(unique)} unique {label} texts...")
            batch_size = 512
            for i in tqdm(range(0, len(unique), batch_size), desc=f"  {label}"):
                batch = unique[i:i+batch_size]
                embs = embedder.encode(batch, convert_to_numpy=True,
                                       show_progress_bar=False)
                for t, e in zip(batch, embs):
                    cache[t] = e
        return np.array([cache[t] for t in texts])

    sent_embs = get_embeddings(sentences, "sentences")
    ctx_embs  = get_embeddings(contexts,  "contexts")
    qry_embs  = get_embeddings(queries,   "queries")

    max_turn = max(turn_numbers) if turn_numbers else 1
    turn_norm = np.array(turn_numbers, dtype=np.float32) / max(max_turn, 1)

    features = np.concatenate([
        sent_embs,
        ctx_embs,
        qry_embs,
        turn_norm.reshape(-1, 1),
        np.zeros((len(rows), 1), dtype=np.float32),
    ], axis=1).astype(np.float32)

    print(f"  Feature matrix: {features.shape}")

    with open(cache_path, "wb") as f:
        pickle.dump(cache, f)
    print("  Cache saved.")

    labels = np.array([r["label"] for r in rows], dtype=np.float32)
    return features, labels, embedder, cache


def train_mlp(X_train, y_train, X_val, y_val):
    print("\n[3/6] Training MLP...")
    print(f"  Train: {len(X_train):,}  Val: {len(X_val):,}  Device: {DEVICE}")

    X_tr = torch.tensor(X_train).to(DEVICE)
    y_tr = torch.tensor(y_train).to(DEVICE)
    X_vl = torch.tensor(X_val).to(DEVICE)
    y_vl = torch.tensor(y_val).to(DEVICE)

    dataset = TensorDataset(X_tr, y_tr)
    loader  = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)

    pos_weight = torch.tensor([(y_train == 0).sum() / max((y_train == 1).sum(), 1)]).to(DEVICE)
    model     = ImportanceMLP(input_dim=X_train.shape[1]).to(DEVICE)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    criterion = nn.BCELoss()
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=3, factor=0.5)

    best_auc   = 0.0
    best_state = None

    for epoch in range(1, EPOCHS + 1):
        model.train()
        total_loss = 0.0
        for xb, yb in loader:
            optimizer.zero_grad()
            preds = model(xb)
            loss  = criterion(preds, yb)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        model.eval()
        with torch.no_grad():
            val_preds = model(X_vl).cpu().numpy()
        auc = roc_auc_score(y_val, val_preds)
        scheduler.step(1 - auc)

        if auc > best_auc:
            best_auc   = auc
            best_state = {k: v.clone() for k, v in model.state_dict().items()}

        if epoch % 5 == 0 or epoch == 1:
            print(f"  Epoch {epoch:02d}/{EPOCHS}  loss={total_loss/len(loader):.4f}  val_auc={auc:.4f}  best={best_auc:.4f}")

    model.load_state_dict(best_state)
    mlp_path = ARTIFACTS_DIR / "mlp_model.pt"
    torch.save({"model_state": best_state, "input_dim": X_train.shape[1]}, mlp_path)
    print(f"  Best val AUC: {best_auc:.4f}")
    print(f"  Saved to {mlp_path}")
    return model, best_auc


def train_xgboost(X_train, y_train, X_val, y_val):
    print("\n[4/6] Training XGBoost...")

    scale_pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
    model = xgb.XGBClassifier(
        n_estimators=500,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        eval_metric="auc",
        early_stopping_rounds=20,
        random_state=RANDOM_SEED,
        device="cuda",
        verbosity=1,
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=50,
    )

    xgb_path = ARTIFACTS_DIR / "xgb_model.json"
    model.save_model(xgb_path)

    val_preds = model.predict_proba(X_val)[:, 1]
    auc = roc_auc_score(y_val, val_preds)
    print(f"  XGBoost val AUC: {auc:.4f}")
    print(f"  Saved to {xgb_path}")
    return model, auc


def run_test_k(mlp_model, xgb_model, embedder, cache):
    print("\n[5/6] Running Test K validation sentences...")
    print("  (These are the judge demo sentences — all must pass)\n")

    def score_sentence(sentence):
        if sentence not in cache:
            emb = embedder.encode([sentence], convert_to_numpy=True)[0]
            cache[sentence] = emb
        else:
            emb = cache[sentence]

        empty = embedder.encode([""], convert_to_numpy=True)[0]
        features = np.concatenate([emb, empty, empty,
                                    np.array([0.0]), np.array([0.0])]).astype(np.float32)
        features = features.reshape(1, -1)

        mlp_model.eval()
        with torch.no_grad():
            x = torch.tensor(features).to(DEVICE)
            mlp_score = mlp_model(x).item()

        xgb_score = xgb_model.predict_proba(features)[0][1]
        ensemble_score = 0.6 * mlp_score + 0.4 * xgb_score
        return mlp_score, xgb_score, ensemble_score

    sep = "-" * 70
    print(f"  {'RESULT':<6} {'EXP':>3}  {'MLP':>5}  {'XGB':>5}  {'ENS':>5}  SENTENCE")
    print(f"  {sep}")

    passed = 0
    failed = 0
    failures = []

    for sentence, expected in VALIDATION_CASES:
        mlp_s, xgb_s, ens_s = score_sentence(sentence)
        threshold = 0.75 if expected == 1 else 0.25

        if expected == 1:
            ok = ens_s >= threshold
        else:
            ok = ens_s <= threshold

        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
            failures.append((sentence, expected, ens_s))

        short = sentence[:48] + ".." if len(sentence) > 50 else sentence
        print(f"  [{status}] exp={expected}  mlp={mlp_s:.2f}  xgb={xgb_s:.2f}  ens={ens_s:.2f}  '{short}'")

    print(f"\n  Test K: {passed}/{len(VALIDATION_CASES)} passed")

    if failures:
        print("\n  FAILURES:")
        for s, e, sc in failures:
            print(f"    expected={e} got={sc:.2f}  '{s}'")
    else:
        print("  All validation sentences passed.")

    return passed, failed


def save_stats(mlp_auc, xgb_auc, passed, failed, elapsed):
    stats = {
        "mlp_val_auc": round(mlp_auc, 4),
        "xgb_val_auc": round(xgb_auc, 4),
        "ensemble_strategy": "0.6 * MLP + 0.4 * XGBoost",
        "test_k_passed": passed,
        "test_k_failed": failed,
        "test_k_total": passed + failed,
        "training_time_minutes": round(elapsed / 60, 1),
        "device": str(DEVICE),
    }
    path = ARTIFACTS_DIR / "training_stats.json"
    with open(path, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"\n  Stats saved to {path}")
    return stats


def main():
    t0 = time.time()

    print("=" * 60)
    print("  CONTEXTOS — IMPORTANCE SCORER TRAINING")
    print("=" * 60)
    print(f"  Device: {DEVICE}")
    print(f"  Epochs: {EPOCHS}  Batch: {BATCH_SIZE}  LR: {LR}")

    rows = load_dataset()
    features, labels, embedder, cache = build_features(rows)

    X_train, X_val, y_train, y_val = train_test_split(
        features, labels,
        test_size=TEST_SIZE,
        random_state=RANDOM_SEED,
        stratify=labels,
    )
    print(f"\n  Train: {len(X_train):,}  Val: {len(X_val):,}")

    mlp_model, mlp_auc = train_mlp(X_train, y_train, X_val, y_val)
    xgb_model, xgb_auc = train_xgboost(X_train, y_train, X_val, y_val)

    passed, failed = run_test_k(mlp_model, xgb_model, embedder, cache)

    elapsed = time.time() - t0
    stats = save_stats(mlp_auc, xgb_auc, passed, failed, elapsed)

    print("\n" + "=" * 60)
    print("  TRAINING COMPLETE")
    print("=" * 60)
    print(f"  MLP AUC:      {mlp_auc:.4f}")
    print(f"  XGBoost AUC:  {xgb_auc:.4f}")
    print(f"  Test K:       {passed}/{passed+failed} passed")
    print(f"  Time:         {elapsed/60:.1f} minutes")
    print(f"\n  Models saved to scorer/artifacts/")
    print("  Run scorer/validate.py to see SHAP feature importance.")


if __name__ == "__main__":
    main()
