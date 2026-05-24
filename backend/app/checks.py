import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from . import models
from .db import target_engine
from .check_catalog import TEMPLATES

IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
ALLOWED_FILTER_OPERATORS = {
    "=", "!=", "<>", ">", ">=", "<", "<=", "like", "ilike", "in", "not_in",
    "is_null", "is_not_null", "is_blank", "is_not_blank",
}
ALLOWED_COMPARISON_OPERATORS = {"=", "!=", "<>", ">", ">=", "<", "<="}


def sql_literal(value: Any) -> str:
    """Return a readable SQL literal for UI display only. Execution still uses bind parameters."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    if isinstance(value, (datetime, date)):
        return "'" + value.isoformat().replace("'", "''") + "'"
    if isinstance(value, (list, tuple)):
        return "(" + ", ".join(sql_literal(item) for item in value) + ")"
    return "'" + str(value).replace("'", "''") + "'"


def bind_params_for_display(sql: str, params: dict[str, Any]) -> str:
    """Substitute :param placeholders in SQL text for copyable UI display."""
    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in params:
            return match.group(0)
        return sql_literal(params[name])

    return re.sub(r":([A-Za-z_][A-Za-z0-9_]*)", replace, sql)


@dataclass
class RenderedQuery:
    checked_query: str
    failed_query: str
    sample_query: str
    params: dict[str, Any]


class CheckTemplateError(ValueError):
    pass


def to_jsonable(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    return value


def safe_identifier(value: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER_RE.match(value):
        raise CheckTemplateError(f"Unsafe SQL identifier: {value}")
    return value


def table_ref(schema_name: str, table_name: str) -> str:
    return f'"{safe_identifier(schema_name)}"."{safe_identifier(table_name)}"'


def column_ref(column_name: str) -> str:
    return f'"{safe_identifier(column_name)}"'


def qualified_column(column_name: str, alias: str | None = None) -> str:
    column = column_ref(column_name)
    return f"{safe_identifier(alias)}.{column}" if alias else column


def _nonblank_expr(column_sql: str) -> str:
    return f"({column_sql} IS NOT NULL AND BTRIM(CAST({column_sql} AS TEXT)) <> '')"


def _operator_to_sql(operator: str) -> str:
    op = operator.lower()
    if op == "!=":
        return "<>"
    return op.upper()


def build_filter_condition(
    filter_clause: dict[str, Any] | None,
    *,
    alias: str | None = None,
    param_prefix: str = "filter",
) -> tuple[str, dict[str, Any]]:
    """Builds only the boolean condition without WHERE."""
    if not filter_clause:
        return "", {}

    conditions = filter_clause.get("conditions", [])
    sql_parts: list[str] = []
    params: dict[str, Any] = {}

    for idx, item in enumerate(conditions):
        field = qualified_column(item["field"], alias)
        operator = str(item["operator"]).lower()
        if operator not in ALLOWED_FILTER_OPERATORS:
            raise CheckTemplateError(f"Unsupported filter operator: {operator}")

        param_name = f"{param_prefix}_{idx}"
        if operator in {"is_null", "is_not_null", "is_blank", "is_not_blank"}:
            if operator == "is_null":
                sql_parts.append(f"{field} IS NULL")
            elif operator == "is_not_null":
                sql_parts.append(f"{field} IS NOT NULL")
            elif operator == "is_blank":
                sql_parts.append(f"({field} IS NULL OR BTRIM(CAST({field} AS TEXT)) = '')")
            else:
                sql_parts.append(_nonblank_expr(field))
        elif operator in {"in", "not_in"}:
            values = item.get("value", [])
            if not isinstance(values, list) or not values:
                raise CheckTemplateError("IN filter requires a non-empty list")
            placeholders = []
            for sub_idx, value in enumerate(values):
                key = f"{param_name}_{sub_idx}"
                placeholders.append(f":{key}")
                params[key] = value
            keyword = "NOT IN" if operator == "not_in" else "IN"
            sql_parts.append(f"{field} {keyword} ({', '.join(placeholders)})")
        else:
            sql_parts.append(f"{field} {_operator_to_sql(operator)} :{param_name}")
            params[param_name] = item.get("value")

    return " AND ".join(sql_parts), params


def build_filter_clause(filter_clause: dict[str, Any] | None) -> tuple[str, str, dict[str, Any]]:
    condition, params = build_filter_condition(filter_clause)
    if not condition:
        return "", "WHERE ", params
    return f"WHERE {condition}", f"WHERE {condition} AND ", params


def build_condition_predicate(
    params: dict[str, Any],
    *,
    alias: str | None = None,
    param_prefix: str = "condition",
) -> tuple[str, dict[str, Any]]:
    """Builds a safe predicate from params: condition_column/operator/value(s)."""
    if "condition_column" not in params or "condition_operator" not in params:
        raise CheckTemplateError("condition_column and condition_operator are required")

    field = qualified_column(str(params["condition_column"]), alias)
    operator = str(params["condition_operator"]).lower()
    if operator not in ALLOWED_FILTER_OPERATORS:
        raise CheckTemplateError(f"Unsupported condition operator: {operator}")

    extra_params: dict[str, Any] = {}
    if operator == "is_null":
        return f"{field} IS NULL", extra_params
    if operator == "is_not_null":
        return f"{field} IS NOT NULL", extra_params
    if operator == "is_blank":
        return f"({field} IS NULL OR BTRIM(CAST({field} AS TEXT)) = '')", extra_params
    if operator == "is_not_blank":
        return _nonblank_expr(field), extra_params

    if operator in {"in", "not_in"}:
        values = params.get("condition_values", params.get("condition_value", []))
        if not isinstance(values, list) or not values:
            raise CheckTemplateError("Condition IN requires condition_values list")
        placeholders = []
        for idx, value in enumerate(values):
            key = f"{param_prefix}_{idx}"
            placeholders.append(f":{key}")
            extra_params[key] = value
        keyword = "NOT IN" if operator == "not_in" else "IN"
        return f"{field} {keyword} ({', '.join(placeholders)})", extra_params

    if "condition_value" not in params:
        raise CheckTemplateError("condition_value is required for this condition operator")
    key = f"{param_prefix}_value"
    extra_params[key] = params["condition_value"]
    return f"{field} {_operator_to_sql(operator)} :{key}", extra_params


def _build_values_placeholders(values: list[Any], params: dict[str, Any], prefix: str) -> str:
    placeholders = []
    for idx, value in enumerate(values):
        key = f"{prefix}_{idx}"
        params[key] = value
        placeholders.append(f":{key}")
    return ", ".join(placeholders) or "NULL"


def _build_values_rows(values: list[Any], params: dict[str, Any], prefix: str) -> str:
    placeholders = []
    for idx, value in enumerate(values):
        key = f"{prefix}_{idx}"
        params[key] = value
        placeholders.append(f"(:{key})")
    if not placeholders:
        raise CheckTemplateError(f"{prefix} requires a non-empty list")
    return ", ".join(placeholders)


def _build_columns_list(values: Any) -> str:
    if not isinstance(values, list) or not values:
        raise CheckTemplateError("columns parameter must be a non-empty list")
    return ", ".join(column_ref(str(value)) for value in values)


def _build_nonempty_columns_count(values: Any) -> str:
    if not isinstance(values, list) or not values:
        raise CheckTemplateError("columns parameter must be a non-empty list")
    parts = [
        f"CASE WHEN {_nonblank_expr(column_ref(str(value)))} THEN 1 ELSE 0 END"
        for value in values
    ]
    return " + ".join(parts)


def build_context(
    config: models.CheckConfig,
    template: dict[str, Any],
    params: dict[str, Any],
    filters: str,
    filters_with_and: str,
    alias_filter_condition: str,
) -> dict[str, Any]:
    table = table_ref(config.dataset.schema_name, config.dataset.table_name)
    context: dict[str, Any] = {
        "table": table,
        "filters": filters,
        "filters_with_and": filters_with_and,
        "where_keyword": "WHERE",
        "filters_after_alias": f" AND {alias_filter_condition}" if alias_filter_condition else "",
    }

    params["dataset_schema"] = config.dataset.schema_name
    params["dataset_table"] = config.dataset.table_name

    if template.get("uses_freshness_column") and "timestamp_column" not in params:
        if not config.dataset.freshness_column:
            raise CheckTemplateError("timestamp_column is required because dataset.freshness_column is not set")
        params["timestamp_column"] = config.dataset.freshness_column

    # Main attribute selected in UI for column-level checks.
    if template["scope"] == "column":
        if not config.attribute:
            raise CheckTemplateError("This check requires an attribute")
        context["column"] = column_ref(config.attribute.column_name)
    else:
        context["column"] = ""

    # Convert *_column parameters to safe identifiers.
    for key, value in list(params.items()):
        if key.endswith("_column") and isinstance(value, str):
            context[key] = column_ref(value)

    # Convert list of columns to comma-separated safe identifiers.
    if "columns" in params:
        context["columns"] = _build_columns_list(params["columns"])
        context["nonempty_columns_count"] = _build_nonempty_columns_count(params["columns"])

    # Accepted values.
    if "values" in params and isinstance(params["values"], list):
        context["accepted_values"] = _build_values_placeholders(params["values"], params, "accepted")

    # Expected columns for schema completeness check.
    if "required_columns" in params and isinstance(params["required_columns"], list):
        context["required_columns_values"] = _build_values_rows(params["required_columns"], params, "required_column")

    # Reference and child tables.
    if "reference_schema" in params and "reference_table" in params:
        context["reference_table_ref"] = table_ref(str(params["reference_schema"]), str(params["reference_table"]))
    if "child_schema" in params and "child_table" in params:
        context["child_table_ref"] = table_ref(str(params["child_schema"]), str(params["child_table"]))

    # Comparison operator between two fields.
    if "operator" in params:
        operator = str(params["operator"])
        if operator not in ALLOWED_COMPARISON_OPERATORS:
            raise CheckTemplateError(f"Unsupported comparison operator: {operator}")
        context["comparison_operator"] = _operator_to_sql(operator)

    # Conditional predicates.
    if "condition_column" in params:
        condition_predicate, condition_params = build_condition_predicate(params)
        params.update(condition_params)
        condition_predicate_alias, alias_condition_params = build_condition_predicate(
            params,
            alias="src",
            param_prefix="condition_alias",
        )
        params.update(alias_condition_params)
        context["condition_predicate"] = condition_predicate
        context["condition_predicate_alias"] = condition_predicate_alias

    # Defaults for placeholders used by some templates.
    context.setdefault("accepted_values", "NULL")
    context.setdefault("required_columns_values", "('')")
    context.setdefault("reference_table_ref", "")
    context.setdefault("child_table_ref", "")
    context.setdefault("comparison_operator", "=")
    context.setdefault("nonempty_columns_count", "0")

    return context


def render_query(config: models.CheckConfig) -> RenderedQuery:
    template = TEMPLATES.get(config.check_type.code)
    if not template:
        raise CheckTemplateError(f"Unsupported check type: {config.check_type.code}")

    params = dict(template.get("defaults", {}))
    params.update(config.params or {})

    filters, filters_with_and, filter_params = build_filter_clause(config.filter_clause)
    alias_filter_condition, _ = build_filter_condition(config.filter_clause, alias="src")
    params.update(filter_params)

    # Fill freshness fallback before required check.
    if template.get("uses_freshness_column") and "timestamp_column" not in params and config.dataset.freshness_column:
        params["timestamp_column"] = config.dataset.freshness_column

    for required_param in template.get("requires", []):
        if required_param not in params or params[required_param] in (None, ""):
            raise CheckTemplateError(f"Missing required parameter: {required_param}")

    context = build_context(config, template, params, filters, filters_with_and, alias_filter_condition)
    table = context["table"]

    checked_query = template.get("checked_query") or f"SELECT COUNT(*) AS checked_rows FROM {table} {filters}"
    checked_query = checked_query.format(**context)

    if "failure_predicate" in template:
        failure_predicate = template["failure_predicate"].format(**context)
        failed_query = f"SELECT COUNT(*) AS failed_rows FROM {table} {filters_with_and} {failure_predicate}"
        sample_query = f"SELECT * FROM {table} {filters_with_and} {failure_predicate} LIMIT 5"
    else:
        failed_query = template["failure_query"].format(**context)
        sample_query = template["sample_query"].format(**context)

    return RenderedQuery(
        checked_query=checked_query,
        failed_query=failed_query,
        sample_query=sample_query,
        params=params,
    )


def execute_check(db: Session, config: models.CheckConfig) -> tuple[str, int, int, float, list[dict[str, Any]]]:
    """Execute a DQ check against the target data database.

    The SQL metadata and check configuration are read using the service database session,
    but the generated DQ SQL is executed through target_engine. This separates the
    service metadata database from the customer/production data database.
    """
    rendered = render_query(config)

    with target_engine.connect() as target_conn:
        checked_rows = target_conn.execute(text(rendered.checked_query), rendered.params).scalar_one()
        failed_rows = target_conn.execute(text(rendered.failed_query), rendered.params).scalar_one()
        samples = [
            to_jsonable(dict(row._mapping))
            for row in target_conn.execute(text(rendered.sample_query), rendered.params).fetchall()
        ]

    failed_percent = round((float(failed_rows) / float(checked_rows)) * 100, 4) if checked_rows else 0.0
    executed_sql = "\n\n".join([
        bind_params_for_display(rendered.checked_query, rendered.params) + ";",
        bind_params_for_display(rendered.failed_query, rendered.params) + ";",
        bind_params_for_display(rendered.sample_query, rendered.params) + ";",
    ])
    return executed_sql, int(checked_rows), int(failed_rows), failed_percent, samples
