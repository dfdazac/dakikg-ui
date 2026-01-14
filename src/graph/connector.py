import os
import os.path as osp
import socket
import urllib.error
from pathlib import Path

from SPARQLWrapper import JSON, SPARQLWrapper, SPARQLExceptions

try:
    # When imported as a package module (e.g. `from graph.connector import GraphDBConnector`)
    from .exceptions import MalformedQueryException
except ImportError:  # pragma: no cover
    # When executed directly as a script (e.g. `python src/graph/connector.py`)
    from exceptions import MalformedQueryException


class GraphDBConnector:
    def __init__(self, endpoint: str):
        self.wrapper = SPARQLWrapper(endpoint)
        self.wrapper.setReturnFormat(JSON)
        self.queries_dict = dict()
        self.session_ids = set()
        
    def _get_query(self, query_name: str):
        if query_name not in self.queries_dict:
            # Repo layout: `src/graph/connector.py` + `src/queries/<name>.sparql`
            queries_dir = Path(__file__).resolve().parents[1] / "queries"
            query_path = queries_dir / f"{query_name}.sparql"
            if not os.path.exists(query_path):
                raise FileNotFoundError(f"Expected query file missing: "
                                        f"{query_path}")

            with open(query_path, encoding="utf-8") as f:
                self.queries_dict[query_name] = f.read()
        return self.queries_dict[query_name]

    def clear_session_ids(self):
        self.session_ids = set()

    def is_alive(self):
        try:
            self.execute_query(self._get_query(self.is_alive.__name__))
            return True
        except (urllib.error.URLError, ConnectionRefusedError, socket.timeout, socket.error):
            return False

    def execute_query(self, query: str):
        try:
            self.wrapper.setQuery(query)
            results = self.wrapper.query().convert()
            return results
        except (urllib.error.URLError, ConnectionRefusedError, socket.timeout, socket.error) as e:
            raise ConnectionError(f"Connection failed: {e}") from e
        except SPARQLExceptions.QueryBadFormed as sparql_exception:
            raise MalformedQueryException(f"Attempted to run a malformed query. This is possibly due "
                                          f"to corrupted entity or predicate identifiers. Check the query:\n"
                                          f"{query}\n"
                                          f"Original error: {sparql_exception}")

    def search_entities(self, entity_query: str):
        """Find entity KG identifiers that best match a given search query.

        Args:
            entity_query: Entity query to search for.
        """
        query = self._get_query(self.search_entities.__name__)
        # Escape user input to keep the SPARQL string literal valid while typing in the UI.
        safe_entity_query = entity_query.replace("\\", "\\\\").replace('"', '\\"')
        query = query.replace("q0", safe_entity_query)
        query_results = self.execute_query(query)["results"]["bindings"]
        output = dict()
        for result in query_results:
            uri = result["e"]["value"]
            comment = result["shortComment"]["value"]
            entity_id = uri.split("/")[-1]
            self.session_ids.add(entity_id)
            output[entity_id] = comment

        if len(output) == 0:
            return "No matches found."
        else:
            return output


if __name__ == "__main__":
    from pprint import pprint

    endpoint = os.getenv("GRAPHDB_ENDPOINT", "http://localhost:7200/repositories/dakikg")
    db = GraphDBConnector(endpoint=endpoint)

    if not db.is_alive():
        raise SystemExit(
            "GraphDB is not reachable. Start GraphDB or set GRAPHDB_ENDPOINT, e.g.\n"
            '  GRAPHDB_ENDPOINT="http://localhost:7200/repositories/dakikg" python src/graph/connector.py'
        )

    pprint(db.search_entities("Ibuprofen"))
