# Concept Search Tools

Three tools live in `tools/concepts.py`: `search_diagnoses_by_code`, `search_medications_by_code`, and `search_procedures_by_code`. They translate codes or names into the surrogate keys that fact tables reference. They are the canonical first step in any structured cohort workflow.

## search_diagnoses_by_code

Used when the researcher has an ICD or SNOMED code (or a textual diagnosis name) and needs the corresponding `DiagnosisKey` values that index `DiagnosisEventFact`. Joins the terminology table to the diagnosis dimension.

```mermaid
sequenceDiagram
    participant B as BioRouter
    participant T as search_diagnoses_by_code
    participant DT as deid_uf.DiagnosisTerminologyDim
    participant DD as deid_uf.DiagnosisDim

    B->>T: search_term, row_limit
    T->>DT: JOIN DiagnosisDim on DiagnosisKey
    DT-->>T: TOP row_limit rows where Value, DisplayString, or Name LIKE term
    T-->>B: CSV
```

```mermaid
flowchart LR
    A[search_term string] --> SQL[SELECT TOP N dt.DiagnosisTerminologyKey, dt.DiagnosisKey, dt.Type, dt.Value, dt.DisplayString, dd.Name]
    SQL --> J[FROM deid_uf.DiagnosisTerminologyDim dt JOIN deid_uf.DiagnosisDim dd ON dt.DiagnosisKey = dd.DiagnosisKey]
    J --> W[WHERE dt.Value LIKE pattern OR dt.DisplayString LIKE pattern OR dd.Name LIKE pattern]
    W --> R[CSV: DiagnosisTerminologyKey, DiagnosisKey, Type, Value, DisplayString, DiagnosisName]
```

Tables touched: `deid_uf.DiagnosisTerminologyDim`, `deid_uf.DiagnosisDim`. Joining column: `DiagnosisKey`.

Defaults and limits: `row_limit=50`.

Pitfalls: substring `LIKE` matching can return many irrelevant rows when the search term is a short token (for example searching for "MI" matches every code containing the letters "MI"). The agent should narrow with a more specific code prefix when possible.

## search_medications_by_code

Used when the researcher has an NDC, RxNorm, brand name, or generic name and needs `MedicationKey` values that index `MedicationOrderFact`. Reads `MedicationCodeDim` only; `MedicationDim` lookup is implicit through the `MedicationKey` foreign key.

```mermaid
sequenceDiagram
    participant B as BioRouter
    participant T as search_medications_by_code
    participant MC as deid_uf.MedicationCodeDim

    B->>T: search_term, row_limit
    T->>MC: SELECT TOP N rows WHERE Code, MedicationName, or MedicationGenericName LIKE term
    MC-->>T: Rows
    T-->>B: CSV
```

```mermaid
flowchart LR
    A[search_term string] --> SQL[SELECT TOP N mc.MedicationCodeKey, mc.MedicationKey, mc.Type, mc.Code, mc.MedicationName, mc.MedicationGenericName, mc.MedicationTherapeuticClass]
    SQL --> F[FROM deid_uf.MedicationCodeDim mc]
    F --> W[WHERE mc.Code LIKE pattern OR mc.MedicationName LIKE pattern OR mc.MedicationGenericName LIKE pattern]
    W --> R[CSV: MedicationCodeKey, MedicationKey, Type, Code, MedicationName, MedicationGenericName, MedicationTherapeuticClass]
```

Tables touched: `deid_uf.MedicationCodeDim`.

Defaults and limits: `row_limit=50`.

Pitfalls: pre-Epic legacy `MedicationDim` records have `*Unspecified` values for `GenericName`, `TherapeuticClass`, `Strength`, and `Form`; only `Name` is reliable for those rows. The describe-table data note for `MedicationDim` records this caveat.

## search_procedures_by_code

Used when the researcher has a CPT or HCPCS code, or a textual procedure name, and needs procedure terminology rows that link to `ProcedureEventFact`.

```mermaid
sequenceDiagram
    participant B as BioRouter
    participant T as search_procedures_by_code
    participant PT as deid_uf.ProcedureTerminologyDim

    B->>T: search_term, row_limit
    T->>PT: SELECT TOP N rows WHERE Code or Name LIKE term
    PT-->>T: Rows
    T-->>B: CSV
```

```mermaid
flowchart LR
    A[search_term string] --> SQL[SELECT TOP N pt.ProcedureTerminologyKey, pt.Code, pt.Name, pt.CodeSet]
    SQL --> F[FROM deid_uf.ProcedureTerminologyDim pt]
    F --> W[WHERE pt.Code LIKE pattern OR pt.Name LIKE pattern]
    W --> R[CSV: ProcedureTerminologyKey, Code, Name, CodeSet]
```

Tables touched: `deid_uf.ProcedureTerminologyDim`.

Defaults and limits: `row_limit=50`.

Pitfalls: `CodeSet` distinguishes CPT, HCPCS, and other vocabularies; the agent should filter on `CodeSet` when the user has specified a vocabulary.
