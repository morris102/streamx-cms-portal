# database-configuration Specification

## Purpose

Defines how the application selects its relational database and obtains PostgreSQL connection settings from the environment, so configuration is explicit, keeps secrets out of version control, and behaves consistently in development and tests.

## Requirements

### Requirement: PostgreSQL is the configured database backend

The application SHALL use PostgreSQL as its `default` database backend. It SHALL NOT silently fall back to SQLite when database configuration is missing or invalid.

#### Scenario: Application connects to PostgreSQL

- **WHEN** the application starts with valid database environment variables
- **THEN** the default connection reports the PostgreSQL backend and the connection succeeds

#### Scenario: Missing configuration fails instead of falling back

- **WHEN** a required database variable is absent
- **THEN** application startup fails with an error identifying the missing configuration instead of opening a SQLite file

### Requirement: Connection settings come from the environment

The application SHALL read the database name, user, password, host, and port from `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT`. `DB_HOST` SHALL default to `localhost` and `DB_PORT` to `5432`; `DB_NAME`, `DB_USER`, and `DB_PASSWORD` are required.

#### Scenario: Environment values configure the connection

- **WHEN** all five database variables are set
- **THEN** the connection uses exactly those values

#### Scenario: Host and port defaults

- **WHEN** `DB_HOST` and `DB_PORT` are unset but the required variables are present
- **THEN** the connection targets `localhost` on port `5432`

### Requirement: Local .env file supplies development settings

When present, a `.env` file at the project root SHALL supply missing database variables without overriding variables already set in the process environment. The `.env` file SHALL be excluded from version control, and a committed `.env.example` SHALL list the required keys with placeholder values only.

#### Scenario: Values load from .env

- **WHEN** a database variable is not set in the process environment and appears in `.env`
- **THEN** the application uses the `.env` value

#### Scenario: Process environment wins

- **WHEN** the same variable exists in both the process environment and `.env`
- **THEN** the process environment value is used

#### Scenario: .env is not committed

- **WHEN** the repository contents are inspected
- **THEN** `.env` is ignored by version control and `.env.example` contains placeholders rather than real credentials

### Requirement: Tests use an isolated PostgreSQL database

The test runner SHALL create and destroy a separate PostgreSQL database derived from `DB_NAME`, leaving the development database unchanged. The configured role SHALL have permission to create databases.

#### Scenario: Test run uses a separate database

- **WHEN** the test suite runs
- **THEN** Django creates and destroys the corresponding test database and the development database is not modified

#### Scenario: Role cannot create the test database

- **WHEN** the configured role lacks permission to create databases
- **THEN** the test run fails with a database-creation error before executing tests
