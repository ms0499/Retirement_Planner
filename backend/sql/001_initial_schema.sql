BEGIN;

CREATE TABLE retirement.alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 1bdf339d7c34

CREATE SCHEMA IF NOT EXISTS "retirement";

CREATE TABLE retirement.households (
    id SERIAL NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

CREATE TABLE retirement.users (
    id SERIAL NOT NULL, 
    email VARCHAR(255) NOT NULL, 
    hashed_password VARCHAR(255) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_users_email ON retirement.users (email);

CREATE TABLE retirement.expense_categories (
    id SERIAL NOT NULL, 
    household_id INTEGER NOT NULL, 
    category VARCHAR(100) NOT NULL, 
    pre_retirement_annual NUMERIC(12, 2) NOT NULL, 
    post_retirement_annual NUMERIC(12, 2) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(household_id) REFERENCES retirement.households (id)
);

CREATE TYPE retirement.lifestylepreset AS ENUM ('MODEST', 'COMFORTABLE', 'LUXURIOUS', 'CUSTOM');

CREATE TYPE retirement.filingstatus AS ENUM ('SINGLE', 'MARRIED_FILING_JOINTLY');

CREATE TABLE retirement.household_assumptions (
    id SERIAL NOT NULL, 
    household_id INTEGER NOT NULL, 
    inflation_rate NUMERIC(5, 4) NOT NULL, 
    expected_return NUMERIC(5, 4) NOT NULL, 
    safe_withdrawal_rate NUMERIC(5, 4) NOT NULL, 
    lifestyle_preset retirement.lifestylepreset NOT NULL, 
    filing_status retirement.filingstatus NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(household_id) REFERENCES retirement.households (id), 
    UNIQUE (household_id)
);

CREATE TYPE retirement.householdrole AS ENUM ('OWNER', 'MEMBER');

CREATE TABLE retirement.household_members (
    id SERIAL NOT NULL, 
    household_id INTEGER NOT NULL, 
    user_id INTEGER NOT NULL, 
    role retirement.householdrole NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(household_id) REFERENCES retirement.households (id), 
    FOREIGN KEY(user_id) REFERENCES retirement.users (id)
);

CREATE TYPE retirement.relationship AS ENUM ('SELF', 'PARTNER');

CREATE TABLE retirement.people (
    id SERIAL NOT NULL, 
    household_id INTEGER NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    relationship_type retirement.relationship NOT NULL, 
    current_age INTEGER NOT NULL, 
    retirement_age INTEGER NOT NULL, 
    life_expectancy INTEGER NOT NULL, 
    social_security_monthly_estimate NUMERIC(10, 2) NOT NULL, 
    social_security_claim_age INTEGER NOT NULL, 
    pension_monthly NUMERIC(10, 2) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(household_id) REFERENCES retirement.households (id)
);

CREATE TABLE retirement.scenarios (
    id SERIAL NOT NULL, 
    household_id INTEGER NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    overrides JSON NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(household_id) REFERENCES retirement.households (id)
);

CREATE TYPE retirement.accounttype AS ENUM ('TRADITIONAL_401K', 'ROTH_401K', 'TRADITIONAL_IRA', 'ROTH_IRA', 'HSA', 'BROKERAGE', 'CASH');

CREATE TABLE retirement.accounts (
    id SERIAL NOT NULL, 
    household_id INTEGER NOT NULL, 
    person_id INTEGER, 
    name VARCHAR(255) NOT NULL, 
    account_type retirement.accounttype NOT NULL, 
    balance NUMERIC(14, 2) NOT NULL, 
    annual_contribution NUMERIC(12, 2) NOT NULL, 
    annual_employer_match NUMERIC(12, 2) NOT NULL, 
    expected_return_override NUMERIC(5, 4), 
    PRIMARY KEY (id), 
    FOREIGN KEY(household_id) REFERENCES retirement.households (id), 
    FOREIGN KEY(person_id) REFERENCES retirement.people (id)
);

INSERT INTO retirement.alembic_version (version_num) VALUES ('1bdf339d7c34') RETURNING retirement.alembic_version.version_num;

COMMIT;

