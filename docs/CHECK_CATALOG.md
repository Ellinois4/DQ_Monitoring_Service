# Каталог DQ-проверок

Проверки разделены по измерениям качества данных DAMA-DMBOK. Кодовые шаблоны лежат в `backend/app/check_catalog/`.

## Структура каталогов

```text
backend/app/check_catalog/
├── timeliness/       # актуальность и временные проверки
├── validity/         # консистентность / допустимость значений
├── completeness/     # полнота
├── reasonableness/   # разумность и аномалии
├── consistency/      # согласованность
├── conformity/       # соответствие справочникам
├── uniqueness/       # уникальность
└── integrity/        # целостность и связи
```

## Реализованные проверки

### Актуальность

- `sla_delivery` — контроль SLA доставки таблицы по частоте, времени доставки и допустимой погрешности.
- `table_freshness` — контроль последнего обновления таблицы.
- `stale_status` — контроль превышения допустимой разницы между двумя временными полями.
- `future_timestamp` — поиск дат из будущего.

### Консистентность / допустимость

- `accepted_values` — проверка допустимого множества значений.
- `numeric_range` — проверка числового диапазона.
- `regex_match` — проверка регулярным выражением.
- `date_range` — проверка допустимого диапазона дат.
- `not_negative` — проверка неотрицательного значения или одностороннего числового ограничения.

### Полнота

- `not_null` — отсутствие `NULL`.
- `not_blank` — отсутствие пустых строк.
- `conditional_not_null` — поле обязательно при выполнении условия.
- `expected_columns_present` — наличие обязательных столбцов.
- `column_fill_rate` — минимальный процент заполненности.

### Разумность

- `row_count_anomaly` — аномалия количества строк за текущий день относительно истории.
- `null_rate_anomaly` — аномальный рост доли `NULL` относительно истории.

### Согласованность

- `cross_field_comparison` — сравнение двух полей в одной записи.
- `same_entity_same_attribute` — стабильный атрибут одной сущности не должен иметь несколько значений.
- `mutually_exclusive_fields` — взаимоисключающие поля не должны быть заполнены одновременно.

### Соответствие

- `reference_match` — проверка соответствия значения справочнику.

### Уникальность

- `unique` — уникальность одного поля.
- `composite_unique` — уникальность комбинации полей.
- `duplicate_rows` — полные дубликаты строк по выбранным колонкам.
- `case_insensitive_unique` — уникальность без учета регистра и внешних пробелов.

### Целостность

- `foreign_key_exists` — проверка ссылочной целостности.
- `parent_has_child` — наличие дочерних записей у родительской сущности.
- `required_link_exists` — наличие обязательной связи при выполнении условия.

## Пример параметров

### SLA доставки таблицы

```json
{
  "frequency": "daily",
  "delivery_time": "12:00",
  "tolerance_hours": 3,
  "timestamp_column": "updated_at"
}
```

Для еженедельного SLA:

```json
{
  "frequency": "weekly",
  "weekday": 1,
  "delivery_time": "12:00",
  "tolerance_hours": 3,
  "timestamp_column": "updated_at"
}
```

### Условная полнота

```json
{
  "condition_column": "country_code",
  "condition_operator": "=",
  "condition_value": "IE"
}
```

### Справочник

```json
{
  "reference_schema": "demo",
  "reference_table": "ref_country",
  "reference_column": "country_code"
}
```

### Составная уникальность

```json
{
  "columns": ["customer_id", "email"]
}
```
