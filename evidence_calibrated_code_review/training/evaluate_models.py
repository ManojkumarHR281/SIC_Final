"""Print the actual held-out metrics saved by a completed training run."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def evaluate(name):
    path = ROOT / "trained_models" / name / "metrics.json"
    if not path.is_file():
        raise SystemExit(f"No trained {name} model report found at {path}. Train it first.")
    print(json.dumps(json.loads(path.read_text(encoding="utf-8")), indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=("code", "nlp"), required=True)
    evaluate(parser.parse_args().model)
