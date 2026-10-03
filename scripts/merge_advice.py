#!/usr/bin/env python3
"""Copy reviewed advice drafts into the runtime translation files."""

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADVICE_DIR = ROOT / "data" / "advice_i18n"
LANGUAGES = ("kn", "ta", "te", "mr", "bn")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lang",
        action="append",
        choices=LANGUAGES,
        required=True,
        help="reviewed language draft to merge; repeat for multiple languages",
    )
    args = parser.parse_args()

    for lang in args.lang:
        source = ADVICE_DIR / "drafts" / f"{lang}.json"
        if not source.is_file():
            raise SystemExit(f"Refusing to merge {lang}: draft does not exist.")
        try:
            draft = json.loads(source.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Refusing to merge {lang}: draft is invalid JSON ({exc}).") from exc
        if not isinstance(draft, dict) or draft.get("status") != "reviewed":
            raise SystemExit(f"Refusing to merge {lang}: draft status must be 'reviewed'.")
        if not isinstance(draft.get("classes"), dict):
            raise SystemExit(f"Refusing to merge {lang}: draft classes must be an object.")
        shutil.copyfile(source, ADVICE_DIR / f"{lang}.json")
        print(f"Merged reviewed {lang} advice.")


if __name__ == "__main__":
    main()
