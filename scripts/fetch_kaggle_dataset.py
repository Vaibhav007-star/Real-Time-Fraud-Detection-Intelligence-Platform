#!/usr/bin/env python3
"""Fetches the official real-world Kaggle Credit Card Fraud Detection dataset
(mlg-ulb/creditcardfraud, 284,807 transactions) and copies it into data/kaggle/.
"""
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))


def main() -> None:
    dest_dir = ROOT / "data" / "kaggle"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / "creditcard.csv"

    if dest_file.exists() and dest_file.stat().st_size > 10 * 1024 * 1024:
        print(f"[OK] Real Kaggle dataset already present at {dest_file} ({dest_file.stat().st_size / (1024*1024):.2f} MB)")
        return

    print("Fetching 'mlg-ulb/creditcardfraud' from Kaggle via kagglehub...")
    try:
        import kagglehub
        path = kagglehub.dataset_download("mlg-ulb/creditcardfraud")
        downloaded_file = Path(path) / "creditcard.csv"
        if not downloaded_file.exists():
            files = list(Path(path).glob("*.csv"))
            if files:
                downloaded_file = files[0]
            else:
                raise FileNotFoundError(f"No CSV found in downloaded folder: {path}")

        print(f"Copying {downloaded_file.name} to {dest_file}...")
        shutil.copy2(downloaded_file, dest_file)
        print(f"[SUCCESS] Successfully saved real dataset to {dest_file} ({dest_file.stat().st_size / (1024*1024):.2f} MB)")
    except Exception as exc:
        print(f"[ERROR] Failed to download dataset via kagglehub: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
