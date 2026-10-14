-- Star schema for retail-lending risk analytics (SQLite)
DROP VIEW IF EXISTS vw_loans;
DROP VIEW IF EXISTS vw_loans_base;
DROP TABLE IF EXISTS fact_applications;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_branch;
DROP TABLE IF EXISTS dim_date;

CREATE TABLE dim_branch  (branch_id TEXT PRIMARY KEY, city TEXT NOT NULL UNIQUE, region TEXT NOT NULL);
CREATE TABLE dim_product (product_id TEXT PRIMARY KEY, product TEXT NOT NULL UNIQUE, secured INTEGER NOT NULL, lgd REAL NOT NULL);
CREATE TABLE dim_date (
    date_key TEXT PRIMARY KEY, year INTEGER, quarter INTEGER, month INTEGER,
    month_name TEXT, year_month TEXT, year_quarter TEXT, day_name TEXT, is_weekend INTEGER);

CREATE TABLE fact_applications (
    application_id        TEXT PRIMARY KEY,
    application_date      TEXT NOT NULL REFERENCES dim_date(date_key),
    disbursed_date        TEXT,               -- NULL for rejected applications
    branch_id             TEXT NOT NULL REFERENCES dim_branch(branch_id),
    product_id            TEXT NOT NULL REFERENCES dim_product(product_id),
    customer_age          INTEGER,
    gender                TEXT,
    employment_type       TEXT NOT NULL CHECK (employment_type IN ('Salaried','Self-Employed','Business Owner')),
    monthly_income        REAL,
    credit_score          REAL,               -- NULL = new-to-credit / invalid bureau score
    existing_emi          REAL,
    loan_amount           REAL NOT NULL,
    tenure_months         INTEGER,
    interest_rate         REAL,
    emi                   REAL,
    channel               TEXT CHECK (channel IN ('Branch','Online','DSA')),
    decision              TEXT NOT NULL CHECK (decision IN ('Approved','Rejected')),
    rejection_reason      TEXT,
    loan_status           TEXT CHECK (loan_status IN ('Current','Closed','Delinquent 30-89','NPA')),
    dpd                   INTEGER,
    default_mob           REAL,               -- months on book when the loan turned NPA (90+ DPD)
    outstanding_principal REAL,
    dq_flags              TEXT
);
CREATE INDEX idx_app_date    ON fact_applications(application_date);
CREATE INDEX idx_app_branch  ON fact_applications(branch_id);
CREATE INDEX idx_app_product ON fact_applications(product_id);
CREATE INDEX idx_app_status  ON fact_applications(loan_status);
