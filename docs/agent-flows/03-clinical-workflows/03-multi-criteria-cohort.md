# Multi-Criteria Cohort Intersection

Research question: "Identify adult patients with type 2 diabetes (ICD-10 E11), an active metformin prescription, and a most-recent HbA1c above eight percent."

Multi-criteria cohort selection intersects three or more independent constraints. The architecture guidance in `CDW_SERVER_INSTRUCTIONS` warns that nesting subqueries across multiple large fact tables times out; the recommended pattern is to resolve concept keys first, then use hard-coded `IN (...)` lists.

## Tool composition

```mermaid
flowchart TD
    Q[Adults with T2D, on metformin, A1c above 8] --> C1[search_diagnoses_by_code E11]
    Q --> C2[search_medications_by_code metformin]
    Q --> C3[search_schema HbA1c, then describe_table LabComponentDim]
    C1 --> K1[DiagnosisKey list]
    C2 --> K2[MedicationKey list]
    C3 --> K3[LabComponentKey for HbA1c]
    K1 --> S1[query: distinct PatientDurableKey from DiagnosisEventFact where DiagnosisKey IN (...)]
    K2 --> S2[query: distinct PatientDurableKey from MedicationOrderFact where MedicationKey IN (...)]
    K3 --> S3[query: PatientDurableKey from LabComponentResultFact where Value high]
    S1 --> I[Intersection in SQL]
    S2 --> I
    S3 --> I
    I --> CS[cohort_summary]
```

## Canonical SQL pattern

```sql
-- After search_diagnoses_by_code, search_medications_by_code, and
-- describe_table('LabComponentDim') the agent has hard-coded key lists.

SELECT PatientDurableKey, Sex, BirthDate, FirstRace, Ethnicity
FROM deid_uf.PatientDim
WHERE IsCurrent = 1
  AND DATEDIFF(YEAR, BirthDate, GETDATE()) >= 18
  AND PatientDurableKey IN (
        SELECT DISTINCT PatientDurableKey
        FROM deid_uf.DiagnosisEventFact
        WHERE DiagnosisKey IN (12345, 12346, 12347)
          AND StartDateKey > 19000101
  )
  AND PatientDurableKey IN (
        SELECT DISTINCT PatientDurableKey
        FROM deid_uf.MedicationOrderFact
        WHERE MedicationKey IN (98765, 98766)
          AND StartDateKey > 19000101
  )
  AND PatientDurableKey IN (
        SELECT PatientDurableKey
        FROM deid_uf.LabComponentResultFact
        WHERE LabComponentKey IN (54321)
          AND TRY_CAST(Value AS FLOAT) > 8.0
          AND ResultDateKey > 19000101
  );
```

The hard-coded `IN (...)` lists come from the prior calls to `search_diagnoses_by_code`, `search_medications_by_code`, and `describe_table('LabComponentDim')`.

## Trade-offs

| Dimension | Behavior |
|---|---|
| Sensitivity | Moderate; depends on coding completeness and lab cutoff. |
| Specificity | High; three independent constraints. |
| Performance | Acceptable when key lists are hard-coded. Cross-fact subquery nesting is forbidden by the performance guidance. |
| Maintenance | Concept keys can shift across data refreshes; re-resolve before each run. |

## Common mistakes

- Nesting `(SELECT ... FROM DiagnosisEventFact WHERE ... AND PatientDurableKey IN (SELECT ... FROM MedicationOrderFact ...))`. The warning in `CDW_SERVER_INSTRUCTIONS` is explicit: this times out; use hard-coded `IN (...)` lists.
- Using `NumericValue` from `LabComponentResultFact` rather than the `Value` string. The docstring on `LabComponentResultFact` warns that `NumericValue` is de-identified.
- Filtering `MedicationOrderFact` only by `OrderedDateKey` when the question concerns an active prescription; the canonical span uses `StartDateKey` and `EndDateKey`.
- Mixing `PatientKey` (from a fact table) with `PatientDurableKey` (in `PatientDim`); they are not interchangeable across SCD2 versions.
