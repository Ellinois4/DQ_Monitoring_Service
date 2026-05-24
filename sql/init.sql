-- Описание источников данных
CREATE TABLE IF NOT EXISTS dq_datasource (
    datasource_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    db_type VARCHAR(50) NOT NULL DEFAULT 'postgresql',
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- Описание проверяемых таблиц
CREATE TABLE IF NOT EXISTS dq_dataset (
    dataset_id SERIAL PRIMARY KEY,
    datasource_id INTEGER NOT NULL REFERENCES dq_datasource(datasource_id),
    schema_name VARCHAR(100) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    display_name VARCHAR(150) NOT NULL,
    owner_name VARCHAR(150),
    criticality VARCHAR(20) NOT NULL DEFAULT 'medium',
    freshness_column VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Описание атрибутов для проверок
CREATE TABLE IF NOT EXISTS dq_attribute (
    attribute_id SERIAL PRIMARY KEY,
    dataset_id INTEGER NOT NULL REFERENCES dq_dataset(dataset_id),
    column_name VARCHAR(100) NOT NULL,
    data_type VARCHAR(100) NOT NULL,
    is_nullable BOOLEAN NOT NULL DEFAULT TRUE
);

-- Поддерживаемые типы проверок
CREATE TABLE IF NOT EXISTS dq_check_type (
    check_type_id SERIAL PRIMARY KEY,
    code VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(150) NOT NULL,
    dimension_name VARCHAR(100) NOT NULL,
    level_scope VARCHAR(20) NOT NULL,
    description TEXT,
    param_schema JSONB
);

-- Настройки уведомлений
CREATE TABLE IF NOT EXISTS dq_notification_rule (
    notification_rule_id SERIAL PRIMARY KEY,
    email_to VARCHAR(255) NOT NULL,
    phone_number VARCHAR(50),
    notify_on_status VARCHAR(20) NOT NULL DEFAULT 'failed',
    critical_only BOOLEAN NOT NULL DEFAULT FALSE
);

-- Настроенные проверки
CREATE TABLE IF NOT EXISTS dq_check_config (
    check_config_id SERIAL PRIMARY KEY,
    dataset_id INTEGER NOT NULL REFERENCES dq_dataset(dataset_id),
    attribute_id INTEGER REFERENCES dq_attribute(attribute_id),
    check_type_id INTEGER NOT NULL REFERENCES dq_check_type(check_type_id),
    notification_rule_id INTEGER REFERENCES dq_notification_rule(notification_rule_id),
    check_name VARCHAR(150) NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'warning',
    threshold_percent NUMERIC(10,4) NOT NULL DEFAULT 0,
    filter_clause JSONB,
    params JSONB,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    schedule_type VARCHAR(30) NOT NULL DEFAULT 'manual',
    schedule_interval_minutes INTEGER,
    schedule_time TIME,
    schedule_day_of_week INTEGER,
    schedule_day_of_month INTEGER,
    schedule_timezone VARCHAR(50) NOT NULL DEFAULT 'Europe/Moscow',
    last_run_at TIMESTAMP,
    CONSTRAINT dq_check_config_schedule_type_chk
        CHECK (schedule_type IN ('manual', 'interval', 'daily', 'weekly', 'monthly')),
    CONSTRAINT dq_check_config_weekday_chk
        CHECK (schedule_day_of_week IS NULL OR schedule_day_of_week BETWEEN 1 AND 7),
    CONSTRAINT dq_check_config_monthday_chk
        CHECK (schedule_day_of_month IS NULL OR schedule_day_of_month BETWEEN 1 AND 31)
);


ALTER TABLE dq_check_config ADD COLUMN IF NOT EXISTS schedule_type VARCHAR(30) NOT NULL DEFAULT 'manual';
ALTER TABLE dq_check_config ADD COLUMN IF NOT EXISTS schedule_time TIME;
ALTER TABLE dq_check_config ADD COLUMN IF NOT EXISTS schedule_day_of_week INTEGER;
ALTER TABLE dq_check_config ADD COLUMN IF NOT EXISTS schedule_day_of_month INTEGER;
ALTER TABLE dq_check_config ADD COLUMN IF NOT EXISTS schedule_timezone VARCHAR(50) NOT NULL DEFAULT 'Europe/Moscow';

-- история запусков проверок
CREATE TABLE IF NOT EXISTS dq_check_run (
    run_id SERIAL PRIMARY KEY,
    check_config_id INTEGER NOT NULL REFERENCES dq_check_config(check_config_id),
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMP,
    status VARCHAR(20) NOT NULL,
    executed_sql TEXT,
    error_message TEXT,
    trigger_mode VARCHAR(20) NOT NULL DEFAULT 'manual'
);

-- результаты проверок
CREATE TABLE IF NOT EXISTS dq_check_result (
    result_id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL UNIQUE REFERENCES dq_check_run(run_id),
    checked_rows INTEGER NOT NULL,
    failed_rows INTEGER NOT NULL,
    failed_percent NUMERIC(10,4) NOT NULL,
    status VARCHAR(20) NOT NULL,
    sample_payload JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);


-- Служебная БД содержит только метаданные сервиса.
-- Проверяемые данные и demo-таблицы создаются в отдельной БД dq_target.

INSERT INTO dq_datasource (name, db_type, description)
VALUES ('Target PostgreSQL', 'postgresql', 'External target data source with checked tables')
ON CONFLICT (name) DO NOTHING;

INSERT INTO dq_dataset (datasource_id, schema_name, table_name, display_name, owner_name, criticality, freshness_column)
SELECT datasource_id, 'demo', 'customers_raw', 'Demo customers', 'Data Platform', 'high', 'updated_at'
FROM dq_datasource
WHERE name = 'Target PostgreSQL'
AND NOT EXISTS (
    SELECT 1 FROM dq_dataset WHERE schema_name = 'demo' AND table_name = 'customers_raw'
);

INSERT INTO dq_attribute (dataset_id, column_name, data_type, is_nullable)
SELECT d.dataset_id, x.column_name, x.data_type, x.is_nullable
FROM dq_dataset d
CROSS JOIN (
    VALUES
        ('customer_id', 'integer', false),
        ('email', 'text', true),
        ('country_code', 'text', true),
        ('age', 'integer', true),
        ('updated_at', 'timestamp', false)
) AS x(column_name, data_type, is_nullable)
WHERE d.schema_name = 'demo'
  AND d.table_name = 'customers_raw'
  AND NOT EXISTS (
      SELECT 1 FROM dq_attribute a WHERE a.dataset_id = d.dataset_id AND a.column_name = x.column_name
  );

-- Регистрируем демонстрационную таблицу с большим набором типовых дефектов.
INSERT INTO dq_dataset (datasource_id, schema_name, table_name, display_name, owner_name, criticality, freshness_column)
SELECT datasource_id, 'demo', 'dq_demo_orders', 'DQ demo orders', 'Data Platform', 'high', 'updated_at'
FROM dq_datasource
WHERE name = 'Target PostgreSQL'
AND NOT EXISTS (
    SELECT 1 FROM dq_dataset WHERE schema_name = 'demo' AND table_name = 'dq_demo_orders'
);

INSERT INTO dq_attribute (dataset_id, column_name, data_type, is_nullable)
SELECT d.dataset_id, x.column_name, x.data_type, x.is_nullable
FROM dq_dataset d
CROSS JOIN (
    VALUES
        ('order_id', 'integer', false),
        ('customer_id', 'integer', false),
        ('email', 'text', true),
        ('country_code', 'text', true),
        ('age', 'integer', true),
        ('amount', 'numeric', true),
        ('status', 'text', true),
        ('payment_id', 'integer', true),
        ('created_at', 'timestamp', true),
        ('updated_at', 'timestamp', true),
        ('processed_at', 'timestamp', true),
        ('delivered_at', 'timestamp', true),
        ('birth_date', 'date', true),
        ('person_inn', 'text', true),
        ('company_inn', 'text', true),
        ('stable_segment', 'text', true),
        ('product_code', 'text', true)
) AS x(column_name, data_type, is_nullable)
WHERE d.schema_name = 'demo'
  AND d.table_name = 'dq_demo_orders'
  AND NOT EXISTS (
      SELECT 1 FROM dq_attribute a WHERE a.dataset_id = d.dataset_id AND a.column_name = x.column_name
  );

INSERT INTO dq_check_type (code, name, dimension_name, level_scope, description, param_schema)
VALUES
    -- Актуальность
    ('sla_delivery', 'SLA delivery', 'timeliness', 'table', 'Checks that a table is delivered by an expected time with tolerance', '{"frequency":"daily|weekly|monthly","delivery_time":"HH:MM","tolerance_hours":"number","timestamp_column":"column","weekday":"1-7 optional","day_of_month":"1-31 optional"}'::jsonb),
    ('table_freshness', 'Table freshness', 'timeliness', 'table', 'Checks the latest update timestamp of a table', '{"timestamp_column":"column","max_age_hours":"number"}'::jsonb),
    ('stale_status', 'Stale status / excessive delay', 'timeliness', 'table', 'Checks that difference between two timestamp columns is not greater than allowed period', '{"start_timestamp_column":"column","end_timestamp_column":"column","max_delay_hours":"number"}'::jsonb),
    ('future_timestamp', 'Future timestamp', 'timeliness', 'column', 'Checks that timestamp values are not in the future', '{"allowed_future_minutes":"number optional"}'::jsonb),

    -- Консистентность / допустимость
    ('accepted_values', 'Accepted values', 'validity', 'column', 'Checks membership in a predefined value list', '{"values":"array"}'::jsonb),
    ('numeric_range', 'Numeric range', 'validity', 'column', 'Checks numeric range min/max', '{"min_value":"number","max_value":"number"}'::jsonb),
    ('regex_match', 'Regex match', 'validity', 'column', 'Checks that values match a regular expression', '{"pattern":"regex"}'::jsonb),
    ('date_range', 'Date range', 'validity', 'column', 'Checks that dates are inside an allowed interval', '{"min_date":"timestamp","max_date":"timestamp"}'::jsonb),
    ('not_negative', 'Not negative / one-sided numeric bound', 'validity', 'column', 'Checks that numeric values are greater than or equal to a lower bound', '{"min_value":"number optional default 0","max_value":"number optional"}'::jsonb),

    -- Полнота
    ('not_null', 'Not null', 'completeness', 'column', 'Counts NULL values in a selected column', '{}'::jsonb),
    ('not_blank', 'Not blank', 'completeness', 'column', 'Counts empty strings in a selected text column', '{}'::jsonb),
    ('conditional_not_null', 'Conditional not null', 'completeness', 'column', 'Checks that a field is filled when a condition is true', '{"condition_column":"column","condition_operator":"operator","condition_value":"value optional","condition_values":"array optional"}'::jsonb),
    ('expected_columns_present', 'Expected columns present', 'completeness', 'table', 'Checks that required table columns exist', '{"required_columns":"array"}'::jsonb),
    ('column_fill_rate', 'Column fill rate', 'completeness', 'column', 'Checks minimum fill percentage of a selected column', '{"min_fill_percent":"number"}'::jsonb),

    -- Разумность
    ('row_count_anomaly', 'Row count anomaly', 'reasonableness', 'table', 'Detects abnormal row count for the current day compared with history', '{"date_column":"column","lookback_days":"integer","max_deviation_percent":"number"}'::jsonb),
    ('null_rate_anomaly', 'Null rate anomaly', 'reasonableness', 'column', 'Detects abnormal growth of NULL rate compared with history', '{"date_column":"column","lookback_days":"integer","max_increase_percent":"number"}'::jsonb),

    -- Согласованность
    ('cross_field_comparison', 'Cross-field comparison', 'consistency', 'table', 'Compares two fields inside one row using a selected operator', '{"left_column":"column","operator":"=|!=|>|>=|<|<=","right_column":"column"}'::jsonb),
    ('same_entity_same_attribute', 'Same entity same attribute', 'consistency', 'table', 'Checks that a stable attribute has one value for the same entity key', '{"entity_key_column":"column","stable_attribute_column":"column"}'::jsonb),
    ('mutually_exclusive_fields', 'Mutually exclusive fields', 'consistency', 'table', 'Checks that no more than one field from a group is filled', '{"columns":"array"}'::jsonb),

    -- Соответствие
    ('reference_match', 'Reference match', 'conformity', 'column', 'Checks that values exist in a reference dictionary', '{"reference_schema":"schema","reference_table":"table","reference_column":"column"}'::jsonb),

    -- Уникальность
    ('unique', 'Unique values', 'uniqueness', 'column', 'Counts duplicate values for a selected column', '{}'::jsonb),
    ('composite_unique', 'Composite unique', 'uniqueness', 'table', 'Checks uniqueness of a combination of columns', '{"columns":"array"}'::jsonb),
    ('duplicate_rows', 'Duplicate rows', 'uniqueness', 'table', 'Checks full duplicate rows by selected columns', '{"columns":"array"}'::jsonb),
    ('case_insensitive_unique', 'Case-insensitive unique', 'uniqueness', 'column', 'Checks uniqueness after lower-case and trim normalization', '{}'::jsonb),

    -- Целостность
    ('foreign_key_exists', 'Foreign key exists', 'integrity', 'column', 'Checks that a foreign key value exists in a referenced table', '{"reference_schema":"schema","reference_table":"table","reference_column":"column"}'::jsonb),
    ('parent_has_child', 'Parent has child', 'integrity', 'table', 'Checks that each parent row has at least one child row', '{"parent_key_column":"column","child_schema":"schema","child_table":"table","child_key_column":"column"}'::jsonb),
    ('required_link_exists', 'Required link exists', 'integrity', 'table', 'Checks that a required related record exists when a condition is true', '{"condition_column":"column","condition_operator":"operator","condition_value":"value optional","link_column":"column","reference_schema":"schema","reference_table":"table","reference_column":"column"}'::jsonb)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    dimension_name = EXCLUDED.dimension_name,
    level_scope = EXCLUDED.level_scope,
    description = EXCLUDED.description,
    param_schema = EXCLUDED.param_schema;

INSERT INTO dq_notification_rule (email_to, phone_number, notify_on_status, critical_only)
SELECT 'owner@example.com', '+3530000000', 'failed', false
WHERE NOT EXISTS (SELECT 1 FROM dq_notification_rule WHERE email_to = 'owner@example.com');


