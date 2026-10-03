#!/usr/bin/env python3
"""Promote reviewed translation drafts into the runtime advice data."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("kn", "ta", "te", "mr", "bn")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", action="append", choices=LANGUAGES, required=True)
    args = parser.parse_args()
    for lang in args.lang:
        source = ROOT / "data" / "advice_i18n" / "drafts" / f"{lang}.json"
        if not source.is_file():
            raise SystemExit(f"Refusing to merge {lang}: reviewed draft does not exist.")
        draft = json.loads(source.read_text(encoding="utf-8"))
        if draft.get("status") != "reviewed":
            raise SystemExit(f"Refusing to merge {lang}: draft status must be 'reviewed'.")
        destination = ROOT / "data" / "advice_i18n" / f"{lang}.json"
        destination.write_text(
            json.dumps({"status": "reviewed", "classes": draft.get("classes", {})},
                       ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
