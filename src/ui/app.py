import os
import sys
from pathlib import Path
from typing import Dict, Union

import pandas as pd
import streamlit as st
from st_keyup import st_keyup

# Allow running via: `streamlit run src/ui/app.py`
SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from graph.connector import GraphDBConnector  # noqa: E402
from graph.exceptions import MalformedQueryException  # noqa: E402


@st.cache_resource(show_spinner=False)
def get_connector(endpoint: str) -> GraphDBConnector:
    connector = GraphDBConnector(endpoint=endpoint)
    # Keep UI snappy: if SPARQLWrapper supports timeouts, enable a short one.
    if hasattr(connector.wrapper, "setTimeout"):
        try:
            connector.wrapper.setTimeout(5)
        except Exception:
            pass
    return connector


@st.cache_data(show_spinner=False, ttl=30)
def cached_search(endpoint: str, query: str, lang: str) -> Union[Dict[str, str], str]:
    connector = get_connector(endpoint)
    return connector.search_entities(query, lang=lang)

@st.cache_data(show_spinner=False, ttl=30)
def cached_search_ades(endpoint: str, query: str, lang: str) -> Union[Dict[str, str], str]:
    connector = get_connector(endpoint)
    return connector.search_ades(query, lang=lang)


def main() -> None:
    st.set_page_config(page_title="DAKI KG UI", layout="wide")
    st.title("DAKI Knowledge Graph")

    default_endpoint = os.getenv("GRAPHDB_ENDPOINT", "http://localhost:7200/repositories/dakikg")
    endpoint = st.sidebar.text_input("GraphDB endpoint", value=default_endpoint)

    st.subheader("Drug search (using rdf:label)")
    drug_lang = st.selectbox("Drug label language", options=["en", "nl"], index=0, key="drug_lang")
    # Updates on every keystroke (debounced).
    q = st_keyup(
        "Search",
        value="",
        placeholder="Type to search (e.g. ibuprofen)…",
        key="entity_query",
        debounce=200,
    )

    drug_query = q.strip()
    if len(drug_query) < 2:
        st.caption("Type at least 2 characters to search.")
    else:
        try:
            results = cached_search(endpoint, drug_query, drug_lang)
        except ConnectionError as e:
            st.error(f"Cannot reach GraphDB at `{endpoint}`.\n\n{e}")
            return
        except MalformedQueryException as e:
            st.error(f"Query error: {e}")
            return
        except ValueError as e:
            st.error(str(e))
            return
        except Exception as e:
            st.exception(e)
            return

        if isinstance(results, str):
            st.info(results)
        else:
            df = pd.DataFrame(
                [{"id": entity_id, "label": label} for entity_id, label in results.items()]
            )
            st.caption(f"{len(df)} hit(s)")
            st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()

    st.subheader("Adverse event search (using skos:prefLabel)")
    ade_lang = st.selectbox("ADE label language", options=["en", "nl"], index=0, key="ade_lang")
    aq = st_keyup(
        "Search ADE",
        value="",
        placeholder='Type to search (e.g. "renal pain")…',
        key="ade_query",
        debounce=200,
    )

    ade_query = aq.strip()
    if len(ade_query) < 2:
        st.caption("Type at least 2 characters to search ADEs.")
        return

    try:
        ade_results = cached_search_ades(endpoint, ade_query, ade_lang)
    except ConnectionError as e:
        st.error(f"Cannot reach GraphDB at `{endpoint}`.\n\n{e}")
        return
    except MalformedQueryException as e:
        st.error(f"Query error: {e}")
        return
    except ValueError as e:
        st.error(str(e))
        return
    except Exception as e:
        st.exception(e)
        return

    if isinstance(ade_results, str):
        st.info(ade_results)
        return

    ade_df = pd.DataFrame(
        [{"id": ade_id, "label": label} for ade_id, label in ade_results.items()]
    )
    st.caption(f"{len(ade_df)} hit(s)")
    st.dataframe(ade_df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()


