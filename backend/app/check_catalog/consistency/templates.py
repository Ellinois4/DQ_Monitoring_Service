"""DQ checks for the DAMA-DMBOK consistency / согласованность dimension."""

from typing import Any

TEMPLATES: dict[str, dict[str, Any]] = {
    "cross_field_comparison": {
        "scope": "table",
        "dimension": "consistency",
        "requires": ["left_column", "operator", "right_column"],
        "failure_query": """
            SELECT COUNT(*) AS failed_rows
            FROM {table} {filters_with_and}
                 {left_column} IS NOT NULL
             AND {right_column} IS NOT NULL
             AND NOT ({left_column} {comparison_operator} {right_column})
        """,
        "sample_query": """
            SELECT {left_column} AS left_value, {right_column} AS right_value
            FROM {table} {filters_with_and}
                 {left_column} IS NOT NULL
             AND {right_column} IS NOT NULL
             AND NOT ({left_column} {comparison_operator} {right_column})
            LIMIT 5
        """,
    },
    "same_entity_same_attribute": {
        "scope": "table",
        "dimension": "consistency",
        "requires": ["entity_key_column", "stable_attribute_column"],
        "failure_query": """
            SELECT COUNT(*) AS failed_rows
            FROM (
                SELECT {entity_key_column}
                FROM {table} {filters}
                GROUP BY {entity_key_column}
                HAVING COUNT(DISTINCT {stable_attribute_column}) > 1
            ) t
        """,
        "sample_query": """
            SELECT {entity_key_column} AS entity_key,
                   COUNT(DISTINCT {stable_attribute_column}) AS distinct_attribute_values,
                   ARRAY_AGG(DISTINCT {stable_attribute_column}) AS values
            FROM {table} {filters}
            GROUP BY {entity_key_column}
            HAVING COUNT(DISTINCT {stable_attribute_column}) > 1
            LIMIT 5
        """,
    },
    "mutually_exclusive_fields": {
        "scope": "table",
        "dimension": "consistency",
        "requires": ["columns"],
        "failure_query": """
            SELECT COUNT(*) AS failed_rows
            FROM {table} {filters_with_and}
                 ({nonempty_columns_count}) > 1
        """,
        "sample_query": """
            SELECT {columns}
            FROM {table} {filters_with_and}
                 ({nonempty_columns_count}) > 1
            LIMIT 5
        """,
    },
}
