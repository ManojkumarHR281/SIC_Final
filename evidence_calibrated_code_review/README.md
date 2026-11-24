# Evidence-Calibrated Code Review

A local-first Flask application that combines the existing AST/static review features with optional, locally trained machine-learning classifiers. Submitted code is treated as data and is never executed. The application stores a source digest and finding snippets by default; retaining complete source requires selecting the explicit opt-in on the review form.

## Current model status

The repository contains reproducible real-data preparation and training pipelines, but model weights and datasets are not checked in. On a fresh install, the UI and API report **Model not trained** until datasets are downloaded and the commands below complete. No accuracy or training result is fabricated.

The implemented model architecture is a transparent scikit-learn baseline:

- **Code classifier:** TF-IDF word and character n-grams with class-weighted logistic regression, trained on the CodeXGLUE Devign defect-detection corpus. Devign examples are C/C++ functions and have binary vulnerable/defective labels; this model does not predict a CWE. Inference is limited to C/C++.
- **Description classifier:** TF-IDF word n-grams with class-weighted logistic regression, trained on English NVD CVE descriptions paired with CWE labels assigned in NVD records. The pipeline reports the most common 25 CWE labels with at least 50 examples in the downloaded training data. The labels it actually retained are recorded in its metrics file.
- **Code calibration:** Platt scaling and isotonic regression are fit on held-out validation data; the one with lower validation Brier score is selected. Test reporting includes Brier score, ECE, reliability bins, precision, recall, F1, ROC-AUC, PR-AUC and a confusion matrix. Predictive uncertainty is normalized binary predictive entropy. Out-of-language code is explicitly unsupported.
- The published Devign file has only two repository groups. Training holds one repository out for testing and takes validation samples from the remaining repository. If held-out ROC-AUC is below 0.60, code inference explicitly abstains as uncertain and raises uncertainty; it does not report a vulnerable/non-vulnerable decision.
- **NLP probabilities:** The text classifier currently reports raw class scores and explicitly marks them uncalibrated. A local explanation template reports model provenance and cites only source text available to it; it does not claim that a binary model identified a causal flaw or CWE.

AST and existing static checks remain useful for language-aware structure, code quality and line evidence. When a trained Devign model is available for C/C++, it replaces the existing security-rule classification for that review; the other existing analyzers remain active. For other languages, existing static checks still run and are labeled heuristic. These existing findings' confidence values remain heuristic until enough reviewed outcomes are available for calibration.

## Dataset sources, attribution, and limitations

| Corpus | Source | Language/labels | License and caveat |
| --- | --- | --- | --- |
| Devign defect detection via CodeXGLUE | [CodeXGLUE](https://github.com/microsoft/CodeXGLUE), Hugging Face dataset `google/code_x_glue_cc_defect_detection` | C/C++ function text; binary `target`; project and commit fields support group splits | The dataset metadata currently has no declared license. Preserve the upstream citation and review the upstream terms before redistribution. The model is not a Python vulnerability detector. |
| CVE descriptions and CWE labels | [NVD Vulnerabilities API 2.0](https://nvd.nist.gov/developers/vulnerabilities) | English vulnerability description paired with NVD-assigned CWE | NVD records are public U.S. government data; CVE records and third-party CNA content can have separate terms. Preserve CVE IDs and NVD attribution. CWE labels can be absent or incomplete. |

Preparation removes missing/short/binary-like code, invalid labels, exact normalized duplicates, and near-duplicates found by a 64-bit token-shingle SimHash distance of at most 3. Code train/validation/test partitions are grouped by project to reduce repository leakage. NVD rows are deduplicated by CVE ID and text/CWE, rows without usable CWE labels are removed, and rare labels are omitted from the supported classifier. The scripts record class counts and the effective splits in the measured model reports.

## Install and run (Windows PowerShell)

```powershell
cd D:\sic2\evidence_calibrated_code_review
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env   # if the file is present; otherwise set SECRET_KEY in the environment
python run.py
```

Open <http://127.0.0.1:7000>. The application starts without model artifacts. It shows model-unavailable status and continues to provide the existing review features.

## Dataset preparation and model training

These commands download actual public data. Network access is required for preparation. NVD's unauthenticated API is rate limited; NVD API key configuration can be added if larger downloads are needed. The Python model fit and evaluation use local files only.

```powershell
cd D:\sic2\evidence_calibrated_code_review
\.venv\Scripts\Activate.ps1
python training\prepare_dataset.py --devign
python training\prepare_dataset.py --nvd-year 2024 --max-results 20000
python training\prepare_dataset.py --nvd-year 2023 --max-results 20000
python training\train_models.py --code datasets\processed\devign.jsonl
python training\train_models.py --nvd datasets\processed\nvd-cwe-2023.jsonl datasets\processed\nvd-cwe-2024.jsonl
python training\evaluate_models.py --model code
python training\evaluate_models.py --model nlp
```

The prepared corpora are written to `datasets/processed/`. Model checkpoints and actual test evaluation reports are written to `trained_models/code/` and `trained_models/nlp/`. Keep both local; do not commit datasets or model files unless their terms permit it. `train_models.py` trains only the model(s) named on its command line and refuses unusably small or single-class data rather than generating placeholder outputs. The code report compares TF-IDF logistic regression against a measured majority-class baseline. `evaluate_models.py` prints the saved held-out evaluation report from a completed training run. Use the saved `metrics.json` for the actual measured results; they vary with dataset revisions and must not be copied from an example.

## API

- `POST /api/review` — existing review API; optionally include `"store_source": true` to retain complete submitted source.
- `GET /api/ml/info` — trained state, version, and measured metrics for both models.
- `GET /api/ml/training-status` — whether any local model artifact exists.
- `POST /api/ml/predict` — `{ "code": "...", "language": "c" }`; unavailable response includes a reason.
- `POST /api/nlp/classify` — `{ "description": "..." }`; predicts one of the trained CWE labels when a checkpoint exists.
- `POST /api/nlp/explain` — local code-model result and conservative explanation provenance.
- Existing review history, delete, reports, dashboard and settings APIs remain available.

No source is sent to an external service by default. Optional AI-provider settings remain separate from these local classifiers. Deleting a review deletes its stored findings and, if explicitly opted in, its retained source.

## Evaluation and tests

After training, the code model report includes accuracy, precision, recall, F1, ROC-AUC, PR-AUC, Brier score, ECE, reliability bins, calibration comparison, class counts and confusion matrix. The NLP report includes accuracy, macro/weighted F1 and per-class results. No transformer fine-tuning is claimed. CPU inference is supported; training may use CPU. Unlike a CodeBERT model this baseline is designed to run on ordinary Windows hardware.

Run the automated tests with:

```powershell
python -m pytest
```

## Limitations

Devign is an older C/C++ corpus, not Python-specific data. Its binary labels are coarse, and its project split cannot eliminate all dataset artifacts. NVD description classification can learn label prevalence and dataset language; it is not a substitute for expert CWE mapping. The generated explanation template is not a generative language model. Without downloaded data and trained files, model APIs correctly return unavailable. The non-ML static analyzers and uncalibrated heuristic confidence remain visible for unsupported languages and general code quality.
