# Crossmap Bridge Tool

`crossmap_patient` resolves an OMOP `person_id` (from the `OMOP_DEID` database) to a CDW `PatientDurableKey` (in the `CDW_NEW.deid_uf.PatientDim` table). It is the bridge that lets a BioRouter session combining UCSFOMOPAgent and CDWAgent flow patient identifiers from one extension to the other.

## Rationale

A clinical researcher running an OMOP cohort selection in the OMOP agent obtains a list of `person_id` values. To pull the corresponding clinical detail (notes, full medication orders, lab strings) the analyst needs `PatientDurableKey` values understood by every downstream CDW tool. `crossmap_patient` performs that translation through a single cross-database join on a stable hospital-issued identifier (`PatientEpicId` in CDW, `person_source_value` in OMOP) and reports a sanity-check boolean by comparing birth dates.

## Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant B as BioRouter
    participant T as crossmap_patient
    participant V as ClinicalQueryValidator
    participant C as pymssql
    participant O as OMOP_DEID.dbo.person
    participant P as CDW_NEW.deid_uf.PatientDim

    U->>B: "What is PatientDurableKey for OMOP person_id 12345?"
    B->>T: person_id (int)
    T->>V: is_read_only_clinical_query
    V-->>T: True
    T->>C: get_connection
    C->>O: JOIN P ON p.person_source_value = pd.PatientEpicId AND pd.IsCurrent = 1 WHERE p.person_id = 12345
    O-->>C: One row (or none)
    P-->>C: Demographics columns
    C-->>T: row
    T->>T: Compare omop_birth_date[:10] vs cdw_birth_date[:10]
    T-->>B: CSV plus "birth_date_match: <bool>"
```

## Flow

```mermaid
flowchart LR
    A[person_id integer] --> SQL[SELECT p.person_id, p.person_source_value, p.birth_datetime AS omop_birth_date, pd.PatientDurableKey, pd.PatientEpicId, pd.BirthDate AS cdw_birth_date, pd.Sex, pd.FirstRace, pd.Ethnicity, pd.PreferredLanguage, pd.Status]
    SQL --> J[FROM OMOP_DEID.dbo.person p JOIN CDW_NEW.deid_uf.PatientDim pd ON p.person_source_value = pd.PatientEpicId AND pd.IsCurrent = 1]
    J --> W[WHERE p.person_id = supplied integer]
    W --> CSV[CSV header + 1 row]
    CSV --> M{Match birth dates}
    M -->|Equal first 10 chars| OK[Append birth_date_match: True]
    M -->|Differ| WARN[Append birth_date_match: False with VERIFY MANUALLY notice]
    M -->|No matching row| NF[Append No matching patient found in CDW]
```

## Tables touched

| Database | Schema | Table | Joining column |
|---|---|---|---|
| `OMOP_DEID` | `dbo` | `person` | `person_source_value` |
| `CDW_NEW` | `deid_uf` | `PatientDim` | `PatientEpicId` |

The join requires that the SQL Server account have read access to both databases on the same instance. SQL Server permits cross-database joins when these conditions hold.

## Defaults and limits

The tool fetches a single row (`row_limit=1`). The integer cast `int(person_id)` rejects non-numeric input before the SQL is composed.

## Pitfalls

If the birth dates differ, the result is annotated with `(OMOP: ..., CDW: ... — VERIFY MANUALLY)`. A mismatch typically indicates an identifier collision, a data-load skew between the two databases, or a stale OMOP build. The tool does not fail in this case; it surfaces the discrepancy and lets the user decide.
