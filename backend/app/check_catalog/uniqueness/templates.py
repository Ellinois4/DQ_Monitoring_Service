"""DQ checks for the DAMA-DMBOK uniqueness / уникальность dimension."""

from typing import Any

TEMPLATES: dict[str, dict[str, Any]] = {
    "unique": {
        "scope": "column",
        "dimension": "uniqueness",
        "failure_query": "SELECT COALESCE(SUM(cnt), 0) AS failed_rows FROM (SELECT COUNT(*) AS cnt FROM {table} {filters} GROUP BY {column} HAVING COUNT(*) > 1) t",
        "sample_query": "SELECT {column} AS value, COUNT(*) AS duplicate_count FROM {table} {filters} GROUP BY {column} HAVING COUNT(*) > 1 ORDER BY duplicate_count DESC LIMIT 5",
    },
    "composite_unique": {
        "scope": "table",
        "dimension": "uniqueness",
        "requires": ["columns"],
        "failure_query": "SELECT COALESCE(SUM(cnt), 0) AS failed_rows FROM (SELECT COUNT(*) AS cnt FROM {table} {filters} GROUP BY {columns} HAVING COUNT(*) > 1) t",
        "sample_query": "SELECT {columns}, COUNT(*) AS duplicate_count FROM {table} {filters} GROUP BY {columns} HAVING COUNT(*) > 1 ORDER BY duplicate_count DESC LIMIT 5",
    },
    "duplicate_rows": {
        "scope": "table",
        "dimension": "uniqueness",
        "requires": ["columns"],
        "failure_query": "SELECT COALESCE(SUM(cnt), 0) AS failed_rows FROM (SELECT COUNT(*) AS cnt FROM {table} {filters} GROUP BY {columns} HAVING COUNT(*) > 1) t",
        "sample_query": "SELECT {columns}, COUNT(*) AS duplicate_count FROM {table} {filters} GROUP BY {columns} HAVING COUNT(*) > 1 ORDER BY duplicate_count DESC LIMIT 5",
    },
    "case_insensitive_unique": {
        "scope": "column",
        "dimension": "uniqueness",
        "failure_query": "SELECT COALESCE(SUM(cnt), 0) AS failed_rows FROM (SELECT COUNT(*) AS cnt FROM {table} {filters} GROUP BY LOWER(BTRIM(CAST({column} AS TEXT))) HAVING COUNT(*) > 1) t",
        "sample_query": "SELECT LOWER(BTRIM(CAST({column} AS TEXT))) AS normalized_value, COUNT(*) AS duplicate_count FROM {table} {filters} GROUP BY LOWER(BTRIM(CAST({column} AS TEXT))) HAVING COUNT(*) > 1 ORDER BY duplicate_count DESC LIMIT 5",
    },
}
