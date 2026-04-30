# Export Tool

`export_query_to_csv` executes a validated read-only SQL query and streams the result to a CSV file at a path supplied by the caller. It is the only CDWAgent tool that writes to the local filesystem, and the only tool whose return value is a side-effect summary rather than result rows.

## Rationale

The standard `query` tool returns at most `row_limit` (1000) rows in a CSV string embedded in the MCP response. For larger extracts the result must be streamed to disk. `export_query_to_csv` opens the output file, writes the column header, and pulls rows in batches of five thousand via `cursor.fetchmany(5000)` until the cursor is exhausted.

## Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant B as BioRouter
    participant T as export_query_to_csv
    participant V as ClinicalQueryValidator
    participant FS as Local filesystem
    participant C as pymssql
    participant S as SQL Server (deid_uf)

    U->>B: "Save the cohort table to /Users/me/exports/cohort.csv"
    B->>T: sql_query, filepath
    T->>V: is_read_only_clinical_query
    alt Validator passes
        V-->>T: True
        T->>FS: Path(filepath).parent.exists?
        alt Directory missing
            FS-->>T: False
            T-->>B: ToolError "Directory does not exist"
        else Directory present
            T->>C: get_connection
            C->>S: cursor.execute(sql)
            S-->>C: column descriptors
            T->>FS: open path, csv.writer, write header
            loop fetchmany(5000)
                C->>S: fetch
                S-->>C: rows
                T->>FS: writer.writerows(rows)
            end
            T-->>B: "Exported N rows to <path>"
        end
    else Validator fails
        V-->>T: False
        T-->>B: ToolError "Only SELECT queries are allowed for export."
    end
```

## Flow

```mermaid
flowchart LR
    A[sql_query string with deid_uf prefix] --> V[Validator]
    A2[filepath absolute path] --> P[Check parent directory exists]
    V -->|Pass| C[Open connection]
    P -->|Exists| C
    P -->|Missing| E[Raise ToolError]
    V -->|Fail| E
    C --> Q[cursor.execute]
    Q --> H{Has columns}
    H -->|No| Z[Return: no results, no file]
    H -->|Yes| W[Open CSV writer, write header]
    W --> L[Loop fetchmany 5000]
    L --> N[Write rows, increment count]
    N --> L
    L -->|No more rows| F[Return Exported N rows to path]
```

## Tables touched

Any tables referenced in `sql_query`. The agent must schema-qualify with `deid_uf.`; the docstring carries that rule as a banner because unqualified names land in the `deid` schema and miss `PatientDurableKey`.

## Defaults and limits

There is no default `row_limit`; the export reads to cursor exhaustion. Batch size is hard-coded at 5000. Output directory must already exist; the tool does not create directories.

## Pitfalls

The path supplied by the user is treated literally. There is no sandbox or path-traversal check beyond `Path(filepath).parent.exists()`. The MCP server runs with the privileges of the BioRouter process, which means a misconfigured caller could overwrite files the user owns.
