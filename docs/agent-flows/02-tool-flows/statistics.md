# Statistics Tools

Two tools live in `tools/stats.py`: `summarize_table` for table-level profiling and `cohort_summary` for cohort-level demographics aggregation.

## summarize_table

Used when the researcher needs to understand the shape and density of a table before composing a query. Returns the row count and, for the first fifty columns, the data type, null count, and null percentage.

```mermaid
sequenceDiagram
    participant B as BioRouter
    participant T as summarize_table
    participant C as pymssql
    participant I as INFORMATION_SCHEMA.COLUMNS
    participant S as deid_uf.<table>

    B->>T: table_name
    T->>T: Reject non-alphanumeric (allow underscore and dot)
    T->>C: get_connection
    C->>S: SELECT COUNT(*) FROM [deid_uf].[table]
    S-->>C: row_count
    C->>I: SELECT COLUMN_NAME, DATA_TYPE WHERE TABLE_SCHEMA='deid_uf' AND TABLE_NAME=table
    I-->>C: column list
    loop first 50 columns
        C->>S: SELECT COUNT(*) WHERE [col] IS NULL
        S-->>C: null_count
    end
    T-->>B: JSON {table_name, row_count, columns[]}
```

```mermaid
flowchart LR
    A[table_name string] --> V{Replace underscores and dots, then isalnum}
    V -->|Pass| Q1[COUNT * for row_count]
    V -->|Fail| E[ToolError invalid table name]
    Q1 --> Q2[INFORMATION_SCHEMA.COLUMNS for column list]
    Q2 --> L[Loop first 50 columns]
    L --> Q3[Per-column NULL count]
    Q3 --> J[Build JSON: name, data_type, null_count, null_pct]
    J --> R[Return JSON object]
```

Tables touched: `[deid_uf].[<table>]` plus `INFORMATION_SCHEMA.COLUMNS`.

Defaults and limits: profiles the first fifty columns by ordinal position. Uses bracket-quoted identifiers `[deid_uf].[table]` so `summarize_table` works on any user-supplied table name that passes the alphanumeric check.

Pitfalls: per-column null-count probes scale linearly with column count; tables with many columns or large row counts may approach the BioRouter timeout. The fifty-column cap mitigates this.

## cohort_summary

Used to count and stratify a cohort defined by an arbitrary subquery returning patient identifiers. The tool auto-detects whether the subquery yields `PatientDurableKey` (preferred) or `PatientKey` (fallback), then computes counts and demographic breakdowns by joining `PatientDim` filtered to `IsCurrent = 1`.

```mermaid
sequenceDiagram
    participant B as BioRouter
    participant T as cohort_summary
    participant V as ClinicalQueryValidator
    participant C as pymssql
    participant P as deid_uf.PatientDim

    B->>T: patient_key_query, demographics flag
    T->>V: is_read_only_clinical_query on patient_key_query
    V-->>T: True
    T->>C: SELECT COUNT(DISTINCT PatientDurableKey) FROM (subquery)
    alt Subquery yields PatientDurableKey
        C-->>T: count, id_column = PatientDurableKey
    else Falls back to PatientKey
        T->>C: SELECT COUNT(DISTINCT PatientKey) FROM (subquery)
        C-->>T: count, id_column = PatientKey
    end
    alt demographics=True and count > 0
        T->>P: SELECT Sex, COUNT(*) WHERE IsCurrent=1 AND <id_col> IN (subquery) GROUP BY Sex
        T->>P: SELECT FirstRace, COUNT(*) ... GROUP BY FirstRace
        T->>P: SELECT Ethnicity, COUNT(*) ... GROUP BY Ethnicity
    end
    T-->>B: JSON {patient_key_query, id_column, patient_count, sex, race, ethnicity}
```

```mermaid
flowchart LR
    A[patient_key_query SELECT subquery] --> V[Validator: read-only check]
    V -->|Pass| C1[COUNT DISTINCT PatientDurableKey from subquery]
    V -->|Fail| E[ToolError invalid patient_key_query]
    C1 -->|OK| ID1[id_column = PatientDurableKey]
    C1 -->|Exception| C2[COUNT DISTINCT PatientKey from subquery]
    C2 --> ID2[id_column = PatientKey]
    ID1 --> D{demographics flag}
    ID2 --> D
    D -->|True and count > 0| S1[Sex breakdown via PatientDim WHERE IsCurrent=1]
    D -->|True and count > 0| S2[FirstRace breakdown]
    D -->|True and count > 0| S3[Ethnicity breakdown]
    S1 --> J[Combine into JSON]
    S2 --> J
    S3 --> J
    D -->|False or count = 0| J
    J --> R[Return JSON]
```

Tables touched: any tables in the user-supplied `patient_key_query`, plus `deid_uf.PatientDim` for the three demographic GROUP BY queries.

Defaults and limits: `demographics=True`. The auto-detection mechanism uses a try-except on the `PatientDurableKey` count query and falls back to `PatientKey` only on exception.

Pitfalls: using `PatientKey` rather than `PatientDurableKey` in the subquery silently triggers the fallback path, but the demographic stratification then joins on `PatientKey` against `PatientDim WHERE IsCurrent = 1`, which matches only the subset of historical surrogate keys that happen to coincide with the current SCD2 row (approximately sixteen percent in observed data). The docstring directs the agent to use `PatientDurableKey` in every subquery.
