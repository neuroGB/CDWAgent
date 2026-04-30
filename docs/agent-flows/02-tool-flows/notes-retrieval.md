# Clinical Notes Tools

Four tools live in `tools/notes.py`: `search_note_concepts`, `search_note_sdoh`, `search_notes`, and `get_note`. The first three accept a cohort (a list of one or more `PatientDurableKey` values, validated against the regular expression `^[A-Za-z0-9_-]+$` and capped at 2000 entries). All four share the helper `_query_to_csv`, which validates SQL and returns CSV.

## search_note_concepts

Used when the question concerns clinical concepts mentioned in notes (diseases, drugs, symptoms, procedures). Backed by the cTAKES NLP layer indexed in `note_concepts`. Defaults `exclude_negated=True` and `exclude_family_history=True`, removing the most common false positives in retrospective phenotyping. `exclude_historical` defaults to `False` because historical mentions are typically clinically relevant for retrospective research.

```mermaid
sequenceDiagram
    participant B as BioRouter
    participant T as search_note_concepts
    participant V as ClinicalQueryValidator
    participant NC as deid_uf.note_concepts
    participant NM as deid_uf.note_metadata
    participant NT as deid_uf.note_text

    B->>T: canon_text?, cui?, patient_durable_keys?, domain?, flags, row_limit
    T->>T: _validate_cohort if keys provided
    T->>V: is_read_only_clinical_query
    V-->>T: True
    T->>NC: JOIN note_concepts nc with note_metadata nm
    alt include_snippet=True
        T->>NT: LEFT JOIN note_text for substring window
    end
    NC-->>T: TOP row_limit rows
    T-->>B: CSV: deid_note_key, PatientDurableKey, canon_text, cui, domain, confidence, flags, snippet?
```

```mermaid
flowchart LR
    A[canon_text or cui or cohort required] --> V[Validate cohort and escape keyword]
    V --> SQL[SELECT TOP N nc.deid_note_key, nm.PatientDurableKey, nc.canon_text, nc.cui, nc.domain, nc.confidence, nc.negated, nc.family_history, nc.history, nm.note_type, nm.enc_dept_specialty, nm.deid_service_date]
    SQL --> J1[FROM deid_uf.note_concepts nc JOIN deid_uf.note_metadata nm ON nc.deid_note_key = nm.deid_note_key]
    J1 --> J2{include_snippet}
    J2 -->|True| J3[LEFT JOIN deid_uf.note_text nt ON nc.deid_note_key = nt.deid_note_key plus SUBSTRING window]
    J2 -->|False| J4[No join]
    J3 --> W[WHERE 1=1 + cohort + canon_text LIKE + cui equality + domain + nc.negated = 0 + nc.family_history = 0 + nc.confidence threshold]
    J4 --> W
    W --> O[ORDER BY nm.deid_service_date DESC]
    O --> R[CSV rows]
```

Tables touched: `deid_uf.note_concepts` (joined to `deid_uf.note_metadata` on `deid_note_key`), optionally `deid_uf.note_text` for the snippet window.

Defaults and limits: `exclude_negated=True`, `exclude_family_history=True`, `exclude_historical=False`, `min_confidence=0.5`, `include_snippet=True`, `row_limit=100`. Cohort cap is 2000.

Pitfalls: this tool searches concepts mentioned, which is not the same as formally coded diagnoses. The disambiguation block in the docstring instructs the agent to surface this distinction when the user's question is ambiguous.

Population-mode optimisation (v0.4.3+): when invoked without `patient_durable_keys`, the tool emits two distinct SQL plans and prepends a `[NOTICE: ...]` banner to the result. The cohort plan applies the `PatientDurableKey IN (...)` filter directly and orders by date, since the cohort is selective enough to keep the join fast. The population plan rewrites the query as a derived subquery that pushes the `canon_text LIKE` and `negated`/`family_history`/`confidence` filters into an inner `SELECT TOP {row_limit*4}` and then joins `note_metadata` outside; the inner cap allows SQL Server to short-circuit the table scan once enough matches accumulate. The trade-off is that the returned rows are no longer the strict top-`row_limit` by `deid_service_date` but the top-`row_limit` of the first ~`row_limit*4` matches encountered. The notice banner instructs the agent to surface this approximation in its reply, per the methodological-transparency clause in the server instructions.

```mermaid
flowchart TD
    Q[search_note_concepts call] --> C{patient_durable_keys?}
    C -->|provided| P1[Cohort plan: standard JOIN with WHERE PatientDurableKey IN ...]
    C -->|empty| P2[Population plan: derived subquery with TOP cap + outer JOIN]
    P1 --> R1[CSV rows]
    P2 --> N[Prepend NOTICE banner]
    N --> R2[NOTICE banner + CSV rows]
    R2 --> A[Agent must surface notice in user-facing reply]
```

## search_note_sdoh

Used when the question concerns Social Determinants of Health (smoking status, housing instability, food insecurity, employment, substance use, transportation barriers). Backed by `note_concepts_sdoh`, populated by the cTAKES SDOH module. Structured fields rarely capture these signals, so the notes layer is often the only source.

```mermaid
sequenceDiagram
    participant B as BioRouter
    participant T as search_note_sdoh
    participant NC as deid_uf.note_concepts_sdoh
    participant NM as deid_uf.note_metadata

    B->>T: canon_text?, patient_durable_keys?, exclude_negated, row_limit
    T->>NC: JOIN with note_metadata on deid_note_key
    NC-->>T: TOP row_limit rows ORDER BY deid_service_date DESC
    T-->>B: CSV
```

```mermaid
flowchart LR
    A[canon_text or cohort required] --> V[Validate cohort and escape keyword]
    V --> SQL[SELECT TOP N nc.deid_note_key, nm.PatientDurableKey, nc.canon_text, nc.cui, nc.domain, nc.confidence, nc.negated, nm.note_type, nm.enc_dept_specialty, nm.deid_service_date]
    SQL --> J[FROM deid_uf.note_concepts_sdoh nc JOIN deid_uf.note_metadata nm ON nc.deid_note_key = nm.deid_note_key]
    J --> W[WHERE 1=1 + cohort + canon_text LIKE + nc.negated = 0]
    W --> O[ORDER BY nm.deid_service_date DESC]
    O --> R[CSV rows]
```

Tables touched: `deid_uf.note_concepts_sdoh`, `deid_uf.note_metadata`.

Defaults and limits: `exclude_negated=True`, `row_limit=100`. Cohort cap is 2000.

Pitfalls: at least one of `canon_text` or `patient_durable_keys` must be supplied; otherwise the tool raises `ToolError`.

The same population-mode optimisation and `[NOTICE: ...]` banner described for `search_note_concepts` apply here when `patient_durable_keys` is omitted (v0.4.3+).

## search_notes

Used for chart review or verbatim phrase match. Requires a defined cohort. The optional `keyword` argument adds a `LIKE` filter on `note_text`. Returns up to fifty notes with a five-hundred-character snippet by default.

```mermaid
sequenceDiagram
    participant B as BioRouter
    participant T as search_notes
    participant NM as deid_uf.note_metadata
    participant NT as deid_uf.note_text

    B->>T: patient_durable_keys (required), keyword?, row_limit
    T->>T: _validate_cohort (size <= 2000, key regex)
    T->>NM: JOIN note_text on deid_note_key
    NM-->>T: TOP row_limit notes ORDER BY deid_service_date DESC
    T-->>B: CSV with SUBSTRING(note_text, 1, 500) snippet
```

```mermaid
flowchart LR
    A[patient_durable_keys list required] --> V[_validate_cohort: regex, size cap, dedupe]
    V --> SQL[SELECT TOP N nm.deid_note_key, nm.PatientDurableKey, nm.note_type, nm.encounter_type, nm.enc_dept_specialty, nm.deid_service_date, SUBSTRING(nt.note_text, 1, 500) AS note_snippet]
    SQL --> J[FROM deid_uf.note_metadata nm JOIN deid_uf.note_text nt ON nm.deid_note_key = nt.deid_note_key]
    J --> W[WHERE nm.PatientDurableKey IN cohort + optional nt.note_text LIKE keyword]
    W --> O[ORDER BY nm.deid_service_date DESC]
    O --> R[CSV rows]
```

Tables touched: `deid_uf.note_metadata`, `deid_uf.note_text`.

Defaults and limits: `row_limit=50`. Cohort cap is 2000 patients (SQL Server `IN`-clause practical limit).

Pitfalls: free-text matches are noisy because they include differential diagnoses, assessments, and history; for clinical-concept search the docstring directs the agent to prefer `search_note_concepts`. For cohorts above 2000 patients, only `search_note_concepts` scales.

## get_note

Used when the agent already has a `deid_note_key` (typically from `search_notes` or `search_note_concepts`) and needs the full note body.

```mermaid
sequenceDiagram
    participant B as BioRouter
    participant T as get_note
    participant NM as deid_uf.note_metadata
    participant NT as deid_uf.note_text

    B->>T: note_key
    T->>T: regex check on note_key
    T->>NM: JOIN note_text on deid_note_key WHERE deid_note_key = note_key
    NM-->>T: One row including full note_text
    T-->>B: CSV
```

```mermaid
flowchart LR
    A[note_key string] --> V{Regex check ^[A-Za-z0-9_-]+$}
    V -->|Pass| SQL[SELECT nm.deid_note_key, nm.note_type, nm.encounter_type, nm.enc_dept_specialty, nm.deid_service_date, nt.note_text]
    V -->|Fail| E[ToolError invalid note_key format]
    SQL --> J[FROM deid_uf.note_metadata nm JOIN deid_uf.note_text nt ON nm.deid_note_key = nt.deid_note_key]
    J --> W[WHERE nm.deid_note_key = note_key]
    W --> R[CSV with full text]
```

Tables touched: `deid_uf.note_metadata`, `deid_uf.note_text`.

Pitfalls: the note text can be very long. Callers that handle long contexts should consume the returned CSV stream rather than parsing in-memory.
