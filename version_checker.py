
import json
from pathlib import Path
from packaging.version import Version, InvalidVersion

DATA_FILE = Path(__file__).parent / "decisions.json"


def load_decisions():
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def get_verified_versions(decisions=None):
    if decisions is None:
        decisions = load_decisions()
    versions = set()
    for d in decisions:
        for ev in d.get("events", []):
            if ev.get("version"):
                try:
                    versions.add(Version(ev["version"]))
                except InvalidVersion:
                    pass
    return versions


def check_status(decision, flask_version):
    events = decision.get("events", [])

    deprecated_event = next(
        (e for e in events if e["type"] == "deprecated"), None
    )
    removed_event = next(
        (e for e in events if e["type"] == "removed"), None
    )

    if deprecated_event:
        deprecated_version = Version(deprecated_event["version"])

        if flask_version < deprecated_version:
            return {
                "status": "Not yet deprecated",
                "event": deprecated_event
            }

    if removed_event:
        removed_version = Version(removed_event["version"])

        if flask_version >= removed_version:
            return {
                "status": "Removed",
                "event": removed_event
            }

    if deprecated_event:
        return {
            "status": "Deprecated",
            "event": deprecated_event
        }

    return {
        "status": "Unknown",
        "event": None
    }


def main():
    decisions = load_decisions()

    user_input = input("Enter Flask version (e.g. 2.2.0): ")
    user_input = user_input.strip()

    if user_input.lower().startswith("flask "):
        user_input = user_input[6:].strip()

    try:
        flask_version = Version(user_input)
    except InvalidVersion:
        print("Invalid version! Example: 2.2.0")
        return

    verified_versions = get_verified_versions(decisions)
    if flask_version not in verified_versions:
        sorted_vers = ", ".join(sorted(str(v) for v in verified_versions))
        print(f"Unavailable version evidence: No verified version information for Flask {flask_version} (supported versions: {sorted_vers}).")
        return

    print(f"\nRationale Version Check: Flask {flask_version}")
    print("=" * 65)

    for decision in decisions:
        result = check_status(decision, flask_version)

        print(f"\nEntity: {decision['entity']}")
        print(f"Status: {result['status']}")

        event = result["event"]

        if event:
            print(f"Version: {event['version']}")
            print(f"Change: {event['type']}")

            ref = event.get("ref")
            if ref:
                print(f"Evidence: https://github.com/pallets/flask/pull/{ref}")

    print("\n" + "=" * 65)


if __name__ == "__main__":
    main()
