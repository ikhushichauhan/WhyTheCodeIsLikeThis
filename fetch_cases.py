import json
import os
import sys
import time
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")

REPO = "pallets/flask"
TOKEN = os.environ.get("GITHUB_TOKEN")

if not TOKEN:
    sys.exit("ERROR: GITHUB_TOKEN set nahi hai.")

API = f"https://api.github.com/repos/{REPO}"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
}

CASES = {
    "before_first_request": [4605, 4995],
    "got_first_request": [4997, 5223],
    "version_attr": [5230, 5648],
    "test_client_as_tuple": [4341, 4417],
    "config_from_json": [3398, 4078],
    "flask_logger": [2436, 2866],
    "markup_escape": [4996, 5084],
}

OUT = Path("data")
OUT.mkdir(exist_ok=True)



def get_json(url, params=None, retries=5):
    last_error = None

    for attempt in range(retries):
        try:
            response = requests.get(
                url,
                headers=HEADERS,
                params=params,
                timeout=30,
            )

            if response.status_code >= 500:
                raise requests.ConnectionError(
                    f"server error {response.status_code}"
                )

            response.raise_for_status()
            return response.json()

        except (requests.ConnectionError, requests.Timeout) as error:
            last_error = error
            wait = 2 ** attempt

            print(
                f"    retry {attempt + 1}/{retries} "
                f"in {wait}s ({type(error).__name__})"
            )

            time.sleep(wait)

    raise last_error



def get_all(url):
    """Fetch all pages. API error par incomplete data return nahi karega."""
    items = []
    page = 1

    while True:
        data = get_json(
            url,
            params={"per_page": 100, "page": page},
        )

        if not data:
            return items

        items.extend(data)
        page += 1


def fetch(number):
    base = get_json(f"{API}/issues/{number}")

    is_pr = "pull_request" in base

    comments = get_all(f"{API}/issues/{number}/comments")

    record = {
        "number": number,
        "type": "pull_request" if is_pr else "issue",
        "url": base["html_url"],
        "title": base["title"],
        "state": base["state"],
        "author": base["user"]["login"],
        "created_at": base["created_at"],
        "closed_at": base.get("closed_at"),
        "labels": [label["name"] for label in base["labels"]],
        "body": base.get("body") or "",
        "comments": [
            {
                "author": c["user"]["login"],
                "created_at": c["created_at"],
                "url": c["html_url"],
                "body": c["body"],
            }
            for c in comments
        ],
        "comments_expected": base["comments"],
        "comments_fetched": len(comments),
        "comments_complete": len(comments) == base["comments"],
    }

    if not record["comments_complete"]:
        print(
            f"  WARNING: #{number} comments mismatch "
            f"(expected {base['comments']}, got {len(comments)})"
        )

    if is_pr:
        pr = get_json(f"{API}/pulls/{number}")

        record["merged"] = pr.get("merged")
        record["merged_at"] = pr.get("merged_at")

        review_comments = get_all(
            f"{API}/pulls/{number}/comments"
        )

        record["review_comments"] = [
            {
                "author": c["user"]["login"],
                "path": c["path"],
                "url": c["html_url"],
                "body": c["body"],
            }
            for c in review_comments
        ]

        files = get_all(f"{API}/pulls/{number}/files")

        record["files"] = [
            {
                "filename": f["filename"],
                "status": f["status"],
                "patch": f.get("patch") or "",
                "patch_missing": not bool(f.get("patch")),
            }
            for f in files
        ]

    return record


if __name__ == "__main__":
    for case, numbers in CASES.items():
        print(f"\n== {case} ==")

        for number in numbers:
            try:
                path = OUT / f"{case}__{number}.json"

                if path.exists():
                    print(f"  #{number} already fetched, skipping")
                    continue

                record = fetch(number)

                path.write_text(
                    json.dumps(
                        record,
                        indent=2,
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )

                extra = ""

                if record["type"] == "pull_request":
                    extra = f", merged_at={record['merged_at']}"

                print(
                    f"  #{number} [{record['type']}] "
                    f"{record['title'][:55]}{extra}"
                )

                if record["type"] == "pull_request":
                    missing = sum(
                        f["patch_missing"] for f in record["files"]
                    )

                    if missing:
                        print(
                            f"    WARNING: {missing} file(s) "
                            "have no patch in API response."
                        )

            except requests.RequestException as error:
                print(f"  ERROR: #{number} API request failed: {error}")

            except (KeyError, ValueError) as error:
                print(f"  ERROR: #{number} data processing failed: {error}")

    print("\nFetch process finished. Check the data/ folder.")
