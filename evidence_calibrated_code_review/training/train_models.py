"""Train/evaluate code defect and NVD CWE classifiers; save only measured artifacts."""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.dummy import DummyClassifier
from sklearn.metrics import (accuracy_score, average_precision_score, classification_report,
                             confusion_matrix, f1_score, precision_score, recall_score,
                             roc_auc_score, brier_score_loss)
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.pipeline import FeatureUnion

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.ml.calibration import ProbabilityCalibrator, entropy_uncertainty, expected_calibration_error
from app.ml.dataset_loader import clean_code_records, clean_cve_records, load_jsonl

OUT = ROOT / "trained_models"


def code_train(path):
    rows = clean_code_records(load_jsonl(path))
    if len(rows) < 100 or len({r["label"] for r in rows}) < 2:
        raise ValueError("Need at least 100 usable Devign samples with both labels.")
    texts = [r["code"] for r in rows]
    y = np.asarray([r["label"] for r in rows])
    groups = np.asarray([r["group"] for r in rows])
    group_count = len(np.unique(groups))
    if group_count >= 2:
        # With the two repositories in this Devign release, reserve one full
        # repository for testing and split the remaining repository into train
        # and validation. Three-way repository isolation is mathematically
        # impossible with only two groups.
        outer_size = .2 if group_count >= 3 else .5
        outer = GroupShuffleSplit(n_splits=1, test_size=outer_size, random_state=42)
        train_val, test = next(outer.split(texts, y, groups))
        train_groups = len(np.unique(groups[train_val]))
    else:
        train_val, test = train_test_split(np.arange(len(rows)), test_size=.2, random_state=42, stratify=y)
        train_groups = 1
    if train_groups >= 2:
        inner = GroupShuffleSplit(n_splits=1, test_size=.125, random_state=43)
        tr_rel, va_rel = next(inner.split([texts[i] for i in train_val], y[train_val], groups[train_val]))
        train, val = train_val[tr_rel], train_val[va_rel]
        split_description = "repository-grouped train/validation/test" if group_count >= 3 else "one repository held out for test; validation split within remaining repository because only two projects exist"
    else:
        train, val = train_test_split(train_val, test_size=.125, random_state=43, stratify=y[train_val])
        split_description = ("one repository held out for test; stratified validation split within the remaining repository because only two projects exist"
                             if group_count == 2 else
                             "stratified sample split; repository holdout unavailable because only one project group exists")
    vectorizer = FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), max_features=120000, sublinear_tf=True, token_pattern=r"(?u)\b\w+\b")),
        ("char", TfidfVectorizer(analyzer="char", ngram_range=(3, 5), max_features=100000, min_df=2, sublinear_tf=True)),
    ])
    xtr = vectorizer.fit_transform([texts[i] for i in train])
    model = LogisticRegression(class_weight="balanced", max_iter=1200, random_state=42, solver="liblinear")
    model.fit(xtr, y[train])
    val_scores = model.decision_function(vectorizer.transform([texts[i] for i in val]))
    calibrator = ProbabilityCalibrator().fit(val_scores, y[val])
    test_scores = model.decision_function(vectorizer.transform([texts[i] for i in test]))
    p = calibrator.predict(test_scores)
    pred = (p >= .5).astype(int)
    metrics = measured_metrics(y[test], pred, p)
    majority = DummyClassifier(strategy="prior").fit(np.zeros((len(train), 1)), y[train])
    baseline_pred = majority.predict(np.zeros((len(test), 1)))
    baseline_prob = majority.predict_proba(np.zeros((len(test), 1)))[:, 1]
    metrics.update({"dataset": "CodeXGLUE Devign", "language": "C/C++", "model": "TF-IDF word+character ngrams + LogisticRegression",
                    "majority_class_baseline": measured_metrics(y[test], baseline_pred, baseline_prob),
                    "calibration": calibrator.method, "calibration_comparison": calibrator.comparison,
                    "samples_after_cleaning": len(rows), "class_distribution": dict(Counter(map(int, y))),
                    "project_groups": group_count, "split": split_description + "; seed 42",
                    "reliability_bins": reliability_bins(y[test], p)})
    out = OUT / "code"; out.mkdir(parents=True, exist_ok=True)
    joblib.dump({"vectorizer": vectorizer, "classifier": model, "calibrator": calibrator, "version": "1.0"}, out / "model.joblib")
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


def measured_metrics(y, pred, p):
    return {"accuracy": float(accuracy_score(y, pred)), "precision": float(precision_score(y, pred, zero_division=0)),
            "recall": float(recall_score(y, pred, zero_division=0)), "f1": float(f1_score(y, pred, zero_division=0)),
            "roc_auc": float(roc_auc_score(y, p)), "pr_auc": float(average_precision_score(y, p)),
            "brier_score": float(brier_score_loss(y, p)), "ece": expected_calibration_error(y, p),
            "confusion_matrix": confusion_matrix(y, pred).tolist()}


def reliability_bins(y, p, bins=10):
    result = []
    for i in range(bins):
        mask = (p >= i / bins) & (p < (i + 1) / bins)
        if mask.any():
            result.append({"count": int(mask.sum()), "mean_confidence": float(p[mask].mean()), "fraction_positive": float(np.asarray(y)[mask].mean())})
    return result


def nlp_train(paths):
    raw = []
    for path in paths:
        raw.extend(load_jsonl(path))
    rows = clean_cve_records(raw)
    counts = Counter(r["label"] for r in rows)
    supported = {label for label, count in counts.most_common(25) if count >= 50}
    rows = [r for r in rows if r["label"] in supported]
    labels = [r["label"] for r in rows]
    if len(rows) < 100 or len(set(labels)) < 2:
        raise ValueError("NVD corpus has too few valid, repeated CWE labels; prepare more years before training.")
    texts = [r["text"] for r in rows]
    x_trainval, x_test, y_trainval, y_test = train_test_split(texts, labels, test_size=.2, random_state=42, stratify=labels)
    x_train, x_val, y_train, y_val = train_test_split(x_trainval, y_trainval, test_size=.125, random_state=43, stratify=y_trainval)
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=150000, sublinear_tf=True, stop_words="english", min_df=2)
    model = LogisticRegression(class_weight="balanced", max_iter=1200, random_state=42, solver="lbfgs")
    model.fit(vectorizer.fit_transform(x_train), y_train)
    probs = model.predict_proba(vectorizer.transform(x_test))
    pred = model.classes_[probs.argmax(axis=1)]
    metrics = {"dataset": "NVD CVE descriptions with NVD assigned CWE", "model": "TF-IDF + LogisticRegression",
               "samples_after_cleaning": len(rows), "class_distribution": dict(Counter(labels)),
               "supported_cwe_labels": list(map(str, model.classes_)), "split": "stratified 70/10/20; seed 42",
               "accuracy": float(accuracy_score(y_test, pred)), "macro_f1": float(f1_score(y_test, pred, average="macro")),
               "weighted_f1": float(f1_score(y_test, pred, average="weighted")),
               "classification_report": classification_report(y_test, pred, output_dict=True, zero_division=0),
               "calibration_note": "Multiclass probabilities are raw classifier probabilities; not presented as calibrated."}
    out = OUT / "nlp"; out.mkdir(parents=True, exist_ok=True)
    joblib.dump({"vectorizer": vectorizer, "classifier": model, "version": "1.0"}, out / "model.joblib")
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", type=Path, help="Processed Devign jsonl")
    parser.add_argument("--nvd", type=Path, nargs="+", help="Processed NVD CWE jsonl files")
    args = parser.parse_args()
    if args.code:
        code_train(args.code)
    if args.nvd:
        nlp_train(args.nvd)
    if not args.code and not args.nvd:
        parser.error("Provide --code and/or --nvd.")
