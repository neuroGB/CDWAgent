# CDWAgent Flow Documentation

This documentation set traces, in figurative form, how the CDWAgent MCP server routes natural-language clinical-research questions to specific SQL operations against the de-identified Epic Caboodle Clinical Data Warehouse (`deid_uf` schema, SQL Server). It is intended for clinical researchers and developers who need to understand the agent's reasoning visually before they trust its answers. Every diagram and SQL fragment is grounded in the source code under `src/cdwagent/` of this repository; nothing is invented.

## Scope

The documentation covers (1) the top-level routing decision tree the agent follows once a user question arrives, (2) per-tool input/output flow for each of the twenty MCP tools the server exposes, (3) twenty canonical clinical-research workflows showing multi-tool composition, (4) a tool-to-table topology map, and (5) a structured-versus-mentioned disambiguation matrix. It does not cover server installation, BioRouter configuration, schema regeneration, or downstream analytic frameworks; those are addressed in the top-level `README.md`, `AGENTS.md`, and `docs/BIOROUTER.md`.

## Contents

| File | Purpose |
|---|---|
| [01-routing-decision-tree.md](./01-routing-decision-tree.md) | Top-level question-to-tool decision tree mirroring `CDW_SERVER_INSTRUCTIONS` |
| [02-tool-flows/README.md](./02-tool-flows/README.md) | Per-tool flow index with one-line descriptions |
| [02-tool-flows/schema-discovery.md](./02-tool-flows/schema-discovery.md) | `get_database_overview`, `describe_table`, `search_schema` |
| [02-tool-flows/clinical-queries.md](./02-tool-flows/clinical-queries.md) | `query`, `get_patient_demographics`, `get_encounters`, `get_medications`, `get_diagnoses`, `get_labs` |
| [02-tool-flows/notes-retrieval.md](./02-tool-flows/notes-retrieval.md) | `search_note_concepts`, `search_note_sdoh`, `search_notes`, `get_note` |
| [02-tool-flows/concept-search.md](./02-tool-flows/concept-search.md) | `search_diagnoses_by_code`, `search_medications_by_code`, `search_procedures_by_code` |
| [02-tool-flows/crossmap-bridge.md](./02-tool-flows/crossmap-bridge.md) | `crossmap_patient` (OMOP `person_id` to CDW `PatientDurableKey`) |
| [02-tool-flows/export.md](./02-tool-flows/export.md) | `export_query_to_csv` |
| [02-tool-flows/statistics.md](./02-tool-flows/statistics.md) | `summarize_table`, `cohort_summary` |
| [03-clinical-workflows/README.md](./03-clinical-workflows/README.md) | Catalog of canonical research workflows |
| [03-clinical-workflows/01-cohort-by-codes.md](./03-clinical-workflows/01-cohort-by-codes.md) | Cohort identification by structured ICD/RxNorm/CPT codes |
| [03-clinical-workflows/02-cohort-by-phenotype.md](./03-clinical-workflows/02-cohort-by-phenotype.md) | Phenotype identification via NLP-extracted concepts |
| [03-clinical-workflows/03-multi-criteria-cohort.md](./03-clinical-workflows/03-multi-criteria-cohort.md) | Diagnosis intersected with medication and a lab cutoff |
| [03-clinical-workflows/04-time-restricted-cohort.md](./03-clinical-workflows/04-time-restricted-cohort.md) | Incidence, prevalence, and new-user designs |
| [03-clinical-workflows/05-lab-trajectory.md](./03-clinical-workflows/05-lab-trajectory.md) | Longitudinal biomarker trajectories |
| [03-clinical-workflows/06-drug-exposure-trajectory.md](./03-clinical-workflows/06-drug-exposure-trajectory.md) | Single-patient and cohort drug exposure timelines |
| [03-clinical-workflows/07-disease-progression.md](./03-clinical-workflows/07-disease-progression.md) | Diagnosis-event sequence reconstruction |
| [03-clinical-workflows/08-healthcare-utilization.md](./03-clinical-workflows/08-healthcare-utilization.md) | Encounters, admissions, and ED visits |
| [03-clinical-workflows/09-adverse-drug-event.md](./03-clinical-workflows/09-adverse-drug-event.md) | Exposure-to-outcome window for ADE signal detection |
| [03-clinical-workflows/10-polypharmacy.md](./03-clinical-workflows/10-polypharmacy.md) | Concurrent medication overlap analysis |
| [03-clinical-workflows/11-notes-phenotype-extraction.md](./03-clinical-workflows/11-notes-phenotype-extraction.md) | Symptom, family history, and prior-condition extraction |
| [03-clinical-workflows/12-sdoh-research.md](./03-clinical-workflows/12-sdoh-research.md) | Social determinants of health via the cTAKES SDOH layer |
| [03-clinical-workflows/13-stratified-disparities.md](./03-clinical-workflows/13-stratified-disparities.md) | Cohort stratified by race, ethnicity, insurance, and SDOH |
| [03-clinical-workflows/14-vulnerable-population.md](./03-clinical-workflows/14-vulnerable-population.md) | Vulnerability identification combining structured and NLP signals |
| [03-clinical-workflows/15-trial-feasibility.md](./03-clinical-workflows/15-trial-feasibility.md) | Eligibility-criteria simulation for clinical trials |
| [03-clinical-workflows/16-care-gap-detection.md](./03-clinical-workflows/16-care-gap-detection.md) | Missing screenings and uncontrolled disease detection |
| [03-clinical-workflows/17-readmission-analysis.md](./03-clinical-workflows/17-readmission-analysis.md) | Thirty-day readmission by index condition |
| [03-clinical-workflows/18-omop-cdw-bridge.md](./03-clinical-workflows/18-omop-cdw-bridge.md) | OMOP-to-CDW patient bridge via `crossmap_patient` |
| [03-clinical-workflows/19-write-rejection.md](./03-clinical-workflows/19-write-rejection.md) | Read-only enforcement and validator rejection path |
| [03-clinical-workflows/20-disambiguation.md](./03-clinical-workflows/20-disambiguation.md) | Structured-coded versus note-mentioned disambiguation |
| [04-schema-interaction-map.md](./04-schema-interaction-map.md) | Tool-to-table topology of the fourteen most-used tables |
| [05-disambiguation-matrix.md](./05-disambiguation-matrix.md) | Detailed sensitivity/specificity matrix and decision flow |

## Source-of-truth references

| Documentation element | Source file |
|---|---|
| Decision tree node labels | `src/cdwagent/server.py` (`CDW_SERVER_INSTRUCTIONS`) |
| Tool input schemas and SQL templates | `src/cdwagent/tools/*.py` |
| Read-only validation logic | `src/cdwagent/validation.py` |
| Connection lifecycle | `src/cdwagent/db.py` |
| Schema reference catalog | `src/cdwagent/data/schema_reference.json` |
