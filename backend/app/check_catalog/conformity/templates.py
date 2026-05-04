"""DQ checks for the DAMA-DMBOK conformity / соответствие dimension."""

from typing import Any

TEMPLATES: dict[str, dict[str, Any]] = {
    "reference_match": {
        "scope": "column",
        "dimension": "conformity",
        "requires": ["reference_schema", "reference_table", "reference_column"],
        "failure_query": """
            SELECT COUNT(*) AS failed_rows
            FROM {table} src
            {where_keyword}
                 src.{column} IS NOT NULL
             AND NOT EXISTS (
                    SELECT 1
                    FROM {reference_table_ref} ref
                    WHERE ref.{reference_column} = src.{column}
                 )
             {filters_after_alias}
        """,
        "sample_query": """
            SELECT src.{column} AS unmatched_value
            FROM {table} src
            {where_keyword}
                 src.{column} IS NOT NULL
             AND NOT EXISTS (
                    SELECT 1
                    FROM {reference_table_ref} ref
                    WHERE ref.{reference_column} = src.{column}
                 )
             {filters_after_alias}
            LIMIT 5
        """,
    },
}
