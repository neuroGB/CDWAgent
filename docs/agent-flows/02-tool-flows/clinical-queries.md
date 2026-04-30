# Clinical Query Tools

Six tools live in `tools/queries.py` (a seventh, `crossmap_patient`, is documented separately under [crossmap-bridge.md](./crossmap-bridge.md)). One is a general-purpose SQL executor (`query`) and five are canned per-patient retrievals (`get_patient_demographics`, `get_encounters`, `get_medications`, `get_diagnoses`, `get_labs`). All six pass through `_execute_readonly_query`, which validates with `ClinicalQueryValidator.is_read_only_clinical_query`, opens a fresh `pymssql` connection, runs the query, fetches up to `row_limit` rows, and returns CSV.

## query

A clinical researcher invokes `query` when no canned tool matches the question. The docstring carries the schema-qualification rule as a banner because unqualified table references are the single largest error source observed in production.

```mermaid
sequenceDiagram
    participant U as User
    participant B as BioRouter
    participant T as query
    participant V as ClinicalQueryValidator
    participant C as pymssql
    participant S as SQL Server (deid_uf)

    U->>B: Custom SQL question
    B->>T: sql_query, row_limit
    T->>V: is_read_only_clinical_query
    alt Pass
        V-->>T: True
        T->>C: get_connection
        C->>S: cursor.execute(sql)
        S-->>C: rows + description
        T-->>B: CSV (header + up to row_limit rows)
    else Fail
        V-->>T: False
        T-->>B: ToolError "Only SELECT queries are allowed."
    end
```

```mermaid
flowchart LR
    A[sql_query string] --> V[Validator]
    A2[row_limit default 1000] --> F[fetchmany]
    V -->|Pass| C[pymssql connection]
    C --> Q[cursor.execute]
    Q --> F
    F --> O[CSV: header line + comma-joined rows]
```

Tables touched: any in `deid_uf`; the agent must include the schema prefix.

Defaults and limits: `row_limit=1000`. The validator rejects queries that do not start with `SELECT`, `WITH`, or `DECLARE`, that contain a write keyword (`MERGE|CREATE|SET|DELETE|REMOVE|ADD|INSERT|UPDATE|DROP|ALTER|TRUNCATE|GRANT|REVOKE|EXEC|EXECUTE|SP_`), or that chain a second statement after a semicolon.

Pitfalls: unqualified tables resolve to schema `deid` and miss `PatientDurableKey`; joining `PatientDim` to fact tables exceeds 120 seconds and times out; CTE-plus-JOIN also times out; correct pattern is `WHERE PatientDurableKey IN (SELECT DISTINCT PatientDurableKey FROM <fact> WHERE ...)`.

## get_patient_demographics

Used when the researcher already has a `PatientDurableKey` (or, less reliably, a `PatientKey`) and needs the most recent demographic record. The tool generated SQL accepts either identifier through an `OR` predicate and orders by `IsCurrent = 1` first then `StartDate DESC`, taking the top one row.

```mermaid
sequenceDiagram
    participant B as BioRouter
    participant T as get_patient_demographics
    participant S as deid_uf.PatientDim

    B->>T: patient_id
    T->>S: SELECT TOP 1 * FROM deid_uf.PatientDim WHERE PatientDurableKey = id OR PatientKey = id ORDER BY IsCurrent DESC, StartDate DESC
    S-->>T: One demographic row
    T-->>B: CSV
```

```mermaid
flowchart LR
    A[patient_id string] --> SQL[SELECT TOP 1 from deid_uf.PatientDim with PatientDurableKey or PatientKey filter]
    SQL --> P[deid_uf.PatientDim]
    P --> R[Single CSV row: PatientKey, PatientDurableKey, Sex, BirthDate, DeathDate, FirstRace, Ethnicity, ...]
```

Tables touched: `deid_uf.PatientDim`.

Defaults and limits: returns one row.

Pitfalls: if the supplied identifier is a `PatientKey` from an outdated SCD2 version, the row returned may have `IsCurrent = 0`; the docstring directs the agent to prefer `PatientDurableKey` whenever available.

## get_encounters

Used when the researcher needs encounter-level history for a single patient. Orders by `DateKey DESC`, which is the correct date column for `EncounterFact`.

```mermaid
sequenceDiagram
    participant B as BioRouter
    participant T as get_encounters
    participant S as deid_uf.EncounterFact

    B->>T: patient_id, row_limit
    T->>S: SELECT TOP row_limit * WHERE PatientDurableKey or PatientKey = id ORDER BY DateKey DESC
    S-->>T: Encounter rows
    T-->>B: CSV
```

```mermaid
flowchart LR
    A[patient_id, row_limit] --> SQL[SELECT TOP N * FROM deid_uf.EncounterFact WHERE PatientDurableKey = id OR PatientKey = id ORDER BY DateKey DESC]
    SQL --> E[deid_uf.EncounterFact]
    E --> R[CSV rows: EncounterKey, PatientKey, PatientDurableKey, DateKey, Type, DepartmentName, DepartmentSpecialty, PatientClass, VisitType]
```

Tables touched: `deid_uf.EncounterFact`.

Pitfalls: the column is `Type`, not `EncounterType`. Date column is `DateKey`, not `EncounterDateKey`.

## get_medications

Used when the researcher needs prescription history. Orders by `OrderedDateKey DESC`. The docstring reminds the agent that for treatment-duration analysis the `StartDateKey` to `EndDateKey` span is the correct interval, not the order date.

```mermaid
flowchart LR
    A[patient_id, row_limit] --> SQL[SELECT TOP N * FROM deid_uf.MedicationOrderFact WHERE PatientDurableKey = id OR PatientKey = id ORDER BY OrderedDateKey DESC]
    SQL --> M[deid_uf.MedicationOrderFact]
    M --> R[CSV: MedicationKey, PatientDurableKey, OrderedDateKey, StartDateKey, EndDateKey, ...]
```

Tables touched: `deid_uf.MedicationOrderFact`.

## get_diagnoses

Used when the researcher needs diagnosis events for a patient. Orders by `StartDateKey DESC`.

```mermaid
flowchart LR
    A[patient_id, row_limit] --> SQL[SELECT TOP N * FROM deid_uf.DiagnosisEventFact WHERE PatientDurableKey = id OR PatientKey = id ORDER BY StartDateKey DESC]
    SQL --> D[deid_uf.DiagnosisEventFact]
    D --> R[CSV: DiagnosisKey, PatientDurableKey, StartDateKey, EndDateKey, ...]
```

Tables touched: `deid_uf.DiagnosisEventFact`.

## get_labs

Used when the researcher needs lab component results for a patient. Orders by `ResultDateKey DESC`.

```mermaid
flowchart LR
    A[patient_id, row_limit] --> SQL[SELECT TOP N * FROM deid_uf.LabComponentResultFact WHERE PatientDurableKey = id OR PatientKey = id ORDER BY ResultDateKey DESC]
    SQL --> L[deid_uf.LabComponentResultFact]
    L --> R[CSV: LabComponentKey, PatientDurableKey, ResultDateKey, Value, ReferenceValues, Flag, Abnormal, ...]
```

Tables touched: `deid_uf.LabComponentResultFact`.

Pitfalls: `NumericValue` is de-identified and contains the literal token `DEID`; the agent must use the `Value` string column for actual lab values. There is no `TextValue`, `ReferenceLow`, `ReferenceHigh`, or `AbnormalFlag` column; use `Value`, `ReferenceValues` (combined string), `Flag`, and `Abnormal`.
