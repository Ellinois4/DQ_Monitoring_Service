-- Target database initialization script.
-- БД имитирует продуктивный хранилище заказчика.

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


