# dakikg-ui

Streamlit UI for querying the [DAKI-KG](https://github.com/romy-vos/daki-kg/tree/main/sparql) knowledge graph.

## Setup

Create a new conda environment and install the dependencies:

```bash
conda create -n dakikg-ui python=3.12
conda activate dakikg-ui
python -m pip install -r requirements.txt
```

## Configure GraphDB endpoint

By default the app uses:

- `http://localhost:7200/repositories/dakikg`

## Run the UI

```bash
streamlit run src/ui/app.py
```

The UI contains:

- Drug search (uses `rdfs:label`)
- ADE search (uses `skos:prefLabel`)

Both searches use the shared SPARQL template in `src/queries/search_by_label.sparql`.

## Quick connector test

```bash
python src/graph/connector.py
```


