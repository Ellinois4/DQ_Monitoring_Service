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
    schedule_interval_minutes INTEGER,
    last_run_at TIMESTAMP
);

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

CREATE SCHEMA IF NOT EXISTS demo;

CREATE TABLE IF NOT EXISTS demo.customers_raw (
    customer_id INTEGER,
    email TEXT,
    country_code TEXT,
    age INTEGER,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

TRUNCATE TABLE demo.customers_raw;
INSERT INTO demo.customers_raw (customer_id, email, country_code, age, updated_at) VALUES
    (1, 'alice@example.com', 'IE', 28, NOW() - INTERVAL '1 day'),
    (2, NULL, 'IE', 34, NOW() - INTERVAL '2 day'),
    (3, 'bob@example.com', 'US', 200, NOW() - INTERVAL '15 day'),
    (4, 'carol@example.com', 'IE', 25, NOW() - INTERVAL '3 day'),
    (4, 'carol.duplicate@example.com', 'IE', 25, NOW() - INTERVAL '3 day'),
    (5, '', 'FR', 31, NOW() - INTERVAL '1 day'),
    (6, 'frank@example.com', 'ZZ', 18, NOW() - INTERVAL '20 day');

CREATE TABLE IF NOT EXISTS demo.ref_country (
    country_code TEXT PRIMARY KEY,
    country_name TEXT NOT NULL
);

TRUNCATE TABLE demo.ref_country;
INSERT INTO demo.ref_country (country_code, country_name) VALUES
    ('IE', 'Ireland'),
    ('US', 'United States'),
    ('FR', 'France'),
    ('DE', 'Germany');

-- Единая демонстрационная таблица для проверки разных измерений качества данных.
-- В таблицу намеренно добавлены ошибки: NULL, пустые строки, дубли, неверные справочные коды,
-- отрицательные суммы, будущие даты, слишком большие задержки и нарушенные связи.
CREATE TABLE IF NOT EXISTS demo.dq_demo_orders (
    order_id INTEGER,
    customer_id INTEGER,
    email TEXT,
    country_code TEXT,
    age INTEGER,
    amount NUMERIC(12,2),
    status TEXT,
    payment_id INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    processed_at TIMESTAMP,
    delivered_at TIMESTAMP,
    birth_date DATE,
    person_inn TEXT,
    company_inn TEXT,
    stable_segment TEXT,
    product_code TEXT
);

CREATE TABLE IF NOT EXISTS demo.demo_customers (
    customer_id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS demo.demo_payments (
    payment_id INTEGER PRIMARY KEY,
    paid_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS demo.demo_order_items (
    order_item_id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    product_code TEXT NOT NULL,
    quantity INTEGER NOT NULL
);

TRUNCATE TABLE demo.dq_demo_orders;
TRUNCATE TABLE demo.demo_customers;
TRUNCATE TABLE demo.demo_payments;
TRUNCATE TABLE demo.demo_order_items;

INSERT INTO demo.demo_customers (customer_id, full_name) VALUES
    (1, 'Alice Green'),
    (2, 'Bob Smith'),
    (3, 'Carol White'),
    (4, 'David Black');

INSERT INTO demo.demo_payments (payment_id, paid_at) VALUES
    (9001, NOW() - INTERVAL '1 day'),
    (9003, NOW() - INTERVAL '2 days');

INSERT INTO demo.demo_order_items (order_item_id, order_id, product_code, quantity) VALUES
    (1, 1001, 'P-100', 1),
    (2, 1001, 'P-200', 2),
    (3, 1003, 'P-300', 1),
    (4, 1004, 'P-400', 3);

INSERT INTO demo.dq_demo_orders (
    order_id, customer_id, email, country_code, age, amount, status, payment_id,
    created_at, updated_at, processed_at, delivered_at, birth_date,
    person_inn, company_inn, stable_segment, product_code
) VALUES
    -- корректная запись
    (1001, 1, 'alice@example.com', 'IE', 28, 120.50, 'paid', 9001,
     NOW() - INTERVAL '1 day', NOW() - INTERVAL '1 day', NOW() - INTERVAL '23 hours', NOW() - INTERVAL '22 hours', DATE '1998-01-15',
     '111111111111', NULL, 'retail', 'P-100'),

    -- email NULL, долгий статус, payment_id отсутствует в demo_payments
    (1002, 2, NULL, 'US', 34, 59.90, 'paid', 9002,
     NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days', NOW() - INTERVAL '1 day', DATE '1991-05-20',
     '222222222222', NULL, 'retail', 'P-200'),

    -- недопустимая страна, нереалистичный возраст, отрицательная сумма
    (1003, 3, 'bad-email', 'ZZ', 200, -10.00, 'created', NULL,
     NOW() - INTERVAL '16 days', NOW() - INTERVAL '15 days', NOW() - INTERVAL '15 days', NOW() - INTERVAL '10 days', DATE '1800-01-01',
     NULL, '3333333333', 'vip', 'P-300'),

    -- дата из будущего, одновременно заполнены person_inn и company_inn
    (1004, 4, 'david@example.com', 'FR', 41, 220.00, 'created', NULL,
     NOW() + INTERVAL '2 days', NOW() + INTERVAL '2 days', NOW() + INTERVAL '2 days', NULL, DATE '1984-02-03',
     '444444444444', '4444444444', 'business', 'P-400'),

    -- дубликат order_id и другой stable_segment для customer_id=4
    (1004, 4, 'DAVID@example.com', 'FR', 41, 220.00, 'created', NULL,
     NOW() - INTERVAL '1 day', NOW() - INTERVAL '1 day', NOW() - INTERVAL '23 hours', NULL, DATE '1984-02-03',
     NULL, '4444444444', 'enterprise', 'P-400'),

    -- пустой email и customer_id, которого нет в demo_customers
    (1005, 999, '', 'DE', 19, 15.00, 'cancelled', NULL,
     NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days', NULL, DATE '2006-06-01',
     NULL, NULL, 'retail', 'P-500');


INSERT INTO dq_datasource (name, db_type, description)
VALUES ('Primary PostgreSQL', 'postgresql', 'Main analytical source')
ON CONFLICT (name) DO NOTHING;

INSERT INTO dq_dataset (datasource_id, schema_name, table_name, display_name, owner_name, criticality, freshness_column)
SELECT datasource_id, 'demo', 'customers_raw', 'Demo customers', 'Data Platform', 'high', 'updated_at'
FROM dq_datasource
WHERE name = 'Primary PostgreSQL'
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
WHERE name = 'Primary PostgreSQL'
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

INSERT INTO dq_check_config (dataset_id, attribute_id, check_type_id, notification_rule_id, check_name, severity, threshold_percent, params, is_enabled, schedule_interval_minutes)
SELECT d.dataset_id, a.attribute_id, ct.check_type_id, nr.notification_rule_id,
       'Email should not be null', 'critical', 0, '{}'::jsonb, TRUE, 60
FROM dq_dataset d
JOIN dq_attribute a ON a.dataset_id = d.dataset_id AND a.column_name = 'email'
JOIN dq_check_type ct ON ct.code = 'not_null'
JOIN dq_notification_rule nr ON nr.email_to = 'owner@example.com'
WHERE d.schema_name = 'demo' AND d.table_name = 'customers_raw'
  AND NOT EXISTS (SELECT 1 FROM dq_check_config WHERE check_name = 'Email should not be null');

INSERT INTO dq_check_config (dataset_id, attribute_id, check_type_id, notification_rule_id, check_name, severity, threshold_percent, params, is_enabled, schedule_interval_minutes)
SELECT d.dataset_id, a.attribute_id, ct.check_type_id, nr.notification_rule_id,
       'Age must be in realistic range', 'warning', 0, '{"min_value":0,"max_value":120}'::jsonb, TRUE, 120
FROM dq_dataset d
JOIN dq_attribute a ON a.dataset_id = d.dataset_id AND a.column_name = 'age'
JOIN dq_check_type ct ON ct.code = 'numeric_range'
JOIN dq_notification_rule nr ON nr.email_to = 'owner@example.com'
WHERE d.schema_name = 'demo' AND d.table_name = 'customers_raw'
  AND NOT EXISTS (SELECT 1 FROM dq_check_config WHERE check_name = 'Age must be in realistic range');


-- Набор демонстрационных проверок по разным измерениям для таблицы demo.dq_demo_orders.
-- Они нужны, чтобы после первого запуска сервиса в мониторинге сразу были видны примеры passed/failed.
INSERT INTO dq_check_config (dataset_id, attribute_id, check_type_id, notification_rule_id, check_name, severity, threshold_percent, params, is_enabled, schedule_interval_minutes)
SELECT d.dataset_id, NULL, ct.check_type_id, nr.notification_rule_id,
       'Demo table freshness by updated_at', 'warning', 0,
       '{"timestamp_column":"updated_at","max_age_hours":24}'::jsonb, TRUE, 60
FROM dq_dataset d JOIN dq_check_type ct ON ct.code = 'table_freshness'
JOIN dq_notification_rule nr ON nr.email_to = 'owner@example.com'
WHERE d.schema_name = 'demo' AND d.table_name = 'dq_demo_orders'
  AND NOT EXISTS (SELECT 1 FROM dq_check_config WHERE check_name = 'Demo table freshness by updated_at');

INSERT INTO dq_check_config (dataset_id, attribute_id, check_type_id, notification_rule_id, check_name, severity, threshold_percent, params, is_enabled, schedule_interval_minutes)
SELECT d.dataset_id, a.attribute_id, ct.check_type_id, nr.notification_rule_id,
       'Demo email should not be blank', 'critical', 0, '{}'::jsonb, TRUE, 60
FROM dq_dataset d JOIN dq_attribute a ON a.dataset_id = d.dataset_id AND a.column_name = 'email'
JOIN dq_check_type ct ON ct.code = 'not_blank'
JOIN dq_notification_rule nr ON nr.email_to = 'owner@example.com'
WHERE d.schema_name = 'demo' AND d.table_name = 'dq_demo_orders'
  AND NOT EXISTS (SELECT 1 FROM dq_check_config WHERE check_name = 'Demo email should not be blank');

INSERT INTO dq_check_config (dataset_id, attribute_id, check_type_id, notification_rule_id, check_name, severity, threshold_percent, params, is_enabled, schedule_interval_minutes)
SELECT d.dataset_id, a.attribute_id, ct.check_type_id, nr.notification_rule_id,
       'Demo country code must be accepted', 'warning', 0,
       '{"values":["IE","US","FR","DE"]}'::jsonb, TRUE, 120
FROM dq_dataset d JOIN dq_attribute a ON a.dataset_id = d.dataset_id AND a.column_name = 'country_code'
JOIN dq_check_type ct ON ct.code = 'accepted_values'
JOIN dq_notification_rule nr ON nr.email_to = 'owner@example.com'
WHERE d.schema_name = 'demo' AND d.table_name = 'dq_demo_orders'
  AND NOT EXISTS (SELECT 1 FROM dq_check_config WHERE check_name = 'Demo country code must be accepted');

INSERT INTO dq_check_config (dataset_id, attribute_id, check_type_id, notification_rule_id, check_name, severity, threshold_percent, params, is_enabled, schedule_interval_minutes)
SELECT d.dataset_id, a.attribute_id, ct.check_type_id, nr.notification_rule_id,
       'Demo amount should not be negative', 'warning', 0,
       '{"min_value":0}'::jsonb, TRUE, 120
FROM dq_dataset d JOIN dq_attribute a ON a.dataset_id = d.dataset_id AND a.column_name = 'amount'
JOIN dq_check_type ct ON ct.code = 'not_negative'
JOIN dq_notification_rule nr ON nr.email_to = 'owner@example.com'
WHERE d.schema_name = 'demo' AND d.table_name = 'dq_demo_orders'
  AND NOT EXISTS (SELECT 1 FROM dq_check_config WHERE check_name = 'Demo amount should not be negative');

INSERT INTO dq_check_config (dataset_id, attribute_id, check_type_id, notification_rule_id, check_name, severity, threshold_percent, params, is_enabled, schedule_interval_minutes)
SELECT d.dataset_id, a.attribute_id, ct.check_type_id, nr.notification_rule_id,
       'Demo created_at should not be in future', 'warning', 0,
       '{"allowed_future_minutes":0}'::jsonb, TRUE, 120
FROM dq_dataset d JOIN dq_attribute a ON a.dataset_id = d.dataset_id AND a.column_name = 'created_at'
JOIN dq_check_type ct ON ct.code = 'future_timestamp'
JOIN dq_notification_rule nr ON nr.email_to = 'owner@example.com'
WHERE d.schema_name = 'demo' AND d.table_name = 'dq_demo_orders'
  AND NOT EXISTS (SELECT 1 FROM dq_check_config WHERE check_name = 'Demo created_at should not be in future');

INSERT INTO dq_check_config (dataset_id, attribute_id, check_type_id, notification_rule_id, check_name, severity, threshold_percent, params, is_enabled, schedule_interval_minutes)
SELECT d.dataset_id, NULL, ct.check_type_id, nr.notification_rule_id,
       'Demo created_at must be before updated_at', 'warning', 0,
       '{"left_column":"created_at","operator":"<=","right_column":"updated_at"}'::jsonb, TRUE, 120
FROM dq_dataset d JOIN dq_check_type ct ON ct.code = 'cross_field_comparison'
JOIN dq_notification_rule nr ON nr.email_to = 'owner@example.com'
WHERE d.schema_name = 'demo' AND d.table_name = 'dq_demo_orders'
  AND NOT EXISTS (SELECT 1 FROM dq_check_config WHERE check_name = 'Demo created_at must be before updated_at');

INSERT INTO dq_check_config (dataset_id, attribute_id, check_type_id, notification_rule_id, check_name, severity, threshold_percent, params, is_enabled, schedule_interval_minutes)
SELECT d.dataset_id, NULL, ct.check_type_id, nr.notification_rule_id,
       'Demo INN fields must be mutually exclusive', 'warning', 0,
       '{"columns":["person_inn","company_inn"]}'::jsonb, TRUE, 120
FROM dq_dataset d JOIN dq_check_type ct ON ct.code = 'mutually_exclusive_fields'
JOIN dq_notification_rule nr ON nr.email_to = 'owner@example.com'
WHERE d.schema_name = 'demo' AND d.table_name = 'dq_demo_orders'
  AND NOT EXISTS (SELECT 1 FROM dq_check_config WHERE check_name = 'Demo INN fields must be mutually exclusive');

INSERT INTO dq_check_config (dataset_id, attribute_id, check_type_id, notification_rule_id, check_name, severity, threshold_percent, params, is_enabled, schedule_interval_minutes)
SELECT d.dataset_id, a.attribute_id, ct.check_type_id, nr.notification_rule_id,
       'Demo country code must exist in ref_country', 'critical', 0,
       '{"reference_schema":"demo","reference_table":"ref_country","reference_column":"country_code"}'::jsonb, TRUE, 120
FROM dq_dataset d JOIN dq_attribute a ON a.dataset_id = d.dataset_id AND a.column_name = 'country_code'
JOIN dq_check_type ct ON ct.code = 'reference_match'
JOIN dq_notification_rule nr ON nr.email_to = 'owner@example.com'
WHERE d.schema_name = 'demo' AND d.table_name = 'dq_demo_orders'
  AND NOT EXISTS (SELECT 1 FROM dq_check_config WHERE check_name = 'Demo country code must exist in ref_country');

INSERT INTO dq_check_config (dataset_id, attribute_id, check_type_id, notification_rule_id, check_name, severity, threshold_percent, params, is_enabled, schedule_interval_minutes)
SELECT d.dataset_id, a.attribute_id, ct.check_type_id, nr.notification_rule_id,
       'Demo order_id must be unique', 'critical', 0, '{}'::jsonb, TRUE, 120
FROM dq_dataset d JOIN dq_attribute a ON a.dataset_id = d.dataset_id AND a.column_name = 'order_id'
JOIN dq_check_type ct ON ct.code = 'unique'
JOIN dq_notification_rule nr ON nr.email_to = 'owner@example.com'
WHERE d.schema_name = 'demo' AND d.table_name = 'dq_demo_orders'
  AND NOT EXISTS (SELECT 1 FROM dq_check_config WHERE check_name = 'Demo order_id must be unique');

INSERT INTO dq_check_config (dataset_id, attribute_id, check_type_id, notification_rule_id, check_name, severity, threshold_percent, params, is_enabled, schedule_interval_minutes)
SELECT d.dataset_id, a.attribute_id, ct.check_type_id, nr.notification_rule_id,
       'Demo customer_id must exist in customers dictionary', 'critical', 0,
       '{"reference_schema":"demo","reference_table":"demo_customers","reference_column":"customer_id"}'::jsonb, TRUE, 120
FROM dq_dataset d JOIN dq_attribute a ON a.dataset_id = d.dataset_id AND a.column_name = 'customer_id'
JOIN dq_check_type ct ON ct.code = 'foreign_key_exists'
JOIN dq_notification_rule nr ON nr.email_to = 'owner@example.com'
WHERE d.schema_name = 'demo' AND d.table_name = 'dq_demo_orders'
  AND NOT EXISTS (SELECT 1 FROM dq_check_config WHERE check_name = 'Demo customer_id must exist in customers dictionary');

INSERT INTO dq_check_config (dataset_id, attribute_id, check_type_id, notification_rule_id, check_name, severity, threshold_percent, params, is_enabled, schedule_interval_minutes)
SELECT d.dataset_id, NULL, ct.check_type_id, nr.notification_rule_id,
       'Demo each order should have at least one item', 'warning', 0,
       '{"parent_key_column":"order_id","child_schema":"demo","child_table":"demo_order_items","child_key_column":"order_id"}'::jsonb, TRUE, 120
FROM dq_dataset d JOIN dq_check_type ct ON ct.code = 'parent_has_child'
JOIN dq_notification_rule nr ON nr.email_to = 'owner@example.com'
WHERE d.schema_name = 'demo' AND d.table_name = 'dq_demo_orders'
  AND NOT EXISTS (SELECT 1 FROM dq_check_config WHERE check_name = 'Demo each order should have at least one item');


