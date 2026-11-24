"""Fetch the real CodeXGLUE/Devign and NVD datasets into datasets/processed."""
import argparse
import json
import time
from datetime import date, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "datasets" / "processed"


def prepare_devign():
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise SystemExit("Install requirements (including Hugging Face datasets) to fetch CodeXGLUE Devign.") from exc
    dataset = load_dataset("google/code_x_glue_cc_defect_detection")
    OUT.mkdir(parents=True, exist_ok=True)
    output = OUT / "devign.jsonl"
    with output.open("w", encoding="utf-8") as target:
        for split_name, split in dataset.items():
            for row in split:
                record = {"code": row.get("func"), "label": int(row.get("target")),
                          "project": row.get("project"), "commit_id": row.get("commit_id"), "source_split": split_name}
                target.write(json.dumps(record, ensure_ascii=False) + "\n")
    (OUT / "devign-attribution.json").write_text(json.dumps({
        "dataset": "CodeXGLUE defect detection / Devign", "huggingface_id": "google/code_x_glue_cc_defect_detection",
        "upstream": "https://github.com/microsoft/CodeXGLUE", "language": "C/C++",
        "labels": "binary defect/vulnerability target; project and commit fields retained",
        "license": "No license declared in the referenced dataset metadata; review upstream terms before redistribution.",
        "rows_downloaded": sum(len(split) for split in dataset.values()),
    }, indent=2), encoding="utf-8")
    print(f"Saved {output}; source: google/code_x_glue_cc_defect_detection (Devign, C/C++)")


def prepare_nvd(year, max_results):
    """Download year-bounded records from the official NVD 2.0 CVE API."""
    OUT.mkdir(parents=True, exist_ok=True)
    output = OUT / f"nvd-cwe-{year}.jsonl"
    endpoint = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    first, end = date(year, 1, 1), min(date(year + 1, 1, 1), date.today() + timedelta(days=1))
    rows, seen = [], set()
    while first < end and len(rows) < max_results:
        last = min(first + timedelta(days=119), end - timedelta(days=1))
        params = {"pubStartDate": first.isoformat() + "T00:00:00.000",
                  "pubEndDate": last.isoformat() + "T23:59:59.999", "resultsPerPage": 2000}
        offset, total = 0, None
        while total is None or offset < total:
            params["startIndex"] = offset
            response = requests.get(endpoint, params=params, timeout=90)
            if response.status_code == 403:
                time.sleep(7)
                response = requests.get(endpoint, params=params, timeout=90)
            response.raise_for_status()
            data = response.json()
            total = data.get("totalResults", 0)
            for item in data.get("vulnerabilities", []):
                cve = item.get("cve", {})
                descriptions = [d.get("value", "") for d in cve.get("descriptions", []) if d.get("lang") == "en"]
                weaknesses = [w.get("description", []) for w in cve.get("weaknesses", [])]
                cwes = [d.get("value") for group in weaknesses for d in group if str(d.get("value", "")).startswith("CWE-")]
                text = descriptions[0] if descriptions else ""
                label = next((c for c in cwes if c not in {"CWE-Other", "CWE-NVD-CWE-noinfo"}), None)
                key = cve.get("id")
                if key and key not in seen and text and label:
                    seen.add(key)
                    rows.append({"cve_id": key, "description": text, "cwe": label})
                    if len(rows) >= max_results:
                        break
            offset += data.get("resultsPerPage", 0)
            if offset >= total or not data.get("resultsPerPage"):
                break
            time.sleep(6.2)  # NVD's public API rate limit without an API key.
        first = last + timedelta(days=1)
        print(f"NVD {year}: collected {len(rows)} labeled descriptions")
    with output.open("w", encoding="utf-8") as target:
        for row in rows:
            target.write(json.dumps(row, ensure_ascii=False) + "\n")
    output.with_name(output.stem + "-attribution.json").write_text(json.dumps({
        "dataset": "NVD CVE API 2.0", "source": "https://nvd.nist.gov/developers/vulnerabilities",
        "year": year, "language": "English descriptions", "labels": "NVD-assigned CWE identifiers",
        "license": "NVD is public U.S. government data; CVE records may include CNA supplied content.",
        "rows_downloaded": len(rows), "max_results": max_results,
    }, indent=2), encoding="utf-8")
    print(f"Saved {output}; NVD API v2.0, year={year}, labeled records={len(rows)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--devign", action="store_true", help="Fetch CodeXGLUE Devign code data")
    parser.add_argument("--nvd-year", type=int, help="Fetch NVD CVE/CWE pairs for one publication year")
    parser.add_argument("--max-results", type=int, default=20000)
    args = parser.parse_args()
    if args.devign:
        prepare_devign()
    if args.nvd_year:
        prepare_nvd(args.nvd_year, args.max_results)
    if not args.devign and not args.nvd_year:
        parser.error("Choose --devign and/or --nvd-year.")
