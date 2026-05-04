"""DQ checks for the DAMA-DMBOK completeness / полнота dimension."""

from typing import Any

TEMPLATES: dict[str, dict[str, Any]] = {
    "not_null": {
        "scope": "column",
        "dimension": "completeness",
        "failure_predicate": "{column} IS NULL",
    },
    "not_blank": {
        "scope": "column",
        "dimension": "completeness",
        "failure_predicate": "{column} IS NULL OR BTRIM(CAST({column} AS TEXT)) = ''",
    },
    "conditional_not_null": {
        "scope": "column",
        "dimension": "completeness",
        "requires": ["condition_column", "condition_operator"],
        "failure_query": """
            SELECT COUNT(*) AS failed_rows
            FROM {table} {filters_with_and}
                 ({condition_predicate})
             AND ({column} IS NULL OR BTRIM(CAST({column} AS TEXT)) = '')
        """,
        "sample_query": """
            SELECT *
            FROM {table} {filters_with_and}
                 ({condition_predicate})
             AND ({column} IS NULL OR BTRIM(CAST({column} AS TEXT)) = '')
            LIMIT 5
        """,
    },
    "expected_columns_present": {
        "scope": "table",
        "dimension": "completeness",
        "requires": ["required_columns"],
        "checked_query": "SELECT COUNT(*) AS checked_rows FROM (VALUES {required_columns_values}) AS required(column_name)",
        "failure_query": """
            WITH required(column_name) AS (VALUES {required_columns_values}),
            missing AS (
                SELECT r.column_name
                FROM required r
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM information_schema.columns c
                    WHERE c.table_schema = :dataset_schema
                      AND c.table_name = :dataset_table
                      AND c.column_name = r.column_name
                )
            )
            SELECT COUNT(*) AS failed_rows FROM missing
        """,
        "sample_query": """
            WITH required(column_name) AS (VALUES {required_columns_values})
            SELECT r.column_name AS missing_column
            FROM required r
            WHERE NOT EXISTS (
                SELECT 1
                FROM information_schema.columns c
                WHERE c.table_schema = :dataset_schema
                  AND c.table_name = :dataset_table
                  AND c.column_name = r.column_name
            )
            LIMIT 20
        """,
    },
    "column_fill_rate": {
        "scope": "column",
        "dimension": "completeness",
        "requires": ["min_fill_percent"],
        "checked_query": "SELECT 1 AS checked_rows",
        "failure_query": """
            WITH stats AS (
                SELECT COUNT(*) AS total_rows,
                       COUNT(*) FILTER (WHERE {column} IS NOT NULL AND BTRIM(CAST({column} AS TEXT)) <> '') AS filled_rows
                FROM {table} {filters}
            )
            SELECT CASE
                WHEN total_rows = 0 THEN 0
                WHEN (filled_rows::numeric / total_rows::numeric) * 100 >= :min_fill_percent THEN 0
                ELSE 1
            END AS failed_rows
            FROM stats
        """,
        "sample_query": """
            SELECT COUNT(*) AS total_rows,
                   COUNT(*) FILTER (WHERE {column} IS NOT NULL AND BTRIM(CAST({column} AS TEXT)) <> '') AS filled_rows,
                   ROUND((COUNT(*) FILTER (WHERE {column} IS NOT NULL AND BTRIM(CAST({column} AS TEXT)) <> '')::numeric / NULLIF(COUNT(*), 0)) * 100, 4) AS fill_percent,
                   :min_fill_percent AS required_fill_percent
            FROM {table} {filters}
        """,
    },
}
