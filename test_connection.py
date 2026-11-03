import os
from urllib.parse import urlparse

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")
env_db = os.getenv("NEO4J_DATABASE")

print("URI loaded:", bool(uri))
print("URI scheme:", urlparse(uri).scheme if uri else None)
print("URI hostname present:", bool(urlparse(uri).hostname) if uri else False)
print("Username loaded:", bool(user))
print("Password set:", bool(password))
print("Database from .env:", env_db)

try:
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        driver.verify_connectivity()
        print("SUCCESS: connected to server")

        for db in [env_db, "neo4j"]:
            if not db:
                continue
            try:
                with driver.session(database=db) as session:
                    ok = session.run("RETURN 1 AS ok").single()["ok"]
                    print(f"SUCCESS: query worked with database={db!r} -> {ok}")
                    break
            except Exception as e:
                print(f"FAILED with database={db!r}: {type(e).__name__}: {e}")
except Exception as e:
    print(type(e).__name__, ":", e)