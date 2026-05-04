"""DQ checks for the DAMA-DMBOK consistency / validity / допустимость dimension."""

from typing import Any

TEMPLATES: dict[str, dict[str, Any]] = {
    "accepted_values": {
        "scope": "column",
        "dimension": "validity",
        "requires": ["values"],
        "failure_query": "SELECT COUNT(*) AS failed_rows FROM {table} {filters_with_and} {column} IS NOT NULL AND {column} NOT IN ({accepted_values})",
        "sample_query": "SELECT {column} AS bad_value FROM {table} {filters_with_and} {column} IS NOT NULL AND {column} NOT IN ({accepted_values}) LIMIT 5",
    },
    "numeric_range": {
        "scope": "column",
        "dimension": "validity",
        "requires": ["min_value", "max_value"],
        "failure_query": "SELECT COUNT(*) AS failed_rows FROM {table} {filters_with_and} {column} IS NOT NULL AND ({column} < :min_value OR {column} > :max_value)",
        "sample_query": "SELECT {column} AS bad_value FROM {table} {filters_with_and} {column} IS NOT NULL AND ({column} < :min_value OR {column} > :max_value) LIMIT 5",
    },
    "regex_match": {
        "scope": "column",
        "dimension": "validity",
        "requires": ["pattern"],
        "failure_query": "SELECT COUNT(*) AS failed_rows FROM {table} {filters_with_and} {column} IS NOT NULL AND NOT (CAST({column} AS TEXT) ~ :pattern)",
        "sample_query": "SELECT {column} AS bad_value FROM {table} {filters_with_and} {column} IS NOT NULL AND NOT (CAST({column} AS TEXT) ~ :pattern) LIMIT 5",
    },
    "date_range": {
        "scope": "column",
        "dimension": "validity",
        "requires": ["min_date", "max_date"],
        "failure_query": "SELECT COUNT(*) AS failed_rows FROM {table} {filters_with_and} {column} IS NOT NULL AND ({column} < CAST(:min_date AS timestamp) OR {column} > CAST(:max_date AS timestamp))",
        "sample_query": "SELECT {column} AS bad_value FROM {table} {filters_with_and} {column} IS NOT NULL AND ({column} < CAST(:min_date AS timestamp) OR {column} > CAST(:max_date AS timestamp)) LIMIT 5",
    },
    "not_negative": {
        "scope": "column",
        "dimension": "validity",
        "defaults": {"min_value": 0, "max_value": None},
        "failure_query": "SELECT COUNT(*) AS failed_rows FROM {table} {filters_with_and} {column} IS NOT NULL AND ({column} < :min_value OR (:max_value IS NOT NULL AND {column} > :max_value))",
        "sample_query": "SELECT {column} AS bad_value FROM {table} {filters_with_and} {column} IS NOT NULL AND ({column} < :min_value OR (:max_value IS NOT NULL AND {column} > :max_value)) LIMIT 5",
    },
}
