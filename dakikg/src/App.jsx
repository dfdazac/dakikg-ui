import { useEffect, useMemo, useState } from 'react'
import './App.css'

const DEFAULT_ENDPOINT =
  import.meta.env.VITE_GRAPHDB_ENDPOINT ??
  '/graphdb/repositories/dakikg'

const LANG_OPTIONS = ['en', 'nl']
const PREDICATES = {
  drug: 'rdfs:label',
  ade: 'skos:prefLabel',
}

const SPARQL_TEMPLATE = `PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?e (SUBSTR(STR(?label), 1, 150) AS ?shortLabel) WHERE {
  ?e <http://www.ontotext.com/plugins/autocomplete#query> "q0" .
  ?e qPred ?label .
  FILTER(lang(?label) = "qLang")
} LIMIT 10`

const escapeSparqlStringLiteral = (value) =>
  value.replace(/\\/g, '\\\\').replace(/"/g, '\\"')

const buildQuery = ({ query, predicate, lang }) => {
  const normalizedLang = (lang || '').trim().toLowerCase()
  if (!LANG_OPTIONS.includes(normalizedLang)) {
    throw new Error(`Unsupported language: ${lang}. Expected en or nl.`)
  }
  if (!Object.values(PREDICATES).includes(predicate)) {
    throw new Error(`Unsupported predicate: ${predicate}.`)
  }
  return SPARQL_TEMPLATE.replace('q0', escapeSparqlStringLiteral(query))
    .replace('qPred', predicate)
    .replace('qLang', normalizedLang)
}

const useDebounce = (value, delayMs) => {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs)
    return () => clearTimeout(timer)
  }, [value, delayMs])

  return debounced
}

const fetchSparql = async ({ endpoint, query, predicate, lang, signal }) => {
  const sparql = buildQuery({ query, predicate, lang })
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      Accept: 'application/sparql-results+json',
      'Content-Type': 'application/sparql-query',
    },
    body: sparql,
    signal,
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(
      `Query failed (${response.status} ${response.statusText}): ${text || 'No response body.'}`
    )
  }

  const payload = await response.json()
  const bindings = payload?.results?.bindings ?? []
  const rows = bindings.map((result) => {
    const uri = result?.e?.value ?? ''
    const label = result?.shortLabel?.value ?? ''
    const id = uri.split('/').pop() || uri
    return { id, label }
  })

  return rows.length === 0 ? 'No matches found.' : rows
}

const useSearchResults = ({ endpoint, query, predicate, lang }) => {
  const [state, setState] = useState({
    loading: false,
    error: null,
    info: null,
    results: [],
  })

  useEffect(() => {
    const trimmed = query.trim()
    if (trimmed.length < 2) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: null,
        info: null,
        results: [],
      }))
      return
    }

    const controller = new AbortController()
    setState((prev) => ({ ...prev, loading: true, error: null, info: null }))

    fetchSparql({
      endpoint,
      query: trimmed,
      predicate,
      lang,
      signal: controller.signal,
    })
      .then((data) => {
        if (typeof data === 'string') {
          setState({ loading: false, error: null, info: data, results: [] })
        } else {
          setState({ loading: false, error: null, info: null, results: data })
        }
      })
      .catch((err) => {
        if (err.name === 'AbortError') {
          return
        }
        setState({
          loading: false,
          error: err?.message || String(err),
          info: null,
          results: [],
        })
      })

    return () => controller.abort()
  }, [endpoint, query, predicate, lang])

  return state
}

function App() {
  const [endpoint, setEndpoint] = useState(DEFAULT_ENDPOINT)
  const [drugLang, setDrugLang] = useState('en')
  const [adeLang, setAdeLang] = useState('en')
  const [drugQuery, setDrugQuery] = useState('')
  const [adeQuery, setAdeQuery] = useState('')

  const debouncedDrugQuery = useDebounce(drugQuery, 200)
  const debouncedAdeQuery = useDebounce(adeQuery, 200)

  const drugSearch = useSearchResults({
    endpoint,
    query: debouncedDrugQuery,
    predicate: PREDICATES.drug,
    lang: drugLang,
  })
  const adeSearch = useSearchResults({
    endpoint,
    query: debouncedAdeQuery,
    predicate: PREDICATES.ade,
    lang: adeLang,
  })

  const drugHint = useMemo(
    () =>
      drugQuery.trim().length < 2
        ? 'Type at least 2 characters to search.'
        : null,
    [drugQuery]
  )
  const adeHint = useMemo(
    () =>
      adeQuery.trim().length < 2
        ? 'Type at least 2 characters to search ADEs.'
        : null,
    [adeQuery]
  )

  return (
    <div className="app">
      <header className="header">
        <h1>DAKI Knowledge Graph</h1>
        <div className="endpoint">
          <label htmlFor="endpoint">GraphDB endpoint</label>
          <input
            id="endpoint"
            type="text"
            value={endpoint}
            onChange={(event) => setEndpoint(event.target.value)}
          />
        </div>
      </header>

      <section className="panel">
        <div className="panel-header">
          <h2>Drug search (using rdf:label)</h2>
          <div className="select">
            <label htmlFor="drug-lang">Drug label language</label>
            <select
              id="drug-lang"
              value={drugLang}
              onChange={(event) => setDrugLang(event.target.value)}
            >
              {LANG_OPTIONS.map((lang) => (
                <option key={lang} value={lang}>
                  {lang}
                </option>
              ))}
            </select>
          </div>
        </div>

        <input
          className="search"
          type="text"
          value={drugQuery}
          placeholder="Type to search (e.g. ibuprofen)..."
          onChange={(event) => setDrugQuery(event.target.value)}
        />
        {drugHint && <p className="hint">{drugHint}</p>}
        {drugSearch.loading && <p className="hint">Searching…</p>}
        {drugSearch.error && <p className="error">{drugSearch.error}</p>}
        {drugSearch.info && <p className="info">{drugSearch.info}</p>}
        {drugSearch.results.length > 0 && (
          <div className="results">
            <p className="caption">{drugSearch.results.length} hit(s)</p>
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Label</th>
                </tr>
              </thead>
              <tbody>
                {drugSearch.results.map((row) => (
                  <tr key={row.id}>
                    <td>{row.id}</td>
                    <td>{row.label}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>Adverse event search (using skos:prefLabel)</h2>
          <div className="select">
            <label htmlFor="ade-lang">ADE label language</label>
            <select
              id="ade-lang"
              value={adeLang}
              onChange={(event) => setAdeLang(event.target.value)}
            >
              {LANG_OPTIONS.map((lang) => (
                <option key={lang} value={lang}>
                  {lang}
                </option>
              ))}
            </select>
          </div>
        </div>

        <input
          className="search"
          type="text"
          value={adeQuery}
          placeholder='Type to search (e.g. "renal pain")...'
          onChange={(event) => setAdeQuery(event.target.value)}
        />
        {adeHint && <p className="hint">{adeHint}</p>}
        {adeSearch.loading && <p className="hint">Searching…</p>}
        {adeSearch.error && <p className="error">{adeSearch.error}</p>}
        {adeSearch.info && <p className="info">{adeSearch.info}</p>}
        {adeSearch.results.length > 0 && (
          <div className="results">
            <p className="caption">{adeSearch.results.length} hit(s)</p>
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Label</th>
                </tr>
              </thead>
              <tbody>
                {adeSearch.results.map((row) => (
                  <tr key={row.id}>
                    <td>{row.id}</td>
                    <td>{row.label}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}

export default App
