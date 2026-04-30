# Schema Discovery Tools

Three tools support schema discovery: `get_database_overview`, `describe_table`, and `search_schema`. None of the three opens a database connection; all read the bundled file `src/cdwagent/data/schema_reference.json`, which is cached in module-level state on first read by `_get_schema_ref`.

## get_database_overview

A clinical researcher invokes this tool when starting an exploration with no prior knowledge of which tables exist. It returns one entry per table containing the table name, description, two boolean flags indicating whether the table holds patient-level or encounter-level data, the column count, and the patient and encounter key columns when present.

```mermaid
sequenceDiagram
    participant U as User
    participant B as BioRouter
    participant T as get_database_overview
    participant F as schema_reference.json (in-memory cache)

    U->>B: "What tables are in CDW?"
    B->>T: call (no arguments)
    T->>F: _get_schema_ref()
    F-->>T: dict of 139 tables
    T-->>B: JSON list of table summaries
    B-->>U: Table catalog
```

```mermaid
flowchart LR
    A[No inputs] --> B[Load schema_reference.json once]
    B --> C[For each table extract name, description, has_patient_data, has_encounter_data, column_count]
    C --> D[Optional: patient_key_column, encounter_key_column]
    D --> E[Return JSON array, one row per table]
```

Tables touched: none. The output is computed entirely from the bundled JSON catalog.

Defaults and limits: returns all 139 tables. No pagination.

Pitfall: the description fields are not exhaustive. For unfamiliar tables the agent should follow up with `describe_table`.

## describe_table

Used when the agent needs the exact column list of a table before composing SQL. Performs a case-insensitive lookup if the supplied name is not an exact match. Includes data-quality notes for four tables that have known caveats: `PatientDim` (SCD Type 2), `LabComponentResultFact` (de-identified `NumericValue`), `LabComponentDim` (`LoincCode` not `Loinc`), and `MedicationDim` (pre-Epic legacy fields).

```mermaid
sequenceDiagram
    participant U as User
    participant B as BioRouter
    participant T as describe_table
    participant F as schema_reference.json

    U->>B: "What columns does LabComponentResultFact have?"
    B->>T: table_name="LabComponentResultFact"
    T->>F: _get_schema_ref()
    alt Table found (exact or case-insensitive)
        T-->>B: {table_name, description, columns[], data_notes?}
    else Not found
        T-->>B: ToolError "Table not found"
    end
```

```mermaid
flowchart LR
    A[table_name string] --> B{Exact match in catalog}
    B -->|Yes| C[Use as-is]
    B -->|No| D{Case-insensitive match}
    D -->|Yes| C
    D -->|No| E[Raise ToolError]
    C --> F[Assemble columns array]
    F --> G{Table in TABLE_NOTES dict}
    G -->|Yes| H[Attach data_notes string]
    G -->|No| I[Skip data_notes]
    H --> J[Return JSON]
    I --> J
```

Tables touched: none.

Defaults and limits: returns the full column list for one table.

Pitfall: columns marked `queryable=false` in the JSON catalog do not exist in the SQL view; the docstring instructs the agent to use the corresponding base column instead, for example `DateKey` rather than `DateKeyValue`.

## search_schema

Used when the researcher knows a clinical concept (such as "allergy" or "vital sign") but does not know which table or column houses it. Runs a substring match (case-insensitive) over both table names and descriptions, and over column names and descriptions, then returns matching tables with their matching columns.

```mermaid
sequenceDiagram
    participant U as User
    participant B as BioRouter
    participant T as search_schema
    participant F as schema_reference.json

    U->>B: "Where are allergies stored?"
    B->>T: keyword="allergy"
    T->>F: _get_schema_ref()
    T->>T: lowercase keyword and walk catalog
    T-->>B: JSON list of {table_name, table_description, matching_columns[]}
    B-->>U: Candidate tables and columns
```

```mermaid
flowchart LR
    A[keyword string] --> B[Lowercase]
    B --> C[For each table]
    C --> D{Keyword in table name or description}
    C --> E[Walk columns]
    E --> F{Keyword in column name or description}
    F -->|Yes| G[Append column entry with queryable note if applicable]
    D -->|Yes or columns matched| H[Append table entry]
    G --> H
    H --> I[Return JSON, or no-match string]
```

Tables touched: none.

Defaults and limits: pure substring match. No semantic expansion or synonym handling.

Pitfall: the keyword "diabetes" returns tables that mention "diabetes" anywhere in metadata, but does not return `DiagnosisDim` rows for diabetes; for that, the agent should call `search_diagnoses_by_code`.
