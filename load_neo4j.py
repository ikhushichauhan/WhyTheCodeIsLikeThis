import os
import json
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

URL = os.getenv("NEO4J_HTTP_URL")
USER = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE")

ENDPOINT = f"{URL}/db/{DATABASE}/query/v2"

# Verified source URLs
SOURCE_URLS = {
    4605: "https://github.com/pallets/flask/issues/4605",
    4995: "https://github.com/pallets/flask/pull/4995",
    4997: "https://github.com/pallets/flask/pull/4997",
    5223: "https://github.com/pallets/flask/pull/5223",
    4341: "https://github.com/pallets/flask/pull/4341",
    4417: "https://github.com/pallets/flask/pull/4417",
}

def run_query(statement, parameters):
    response = requests.post(
        ENDPOINT,
        auth=HTTPBasicAuth(USER, PASSWORD),
        json={
            "statement": statement,
            "parameters": parameters
        },
        timeout=30
    )

    if response.status_code != 202:
        raise Exception(
            f"HTTP {response.status_code}: {response.text}"
        )

    result = response.json()

    if result.get("errors"):
        raise Exception(result["errors"])

    return result


with open("decisions.json", encoding="utf-8") as f:
    decisions = json.load(f)

for decision in decisions:
    events_with_urls = []
    for ev in decision.get("events", []):
        ev_copy = dict(ev)
        ev_copy["url"] = SOURCE_URLS.get(ev.get("ref"), "")
        events_with_urls.append(ev_copy)

    params = {
        "entity": decision["entity"],
        "aliases": decision["aliases"],
        "status": decision["status"],
        "events": events_with_urls
    }

    query = """
    MERGE (d:Decision {entity: $entity})
    SET d.aliases = $aliases,
        d.status = $status
    WITH d
    UNWIND $events AS ev
    MERGE (e:ChangeEvent {ref: ev.ref})
    SET e.type = ev.type,
        e.version = ev.version,
        e.merged_at = ev.merged_at,
        e.url = ev.url
    MERGE (d)-[:HAS_EVENT]->(e)
    RETURN d.entity AS entity
    """

    run_query(query, params)

    # Load evidence for rationale and events without duplicates
    rationale = decision.get("rationale")
    rationale_ref = rationale.get("ref") if rationale else None

    # Load all verified references as evidence
    for ev in decision.get("events", []):
        ref = ev["ref"]
        quote = rationale["quote"] if (rationale and ref == rationale_ref) else ""
        url = SOURCE_URLS.get(ref, "")

        evidence_query = """
        MATCH (d:Decision {entity: $entity})
        MERGE (e:Evidence {
            entity: $entity,
            ref: $ref
        })
        SET e.url = $url,
            e.quote = CASE WHEN $quote <> '' THEN $quote ELSE coalesce(e.quote, '') END
        MERGE (d)-[:SUPPORTED_BY]->(e)
        RETURN e.ref AS ref
        """

        run_query(evidence_query, {
            "entity": decision["entity"],
            "ref": ref,
            "quote": quote,
            "url": url
        })

    print("Loaded:", decision["entity"])

print("\nAll decisions processed successfully!")
