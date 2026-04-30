# Clinical Workflow Catalog

The twenty workflows below cover the canonical research patterns CDWAgent is expected to support. Each file presents a clinical research question, a multi-tool composition diagram, the canonical SQL pattern (always schema-qualified with `deid_uf.` and using the `PatientDurableKey IN (...)` cohort pattern), trade-offs, and common mistakes the LLM tends to make. The mistakes are extracted from the warnings encoded in `CDW_SERVER_INSTRUCTIONS` and the per-tool docstrings.

| # | Workflow | File |
|---|---|---|
| 1 | Cohort identification by structured codes | [01-cohort-by-codes.md](./01-cohort-by-codes.md) |
| 2 | Phenotype identification by NLP-mentioned concepts | [02-cohort-by-phenotype.md](./02-cohort-by-phenotype.md) |
| 3 | Multi-criteria cohort intersection | [03-multi-criteria-cohort.md](./03-multi-criteria-cohort.md) |
| 4 | Time-restricted cohort (incidence vs prevalence) | [04-time-restricted-cohort.md](./04-time-restricted-cohort.md) |
| 5 | Lab and biomarker trajectory analysis | [05-lab-trajectory.md](./05-lab-trajectory.md) |
| 6 | Drug exposure trajectory | [06-drug-exposure-trajectory.md](./06-drug-exposure-trajectory.md) |
| 7 | Disease progression sequence | [07-disease-progression.md](./07-disease-progression.md) |
| 8 | Healthcare utilization | [08-healthcare-utilization.md](./08-healthcare-utilization.md) |
| 9 | Adverse drug event signal detection | [09-adverse-drug-event.md](./09-adverse-drug-event.md) |
| 10 | Polypharmacy and drug-drug overlap | [10-polypharmacy.md](./10-polypharmacy.md) |
| 11 | Notes phenotype extraction | [11-notes-phenotype-extraction.md](./11-notes-phenotype-extraction.md) |
| 12 | Social Determinants of Health research | [12-sdoh-research.md](./12-sdoh-research.md) |
| 13 | Stratified disparities analysis | [13-stratified-disparities.md](./13-stratified-disparities.md) |
| 14 | Vulnerable population identification | [14-vulnerable-population.md](./14-vulnerable-population.md) |
| 15 | Clinical trial feasibility | [15-trial-feasibility.md](./15-trial-feasibility.md) |
| 16 | Care gap detection | [16-care-gap-detection.md](./16-care-gap-detection.md) |
| 17 | Readmission analysis | [17-readmission-analysis.md](./17-readmission-analysis.md) |
| 18 | OMOP-to-CDW bridge | [18-omop-cdw-bridge.md](./18-omop-cdw-bridge.md) |
| 19 | Read-only enforcement and write rejection | [19-write-rejection.md](./19-write-rejection.md) |
| 20 | Disambiguation: structured-coded vs note-mentioned | [20-disambiguation.md](./20-disambiguation.md) |
