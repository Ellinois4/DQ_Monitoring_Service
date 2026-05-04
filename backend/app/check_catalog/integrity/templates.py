"""DQ checks for the DAMA-DMBOK integrity / целостность dimension."""

from typing import Any

TEMPLATES: dict[str, dict[str, Any]] = {
    "foreign_key_exists": {
        "scope": "column",
        "dimension": "integrity",
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
            SELECT src.{column} AS missing_reference
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
    "parent_has_child": {
        "scope": "table",
        "dimension": "integrity",
        "requires": ["parent_key_column", "child_schema", "child_table", "child_key_column"],
        "failure_query": """
            SELECT COUNT(*) AS failed_rows
            FROM {table} parent
            {where_keyword}
                 parent.{parent_key_column} IS NOT NULL
             AND NOT EXISTS (
                    SELECT 1
                    FROM {child_table_ref} child
                    WHERE child.{child_key_column} = parent.{parent_key_column}
                 )
             {filters_after_alias}
        """,
        "sample_query": """
            SELECT parent.{parent_key_column} AS parent_key_without_child
            FROM {table} parent
            {where_keyword}
                 parent.{parent_key_column} IS NOT NULL
             AND NOT EXISTS (
                    SELECT 1
                    FROM {child_table_ref} child
                    WHERE child.{child_key_column} = parent.{parent_key_column}
                 )
             {filters_after_alias}
            LIMIT 5
        """,
    },
    "required_link_exists": {
        "scope": "table",
        "dimension": "integrity",
        "requires": ["condition_column", "condition_operator", "link_column", "reference_schema", "reference_table", "reference_column"],
        "failure_query": """
            SELECT COUNT(*) AS failed_rows
            FROM {table} src
            {where_keyword}
                 ({condition_predicate_alias})
             AND src.{link_column} IS NOT NULL
             AND NOT EXISTS (
                    SELECT 1
                    FROM {reference_table_ref} ref
                    WHERE ref.{reference_column} = src.{link_column}
                 )
             {filters_after_alias}
        """,
        "sample_query": """
            SELECT src.{link_column} AS missing_required_link
            FROM {table} src
            {where_keyword}
                 ({condition_predicate_alias})
             AND src.{link_column} IS NOT NULL
             AND NOT EXISTS (
                    SELECT 1
                    FROM {reference_table_ref} ref
                    WHERE ref.{reference_column} = src.{link_column}
                 )
             {filters_after_alias}
            LIMIT 5
        """,
    },
}
