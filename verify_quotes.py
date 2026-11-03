
import json
import re
from pathlib import Path

DATA = Path("data")

def norm(text):
    text = re.sub(r"[`*_>]", "", text)
    return re.sub(r"\s+", " ", text).strip().lower()

def source_text(ref):
    files = list(DATA.glob(f"*__{ref}.json"))

    if not files:
        return None

    rec = json.loads(
        files[0].read_text(encoding="utf-8")
    )

    parts = [
        rec.get("title", ""),
        rec.get("body", "")
    ]

    parts += [
        c.get("body", "")
        for c in rec.get("comments", [])
    ]

    parts += [
        c.get("body", "")
        for c in rec.get("review_comments", [])
    ]

    return norm(" ".join(parts)), rec.get("url", "")

decisions = json.loads(
    Path("decisions.json").read_text(encoding="utf-8")
)

for decision in decisions:
    rationale = decision.get("rationale")

    if not rationale:
        print(f"{decision['entity']}: NULL (refusal case)")
        continue

    found = source_text(rationale["ref"])

    if not found:
        print(
            f"{decision['entity']}: FILE NOT FOUND "
            f"#{rationale['ref']}"
        )
        continue

    text, url = found
    verified = norm(rationale["quote"]) in text

    print(
        f"{decision['entity']}: "
        f"{'VERIFIED' if verified else 'NOT FOUND'}"
    )
    print("Source:", url)
