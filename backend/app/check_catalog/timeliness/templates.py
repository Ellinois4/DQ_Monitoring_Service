"""DQ checks for the DAMA-DMBOK timeliness / актуальность dimension."""

from typing import Any

TEMPLATES: dict[str, dict[str, Any]] = {
    "sla_delivery": {
        "scope": "table",
        "dimension": "timeliness",
        "requires": ["frequency", "delivery_time", "tolerance_hours", "timestamp_column"],
        "defaults": {"weekday": 1, "day_of_month": 1},
        "uses_freshness_column": True,
        "checked_query": "SELECT 1 AS checked_rows",
        "failure_query": """
            WITH stats AS (
                SELECT MAX({timestamp_column}) AS last_update
                FROM {table} {filters}
            ), p AS (
                SELECT LOWER(CAST(:frequency AS text)) AS frequency,
                       CAST(:delivery_time AS time) AS delivery_time,
                       (:tolerance_hours * INTERVAL '1 hour') AS tolerance_interval,
                       CAST(:weekday AS integer) AS weekday,
                       CAST(:day_of_month AS integer) AS day_of_month
            ), calc AS (
                SELECT s.last_update,
                       CASE
                         WHEN p.frequency = 'daily' THEN TRUE
                         WHEN p.frequency = 'weekly' THEN EXTRACT(ISODOW FROM CURRENT_TIMESTAMP)::integer = p.weekday
                         WHEN p.frequency = 'monthly' THEN EXTRACT(DAY FROM CURRENT_TIMESTAMP)::integer = p.day_of_month
                         ELSE FALSE
                       END AS due_day,
                       CASE
                         WHEN p.frequency = 'daily' THEN DATE_TRUNC('day', CURRENT_TIMESTAMP)
                         WHEN p.frequency = 'weekly' THEN DATE_TRUNC('week', CURRENT_TIMESTAMP)
                         WHEN p.frequency = 'monthly' THEN DATE_TRUNC('month', CURRENT_TIMESTAMP)
                         ELSE DATE_TRUNC('day', CURRENT_TIMESTAMP)
                       END AS required_since,
                       p.delivery_time,
                       p.tolerance_interval
                FROM stats s CROSS JOIN p
            )
            SELECT CASE
                WHEN NOT due_day THEN 0
                WHEN CURRENT_TIME <= delivery_time + tolerance_interval THEN 0
                WHEN last_update IS NOT NULL AND last_update >= required_since THEN 0
                ELSE 1
            END AS failed_rows
            FROM calc
        """,
        "sample_query": """
            WITH stats AS (
                SELECT MAX({timestamp_column}) AS last_update
                FROM {table} {filters}
            ), p AS (
                SELECT LOWER(CAST(:frequency AS text)) AS frequency,
                       CAST(:delivery_time AS time) AS delivery_time,
                       (:tolerance_hours * INTERVAL '1 hour') AS tolerance_interval,
                       CAST(:weekday AS integer) AS weekday,
                       CAST(:day_of_month AS integer) AS day_of_month
            )
            SELECT s.last_update, p.frequency, p.delivery_time, p.tolerance_interval,
                   CASE
                     WHEN p.frequency = 'daily' THEN DATE_TRUNC('day', CURRENT_TIMESTAMP)
                     WHEN p.frequency = 'weekly' THEN DATE_TRUNC('week', CURRENT_TIMESTAMP)
                     WHEN p.frequency = 'monthly' THEN DATE_TRUNC('month', CURRENT_TIMESTAMP)
                     ELSE DATE_TRUNC('day', CURRENT_TIMESTAMP)
                   END AS required_since
            FROM stats s CROSS JOIN p
            LIMIT 1
        """,
    },
    "table_freshness": {
        "scope": "table",
        "dimension": "timeliness",
        "requires": ["timestamp_column", "max_age_hours"],
        "uses_freshness_column": True,
        "checked_query": "SELECT 1 AS checked_rows",
        "failure_query": """
            SELECT CASE
                WHEN MAX({timestamp_column}) IS NULL THEN 1
                WHEN MAX({timestamp_column}) < CURRENT_TIMESTAMP - (:max_age_hours * INTERVAL '1 hour') THEN 1
                ELSE 0
            END AS failed_rows
            FROM {table} {filters}
        """,
        "sample_query": """
            SELECT MAX({timestamp_column}) AS last_update,
                   CURRENT_TIMESTAMP - (:max_age_hours * INTERVAL '1 hour') AS freshness_threshold
            FROM {table} {filters}
        """,
    },
    "stale_status": {
        "scope": "table",
        "dimension": "timeliness",
        "requires": ["start_timestamp_column", "end_timestamp_column", "max_delay_hours"],
        "failure_query": """
            SELECT COUNT(*) AS failed_rows
            FROM {table} {filters_with_and}
                 {start_timestamp_column} IS NOT NULL
             AND {end_timestamp_column} IS NOT NULL
             AND ({end_timestamp_column} - {start_timestamp_column}) > (:max_delay_hours * INTERVAL '1 hour')
        """,
        "sample_query": """
            SELECT {start_timestamp_column} AS start_timestamp,
                   {end_timestamp_column} AS end_timestamp,
                   ({end_timestamp_column} - {start_timestamp_column}) AS actual_delay
            FROM {table} {filters_with_and}
                 {start_timestamp_column} IS NOT NULL
             AND {end_timestamp_column} IS NOT NULL
             AND ({end_timestamp_column} - {start_timestamp_column}) > (:max_delay_hours * INTERVAL '1 hour')
            LIMIT 5
        """,
    },
    "future_timestamp": {
        "scope": "column",
        "dimension": "timeliness",
        "defaults": {"allowed_future_minutes": 0},
        "failure_query": """
            SELECT COUNT(*) AS failed_rows
            FROM {table} {filters_with_and}
                 {column} > CURRENT_TIMESTAMP + (:allowed_future_minutes * INTERVAL '1 minute')
        """,
        "sample_query": """
            SELECT {column} AS future_value
            FROM {table} {filters_with_and}
                 {column} > CURRENT_TIMESTAMP + (:allowed_future_minutes * INTERVAL '1 minute')
            ORDER BY {column} DESC
            LIMIT 5
        """,
    },
}
