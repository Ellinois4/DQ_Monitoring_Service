"""DQ checks for the DAMA-DMBOK reasonableness / разумность dimension."""

from typing import Any

TEMPLATES: dict[str, dict[str, Any]] = {
    "row_count_anomaly": {
        "scope": "table",
        "dimension": "reasonableness",
        "requires": ["date_column", "lookback_days", "max_deviation_percent"],
        "checked_query": "SELECT 1 AS checked_rows",
        "failure_query": """
            WITH daily_counts AS (
                SELECT DATE_TRUNC('day', {date_column})::date AS day, COUNT(*) AS row_count
                FROM {table} {filters_with_and}
                     {date_column} >= DATE_TRUNC('day', CURRENT_TIMESTAMP) - (:lookback_days * INTERVAL '1 day')
                 AND {date_column} < DATE_TRUNC('day', CURRENT_TIMESTAMP) + INTERVAL '1 day'
                GROUP BY 1
            ), current_day AS (
                SELECT COALESCE(MAX(row_count) FILTER (WHERE day = CURRENT_DATE), 0) AS current_count
                FROM daily_counts
            ), history AS (
                SELECT AVG(row_count)::numeric AS avg_count
                FROM daily_counts
                WHERE day < CURRENT_DATE
            )
            SELECT CASE
                WHEN history.avg_count IS NULL OR history.avg_count = 0 THEN 0
                WHEN ABS(current_day.current_count - history.avg_count) / history.avg_count * 100 > :max_deviation_percent THEN 1
                ELSE 0
            END AS failed_rows
            FROM current_day CROSS JOIN history
        """,
        "sample_query": """
            WITH daily_counts AS (
                SELECT DATE_TRUNC('day', {date_column})::date AS day, COUNT(*) AS row_count
                FROM {table} {filters_with_and}
                     {date_column} >= DATE_TRUNC('day', CURRENT_TIMESTAMP) - (:lookback_days * INTERVAL '1 day')
                 AND {date_column} < DATE_TRUNC('day', CURRENT_TIMESTAMP) + INTERVAL '1 day'
                GROUP BY 1
            )
            SELECT * FROM daily_counts ORDER BY day DESC LIMIT 10
        """,
    },
    "null_rate_anomaly": {
        "scope": "column",
        "dimension": "reasonableness",
        "requires": ["date_column", "lookback_days", "max_increase_percent"],
        "checked_query": "SELECT 1 AS checked_rows",
        "failure_query": """
            WITH rates AS (
                SELECT DATE_TRUNC('day', {date_column})::date AS day,
                       COUNT(*) AS total_rows,
                       COUNT(*) FILTER (WHERE {column} IS NULL) AS null_rows
                FROM {table} {filters_with_and}
                     {date_column} >= DATE_TRUNC('day', CURRENT_TIMESTAMP) - (:lookback_days * INTERVAL '1 day')
                 AND {date_column} < DATE_TRUNC('day', CURRENT_TIMESTAMP) + INTERVAL '1 day'
                GROUP BY 1
            ), current_day AS (
                SELECT COALESCE(MAX(null_rows::numeric / NULLIF(total_rows, 0) * 100) FILTER (WHERE day = CURRENT_DATE), 0) AS current_null_rate
                FROM rates
            ), history AS (
                SELECT AVG(null_rows::numeric / NULLIF(total_rows, 0) * 100) AS avg_null_rate
                FROM rates
                WHERE day < CURRENT_DATE
            )
            SELECT CASE
                WHEN history.avg_null_rate IS NULL THEN 0
                WHEN current_day.current_null_rate - history.avg_null_rate > :max_increase_percent THEN 1
                ELSE 0
            END AS failed_rows
            FROM current_day CROSS JOIN history
        """,
        "sample_query": """
            WITH rates AS (
                SELECT DATE_TRUNC('day', {date_column})::date AS day,
                       COUNT(*) AS total_rows,
                       COUNT(*) FILTER (WHERE {column} IS NULL) AS null_rows,
                       ROUND(COUNT(*) FILTER (WHERE {column} IS NULL)::numeric / NULLIF(COUNT(*), 0) * 100, 4) AS null_rate
                FROM {table} {filters_with_and}
                     {date_column} >= DATE_TRUNC('day', CURRENT_TIMESTAMP) - (:lookback_days * INTERVAL '1 day')
                 AND {date_column} < DATE_TRUNC('day', CURRENT_TIMESTAMP) + INTERVAL '1 day'
                GROUP BY 1
            )
            SELECT * FROM rates ORDER BY day DESC LIMIT 10
        """,
    },
}
