
import os
import requests
import streamlit as st
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

URL = os.getenv("NEO4J_HTTP_URL")
USER = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE")

ENDPOINT = f"{URL}/db/{DATABASE}/query/v2"

st.set_page_config(
    page_title="Why The Code Is Like This",
    page_icon="🔍",
    layout="wide"
)

def run_query(statement, parameters=None):
    response = requests.post(
        ENDPOINT,
        auth=HTTPBasicAuth(USER, PASSWORD),
        json={
            "statement": statement,
            "parameters": parameters or {}
        },
        timeout=20
    )
    response.raise_for_status()

    result = response.json()

    if result.get("errors"):
        raise Exception(result["errors"])

    return result.get("data", {}).get("values", [])


def find_decision(question):
    query = """
    MATCH (d:Decision)
    WHERE any(alias IN d.aliases
        WHERE toLower($question) CONTAINS toLower(alias))
    OPTIONAL MATCH (d)-[:HAS_EVENT]->(ev:ChangeEvent)
    OPTIONAL MATCH (d)-[:SUPPORTED_BY]->(e:Evidence)
    RETURN d.entity, d.status,
           collect(DISTINCT {
               type: ev.type,
               version: ev.version,
               ref: ev.ref,
               merged_at: ev.merged_at
           }),
           collect(DISTINCT {
               quote: e.quote,
               url: e.url,
               ref: e.ref
           })
    """

    rows = run_query(query, {"question": question})

    return rows[0] if rows else None


st.title("🔍 Why The Code Is Like This")
st.caption("Understand the reasoning behind code changes using repository evidence.")

st.divider()

question = st.text_input(
    "Ask about a Flask code decision",
    placeholder="Why was before_first_request removed?"
)

if st.button("Investigate", type="primary"):
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        try:
            with st.spinner("Searching verified repository evidence..."):
                result = find_decision(question)

            if not result:
                st.warning(
                    "No matching code decision found. "
                    "I cannot provide a verified explanation."
                )

            else:
                entity, status, events, evidence = result

                st.subheader(entity)
                st.write(f"**Current status:** {status}")

                if not evidence or not evidence[0]["quote"]:
                    st.warning(
                        "A matching decision was found, "
                        "but no verified rationale is available."
                    )
                    st.info(
                        "I won't invent an explanation without evidence."
                    )

                else:
                    st.subheader("Why was it changed?")

                    for item in evidence:
                        if item["quote"]:
                            st.info(item["quote"])
                            st.markdown(
                                f"[View original evidence]({item['url']})"
                            )

                st.subheader("Change history")

                for event in events:
                    if event["ref"] is not None:
                        st.write(
                            f"- **{event['type'].title()}** "
                            f"in Flask {event['version']} "
                            f"(PR/Issue #{event['ref']})"
                        )

        except Exception as error:
            st.error(f"Something went wrong: {error}")

st.divider()
st.caption("Evidence-backed answers | No generated rationale without sources")


st.sidebar.title("Project Overview")
st.sidebar.markdown("### Evidence-backed code archaeology")
st.sidebar.metric("Verified decisions", 2)
st.sidebar.metric("Refusal cases", 1)
st.sidebar.metric("Total curated cases", 3)

st.sidebar.divider()
st.sidebar.markdown("**Technology Stack**")
st.sidebar.write("• Neo4j AuraDB")
st.sidebar.write("• Python")
st.sidebar.write("• Streamlit")
st.sidebar.write("• GitHub Repository Evidence")

