
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
    4997: "https://github.com/pallets/flask/pull/4997",
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
    params = {
        "entity": decision["entity"],
        "aliases": decision["aliases"],
        "status": decision["status"],
        "events": decision["events"]
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
        e.merged_at = ev.merged_at
    MERGE (d)-[:HAS_EVENT]->(e)
    RETURN d.entity AS entity
    """

    run_query(query, params)

    rationale = decision.get("rationale")

    if rationale:
        ref = rationale["ref"]

        evidence_query = """
        MATCH (d:Decision {entity: $entity})
        MERGE (e:Evidence {
            entity: $entity,
            ref: $ref
        })
        SET e.quote = $quote,
            e.url = $url
        MERGE (d)-[:SUPPORTED_BY]->(e)
        RETURN e.ref AS ref
        """

        run_query(evidence_query, {
            "entity": decision["entity"],
            "ref": ref,
            "quote": rationale["quote"],
            "url": SOURCE_URLS.get(ref, "")
        })

    print("Loaded:", decision["entity"])

print("\nAll decisions processed successfully!")
