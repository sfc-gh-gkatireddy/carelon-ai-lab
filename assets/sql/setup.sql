-- ═══════════════════════════════════════════════════════════════════════════
-- Elevance AI Lab — Setup Script
-- Creates the lab database, tables, warehouse, role, and loads synthetic data.
-- Run as ACCOUNTADMIN from a SQL worksheet after creating the Git repository:
--   EXECUTE IMMEDIATE FROM @ELEVANCE_LAB_REPO/branches/main/assets/sql/setup.sql;
-- All data is 100% synthetic. No real member, patient, or PHI data.
-- ═══════════════════════════════════════════════════════════════════════════

-- ── 1. Database and schema ──────────────────────────────────────────────────
CREATE DATABASE IF NOT EXISTS ELEVANCE_LAB_DB;
CREATE SCHEMA IF NOT EXISTS ELEVANCE_LAB_DB.PAYER;
CREATE SCHEMA IF NOT EXISTS ELEVANCE_LAB_DB.AGENTS;

USE DATABASE ELEVANCE_LAB_DB;
USE SCHEMA PAYER;

-- ── 2. Warehouse and role ───────────────────────────────────────────────────
CREATE WAREHOUSE IF NOT EXISTS ELEVANCE_LAB_WH
  WAREHOUSE_SIZE = 'MEDIUM'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  INITIALLY_SUSPENDED = TRUE;

CREATE ROLE IF NOT EXISTS ELEVANCE_LAB_ROLE;

GRANT USAGE ON WAREHOUSE ELEVANCE_LAB_WH TO ROLE ELEVANCE_LAB_ROLE;
GRANT USAGE, CREATE SCHEMA ON DATABASE ELEVANCE_LAB_DB TO ROLE ELEVANCE_LAB_ROLE;
GRANT ALL ON SCHEMA ELEVANCE_LAB_DB.PAYER TO ROLE ELEVANCE_LAB_ROLE;
GRANT ALL ON SCHEMA ELEVANCE_LAB_DB.AGENTS TO ROLE ELEVANCE_LAB_ROLE;
GRANT CREATE CORTEX SEARCH SERVICE ON SCHEMA ELEVANCE_LAB_DB.PAYER TO ROLE ELEVANCE_LAB_ROLE;
GRANT CREATE AGENT ON SCHEMA ELEVANCE_LAB_DB.AGENTS TO ROLE ELEVANCE_LAB_ROLE;
GRANT CREATE SNOWFLAKE INTELLIGENCE ON ACCOUNT TO ROLE ELEVANCE_LAB_ROLE;
-- Grant the lab role to whoever is running this script.
-- EXECUTE IMMEDIATE is needed because GRANT ... TO USER does not accept
-- CURRENT_USER() directly as a bare argument.
BEGIN
  EXECUTE IMMEDIATE 'GRANT ROLE ELEVANCE_LAB_ROLE TO USER ' || CURRENT_USER();
END;

-- ── 3. File formats ─────────────────────────────────────────────────────────
CREATE OR REPLACE FILE FORMAT TEXT_FORMAT
  TYPE = CSV
  SKIP_HEADER = 1
  FIELD_OPTIONALLY_ENCLOSED_BY = '"'
  TRIM_SPACE = TRUE
  EMPTY_FIELD_AS_NULL = TRUE;

CREATE OR REPLACE FILE FORMAT POLICY_TEXT_FORMAT
  TYPE = CSV
  RECORD_DELIMITER = '\n'
  FIELD_DELIMITER = NONE
  SKIP_HEADER = 0
  TRIM_SPACE = TRUE;

-- ── 4. Tables ───────────────────────────────────────────────────────────────
CREATE OR REPLACE TABLE MEMBERS (
  member_id         VARCHAR    NOT NULL,
  name              VARCHAR,
  dob               DATE,
  gender            VARCHAR,
  plan_id           VARCHAR,
  plan_name         VARCHAR,
  plan_type         VARCHAR,
  pcp               VARCHAR,
  chronic_condition VARCHAR,
  smoker_ind        VARCHAR,
  enrollment_start  DATE,
  enrollment_end     DATE,
  state             VARCHAR,
  city              VARCHAR,
  CONSTRAINT pk_members PRIMARY KEY (member_id)
);

CREATE OR REPLACE TABLE MEDICAL_CLAIMS (
  claim_id       VARCHAR  NOT NULL,
  member_id      VARCHAR,
  service_date   DATE,
  provider_id    VARCHAR,
  icd10_code     VARCHAR,
  icd10_desc     VARCHAR,
  procedure_code VARCHAR,
  procedure_desc VARCHAR,
  billed_amt     NUMBER(12,2),
  allowed_amt    NUMBER(12,2),
  paid_amt       NUMBER(12,2),
  claim_status   VARCHAR,
  service_type   VARCHAR,
  CONSTRAINT pk_medical_claims PRIMARY KEY (claim_id),
  CONSTRAINT fk_medical_member FOREIGN KEY (member_id) REFERENCES MEMBERS(member_id)
);

CREATE OR REPLACE TABLE PHARMACY_CLAIMS (
  rx_id          VARCHAR  NOT NULL,
  member_id      VARCHAR,
  drug_name      VARCHAR,
  ndc_code       VARCHAR,
  drug_class     VARCHAR,
  drug_strength  VARCHAR,
  days_supply    NUMBER,
  paid_amt       NUMBER(12,2),
  fill_date      DATE,
  prescriber_id  VARCHAR,
  CONSTRAINT pk_pharmacy_claims PRIMARY KEY (rx_id),
  CONSTRAINT fk_pharmacy_member FOREIGN KEY (member_id) REFERENCES MEMBERS(member_id)
);

CREATE OR REPLACE TABLE PROVIDERS (
  provider_id        VARCHAR NOT NULL,
  name               VARCHAR,
  specialty          VARCHAR,
  npi                VARCHAR,
  network_status     VARCHAR,
  location           VARCHAR,
  avg_cost_per_visit NUMBER(12,2),
  CONSTRAINT pk_providers PRIMARY KEY (provider_id)
);

-- ── 5. Load data from the Git repo stage ────────────────────────────────────
COPY INTO MEMBERS
FROM @ELEVANCE_LAB_REPO/branches/main/assets/data/members.csv
FILE_FORMAT = (FORMAT_NAME = TEXT_FORMAT)
ON_ERROR = 'ABORT_STATEMENT';

COPY INTO MEDICAL_CLAIMS
FROM @ELEVANCE_LAB_REPO/branches/main/assets/data/medical_claims.csv
FILE_FORMAT = (FORMAT_NAME = TEXT_FORMAT)
ON_ERROR = 'ABORT_STATEMENT';

COPY INTO PHARMACY_CLAIMS
FROM @ELEVANCE_LAB_REPO/branches/main/assets/data/pharmacy_claims.csv
FILE_FORMAT = (FORMAT_NAME = TEXT_FORMAT)
ON_ERROR = 'ABORT_STATEMENT';

COPY INTO PROVIDERS
FROM @ELEVANCE_LAB_REPO/branches/main/assets/data/providers.csv
FILE_FORMAT = (FORMAT_NAME = TEXT_FORMAT)
ON_ERROR = 'ABORT_STATEMENT';

-- ── 6. Internal stages for lab artifacts ────────────────────────────────────
CREATE OR REPLACE STAGE POLICY_DOCS
  FILE_FORMAT = POLICY_TEXT_FORMAT
  COMMENT = 'Benefit policy documents for Cortex Search and AI_EXTRACT';

CREATE OR REPLACE STAGE SEMANTIC_MODELS
  COMMENT = 'Fallback semantic model YAML if Autopilot is unavailable';

-- ── 7. Snowflake Intelligence object (for CoWork agent registration) ─────────
CREATE SNOWFLAKE INTELLIGENCE IF NOT EXISTS SNOWFLAKE_INTELLIGENCE_OBJECT_DEFAULT;

-- ── 8. Verification ─────────────────────────────────────────────────────────
SELECT 'MEMBERS'          AS tbl, COUNT(*) AS row_count FROM MEMBERS
UNION ALL
SELECT 'MEDICAL_CLAIMS',  COUNT(*) FROM MEDICAL_CLAIMS
UNION ALL
SELECT 'PHARMACY_CLAIMS', COUNT(*) FROM PHARMACY_CLAIMS
UNION ALL
SELECT 'PROVIDERS',       COUNT(*) FROM PROVIDERS
ORDER BY 1;

-- Expected output:
--   MEDICAL_CLAIMS   ~116,000
--   MEMBERS           10,000
--   PHARMACY_CLAIMS   ~54,000
--   PROVIDERS          2,000
