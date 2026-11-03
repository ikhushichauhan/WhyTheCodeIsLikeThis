
import os
import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

url = os.getenv("NEO4J_HTTP_URL")
username = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")
database = os.getenv("NEO4J_DATABASE")

endpoint = f"{url}/db/{database}/query/v2"

try:
    response = requests.post(
        endpoint,
        auth=HTTPBasicAuth(username, password),
        json={"statement": "RETURN 1 AS ok"},
        timeout=15
    )

    print("HTTP Status:", response.status_code)
    print("Response:", response.text[:1500])

except requests.RequestException as e:
    print("Connection failed:", type(e).__name__, e)
