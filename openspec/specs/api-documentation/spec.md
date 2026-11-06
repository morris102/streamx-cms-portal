# api-documentation Specification

## Purpose
Defines the OpenAPI 3.0 documentation for the user-management API: the served specification file, the Swagger UI page, their Admin-only access rules, and the tests that keep the documentation synchronized with the implemented endpoints.

## Requirements

### Requirement: OpenAPI specification file

The system SHALL provide a machine-readable OpenAPI 3.0 specification of every user-management endpoint as a JSON document, and SHALL serve it at `GET /api/openapi.json/`.

#### Scenario: Specification is served

- **WHEN** an Admin requests `GET /api/openapi.json/`
- **THEN** the response is 200 with a JSON document whose `openapi` field declares OpenAPI 3.x

#### Scenario: Specification doubles as export

- **WHEN** a client saves the response body of `GET /api/openapi.json/`
- **THEN** the saved file is a valid standalone OpenAPI 3.0 JSON artifact

### Requirement: Interactive documentation UI

The system SHALL serve an interactive Swagger UI page at `GET /api/docs/` that loads the served specification.

#### Scenario: Swagger UI loads

- **WHEN** an Admin opens `/api/docs/`
- **THEN** the page renders all user-management operations from the served specification

### Requirement: Documentation is Admin-only

Both documentation endpoints SHALL require an authenticated, active caller with the Admin role, using the same rules as the user-management API.

#### Scenario: Anonymous access is rejected

- **WHEN** a client without a session requests `/api/openapi.json/` or `/api/docs/`
- **THEN** the response is 401

#### Scenario: Non-Admin access is rejected

- **WHEN** a user with the Editor or Author role requests either documentation endpoint
- **THEN** the response is 403

### Requirement: Specification documents the implemented contract

The specification SHALL describe every user-management operation with its HTTP method and path, request schemas, response schemas for every status code the implementation returns (200, 201, 204, plus error responses 400, 401, 403, 404, 405, 409), the session-and-CSRF authentication model, and reusable component schemas. It SHALL NOT document status codes or error shapes the implementation does not produce.

#### Scenario: All operations are documented

- **WHEN** the specification is compared against `users/urls.py` and `users/views.py`
- **THEN** all five operations (list, create, view, update, delete) appear with their methods, and no undocumented operation exists in the API

#### Scenario: Authentication is documented

- **WHEN** the specification's security section is read
- **THEN** it states that endpoints require a Django session cookie and that unsafe methods require a CSRF token

#### Scenario: Error contract is documented

- **WHEN** the specification's error responses are read
- **THEN** validation errors are described as `{"errors": {field: [messages]}}` (400) and other rejections as `{"detail": "..."}` (401, 403, 409)

#### Scenario: Sensitive fields are excluded

- **WHEN** user schemas in the specification are read
- **THEN** no password, password-hash, or session/token field exists in any response schema, while `password` appears only in request schemas

### Requirement: Specification drift is caught by tests

The automated test suite SHALL verify that the served specification remains synchronized with the implemented routes.

#### Scenario: Route coverage test

- **WHEN** the test suite parses and inspects the specification against the URL configuration
- **THEN** every documented path/method matches an implemented route and every implemented user-management route is documented
