# Top-Level Routing Decision Tree

The CDWAgent does not perform classification or planning of its own; it relies on the Large Language Model that hosts BioRouter to read the server instructions delivered at session initialization and to dispatch tool calls accordingly. The diagram below replicates the decision tree encoded in `CDW_SERVER_INSTRUCTIONS` (defined in `src/cdwagent/server.py`). All node labels are taken verbatim from that constant or from the per-tool docstrings.

## Decision tree

```mermaid
flowchart TD
    Q[User question arrives in BioRouter] --> R0{Question intent}

    R0 -->|Schema question or table lookup| S1[Schema discovery branch]
    R0 -->|Code or vocabulary lookup| C1[Concept search branch]
    R0 -->|Patient detail by ID| P1[Per-patient retrieval branch]
    R0 -->|Cohort or population SQL| Q1[Custom SQL branch]
    R0 -->|Clinical notes question| N1[Notes branch]
    R0 -->|Cross-database OMOP mapping| X1[Crossmap branch]
    R0 -->|Statistics or summary| T1[Statistics branch]
    R0 -->|Save tabular results| E1[Export branch]

    S1 --> S2{Granularity}
    S2 -->|All tables| S3[get_database_overview]
    S2 -->|One table| S4[describe_table]
    S2 -->|Keyword across tables| S5[search_schema]

    C1 --> C2{Concept type}
    C2 -->|Diagnosis ICD or SNOMED| C3[search_diagnoses_by_code]
    C2 -->|Medication NDC or RxNorm| C4[search_medications_by_code]
    C2 -->|Procedure CPT or HCPCS| C5[search_procedures_by_code]

    P1 --> P2{What facet}
    P2 -->|Demographics| P3[get_patient_demographics]
    P2 -->|Encounters| P4[get_encounters]
    P2 -->|Medications| P5[get_medications]
    P2 -->|Diagnoses| P6[get_diagnoses]
    P2 -->|Labs| P7[get_labs]

    Q1 --> Q2[query]
    Q2 --> V1{Validator: SELECT, WITH, or DECLARE only and no semicolon-statement chain}
    V1 -->|Pass| V2[Schema-qualify rule applies; subquery cohort pattern recommended]
    V1 -->|Fail| V3[Reject with read-only error]
    V2 --> Q3{Date column per fact table}
    Q3 -->|EncounterFact| D1[DateKey]
    Q3 -->|DiagnosisEventFact| D2[StartDateKey, EndDateKey]
    Q3 -->|MedicationOrderFact| D3[OrderedDateKey, StartDateKey, EndDateKey]
    Q3 -->|LabComponentResultFact| D4[ResultDateKey]
    Q3 -->|ProcedureEventFact| D5[ProcedureDateKey]
    Q3 -->|note_metadata| D6[deid_service_date]

    N1 --> N2{What is sought}
    N2 -->|Clinical concept mention| N3[search_note_concepts]
    N2 -->|Social determinants| N4[search_note_sdoh]
    N2 -->|Verbatim chart text| N5[search_notes]
    N2 -->|Specific note by key| N6[get_note]

    N3 --> N7{Disambiguation prompt}
    N7 -->|Formally diagnosed| N8[Redirect to search_diagnoses_by_code plus DiagnosisEventFact]
    N7 -->|Mentioned in note| N9[Stay on search_note_concepts]

    X1 --> X2[crossmap_patient]
    X2 --> X3[Cross-database join OMOP_DEID.dbo.person to CDW_NEW.deid_uf.PatientDim on PatientEpicId]

    T1 --> T2{Scope}
    T2 -->|Single table| T3[summarize_table]
    T2 -->|Cohort subquery| T4[cohort_summary]

    E1 --> E2[export_query_to_csv]
    E2 --> V1
```

## Glossary of nodes

| Node | Meaning | Source |
|---|---|---|
| Schema-qualify rule | Every table reference must carry the `deid_uf.` prefix; unqualified references resolve to the `deid` schema and lack `PatientDurableKey`. | `CDW_SERVER_INSTRUCTIONS`, `query` docstring, `export_query_to_csv` docstring |
| Subquery cohort pattern | `WHERE PatientDurableKey IN (SELECT DISTINCT PatientDurableKey FROM <fact> WHERE ...)` instead of joining `PatientDim` to a fact table. | `CDW_SERVER_INSTRUCTIONS` performance section |
| Validator | `ClinicalQueryValidator.is_read_only_clinical_query` accepts only statements starting with `SELECT`, `WITH`, or `DECLARE`, blocks write keywords, and rejects multi-statement chains. | `src/cdwagent/validation.py` |
| Date column per fact table | The agent must select the date key appropriate to each fact table; guessing a generic `DateKey` causes incorrect filtering on `DiagnosisEventFact`, `MedicationOrderFact`, `LabComponentResultFact`, and `ProcedureEventFact`. | `CDW_SERVER_INSTRUCTIONS` |
| Disambiguation prompt | When the user asks for "diabetic patients" without specifying coding versus mention, the agent surfaces the sensitivity-specificity trade-off and either asks or runs both branches. | `CDW_SERVER_INSTRUCTIONS` notes section, `search_note_concepts` docstring |
| Cross-database join | Crossmap is a cross-database query inside one SQL Server instance, not a cross-schema join. It reads `OMOP_DEID.dbo.person` and `CDW_NEW.deid_uf.PatientDim`. | `crossmap_patient` implementation |

## Identifier and date rules that bind every branch

The following rules apply uniformly across the structured-query branches `Q1`, `P1`, and `T1`, and across the cohort form of every notes tool.

```mermaid
flowchart LR
    A[Cohort identifier] --> B{PatientDurableKey vs PatientKey}
    B -->|Stable across SCD2 versions| C[PatientDurableKey - use everywhere]
    B -->|Surrogate, changes with demographics update| D[PatientKey - avoid for joins]

    E[Date filter] --> F{Fact table}
    F -->|EncounterFact| G[DateKey]
    F -->|DiagnosisEventFact| H[StartDateKey]
    F -->|MedicationOrderFact| I[OrderedDateKey or StartDateKey]
    F -->|LabComponentResultFact| J[ResultDateKey]
    F -->|ProcedureEventFact| K[ProcedureDateKey]

    L[Date conversion] --> M[CONVERT DATE, CAST DateKey AS VARCHAR 8, format 112]
    L --> N[Filter invalid: WHERE DateKey greater than 19000101]
```

## Routing signal

BioRouter does not classify questions before dispatch. The Large Language Model receives the union of all enabled extensions' tool descriptions plus the server instructions string, and selects a tool by name. Tool names therefore carry the `CDW-` namespace prefix to disambiguate from siblings such as UCSFOMOPAgent's `query_ucsf_omop`. The flow above is the implicit decision graph the model is expected to follow once it has read `CDW_SERVER_INSTRUCTIONS`.

## Methodological-transparency post-condition

A subset of tools (notably `search_note_concepts` and `search_note_sdoh` in their population-mode plan) prepend a `[NOTICE: ...]` banner to the result string when they apply an internal optimisation, default filter, or approximation that materially affects the interpretation of the returned data. The server instructions formalize a non-negotiable post-condition for the agent: when a tool result begins with `[NOTICE: ...]`, the agent quotes or paraphrases that notice in the user-facing reply. Suppressing notices is treated as a clinical-research integrity violation, since researchers must be able to assess whether the result fits their study's evidentiary requirements (e.g., strict recency for audit versus approximate recency for phenotype discovery).

```mermaid
flowchart LR
    T[Tool result string] --> N{Begins with NOTICE banner?}
    N -->|yes| Q[Agent quotes or paraphrases the notice in the response to the user]
    N -->|no| R[Agent answers normally]
```
