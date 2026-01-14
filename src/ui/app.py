import os
import sys
from pathlib import Path
from typing import Dict, Union

import pandas as pd
import streamlit as st

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
def cached_search(endpoint: str, query: str) -> Union[Dict[str, str], str]:
    connector = get_connector(endpoint)
    return connector.search_entities(query)


def main() -> None:
    st.set_page_config(page_title="DAKI KG UI", layout="wide")
    st.title("DAKI Knowledge Graph")

    default_endpoint = os.getenv("GRAPHDB_ENDPOINT", "http://localhost:7200/repositories/dakikg")
    endpoint = st.sidebar.text_input("GraphDB endpoint", value=default_endpoint)

    st.subheader("Entity search")
    q = st.text_input(
        "Search",
        value="",
        placeholder="Type to search (e.g. ibuprofen)…",
        key="entity_query",
    )

    query = q.strip()
    if len(query) < 2:
        st.caption("Type at least 2 characters to search.")
        return

    try:
        results = cached_search(endpoint, query)
    except ConnectionError as e:
        st.error(f"Cannot reach GraphDB at `{endpoint}`.\n\n{e}")
        return
    except MalformedQueryException as e:
        st.error(f"Query error: {e}")
        return
    except Exception as e:
        st.exception(e)
        return

    if isinstance(results, str):
        st.info(results)
        return

    df = pd.DataFrame(
        [{"id": entity_id, "label": label} for entity_id, label in results.items()]
    )

    st.caption(f"{len(df)} hit(s)")
    st.dataframe(df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()


