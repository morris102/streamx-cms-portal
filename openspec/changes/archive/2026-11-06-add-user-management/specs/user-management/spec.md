# Spec Delta

## Purpose

Defines the Admin-facing lifecycle for user accounts: paginated listing, email search, active/inactive filtering, and create, view, update, and delete operations.

## ADDED Requirements

### Requirement: Paginated user listing

The system SHALL return users ordered by ascending ID in a paginated envelope containing `count`, `page`, `page_size`, `total_pages`, and `results`. The default page SHALL be 1 and the default page size SHALL be 20; page size SHALL NOT exceed 100.

#### Scenario: Default pagination

- **WHEN** an Admin requests `GET /api/users/` without pagination parameters
- **THEN** the response is 200 with `page` 1, `page_size` 20, `count`, `total_pages`, and up to 20 users in `results`

#### Scenario: Custom page size

- **WHEN** an Admin requests `GET /api/users/?page=2&page_size=5`
- **THEN** the response is 200 with at most five users in `results` and `page` 2

#### Scenario: Invalid pagination values

- **WHEN** an Admin requests a page below 1, a non-integer page, or a page size above 100
- **THEN** the response is 400 with a validation error

#### Scenario: Page beyond the last page

- **WHEN** an Admin requests a page greater than `total_pages`
- **THEN** the response is 200 with an empty `results` list and the correct `count`

### Requirement: Email search

The system SHALL filter the user list to users whose email contains the `search` value, case-insensitively, when `search` is non-blank. A blank or whitespace-only `search` SHALL NOT filter the list.

#### Scenario: Partial email search

- **WHEN** an Admin requests `GET /api/users/?search=example.com`
- **THEN** only users whose email contains `example.com` are returned

#### Scenario: Case-insensitive search

- **WHEN** an Admin searches with `ALICE` and a user has `alice@example.com`
- **THEN** that user is included in the results

#### Scenario: Blank search is ignored

- **WHEN** an Admin requests `GET /api/users/?search=%20`
- **THEN** the response is the same as a request without `search`

### Requirement: Active/inactive filtering

The system SHALL filter the user list by `is_active` when the query parameter is `true` or `false`, case-insensitively. Any other value SHALL return 400.

#### Scenario: Active users only

- **WHEN** an Admin requests `GET /api/users/?is_active=true`
- **THEN** only active users are returned

#### Scenario: Inactive users only

- **WHEN** an Admin requests `GET /api/users/?is_active=false`
- **THEN** only inactive users are returned

#### Scenario: Invalid active filter

- **WHEN** an Admin requests `is_active=maybe`
- **THEN** the response is 400 with a validation error

#### Scenario: Search and filter combine

- **WHEN** an Admin requests a search term and `is_active=false` together
- **THEN** only inactive users whose email matches the search term are returned

### Requirement: Create user

An Admin SHALL be able to create a user by supplying username, email, password, and role. The response SHALL be 201 with the user representation, the password SHALL be stored hashed, and `is_active` SHALL default to `true` when omitted.

#### Scenario: Successful creation

- **WHEN** an Admin posts valid username, email, password, and role values
- **THEN** the response is 201 with the new user and no password field

#### Scenario: Duplicate username or email

- **WHEN** an Admin submits a username or email that already exists, including an email that differs only by case
- **THEN** the response is 400 with a validation error

#### Scenario: Invalid password

- **WHEN** an Admin submits a password rejected by Django's configured password validators
- **THEN** the response is 400 with a validation error

#### Scenario: Invalid role

- **WHEN** an Admin submits a role other than `Admin`, `Editor`, or `Author`
- **THEN** the response is 400 with a validation error

#### Scenario: Missing required field

- **WHEN** an Admin omits username, email, password, or role
- **THEN** the response is 400 with a validation error

#### Scenario: Unknown field is rejected

- **WHEN** an Admin submits a field that is not part of the user contract
- **THEN** the response is 400 and no user is created

#### Scenario: Default active status

- **WHEN** an Admin creates a user without `is_active`
- **THEN** the created user is active

### Requirement: View user

An Admin SHALL be able to retrieve one user by ID. A missing user SHALL return 404.

#### Scenario: Existing user

- **WHEN** an Admin requests `GET /api/users/{id}/` for an existing user
- **THEN** the response is 200 with that user's representation

#### Scenario: Missing user

- **WHEN** an Admin requests a user ID that does not exist
- **THEN** the response is 404

### Requirement: Update user

An Admin SHALL be able to partially update a user's username, email, first name, last name, password, role, and active status. A supplied password SHALL be validated and hashed; an omitted password SHALL remain unchanged.

#### Scenario: Update profile fields

- **WHEN** an Admin patches a user's email, first name, or last name
- **THEN** the response is 200 and the stored values are updated

#### Scenario: Change password

- **WHEN** an Admin patches a valid new password
- **THEN** the response is 200 and the user can authenticate with the new password

#### Scenario: Duplicate values on update

- **WHEN** an Admin updates a user to a username or email that belongs to another user
- **THEN** the response is 400 with a validation error

#### Scenario: Invalid role on update

- **WHEN** an Admin submits a role other than `Admin`, `Editor`, or `Author`
- **THEN** the response is 400 with a validation error

#### Scenario: Unknown field on update

- **WHEN** an Admin submits a field that is not part of the update contract
- **THEN** the response is 400 and the user is unchanged

#### Scenario: Missing user on update

- **WHEN** an Admin patches a user ID that does not exist
- **THEN** the response is 404

### Requirement: Delete user

An Admin SHALL be able to delete a user. Successful deletion SHALL return 204 with no body; a missing user SHALL return 404. Deletion SHALL be subject to the protections defined in `role-based-access-control`.

#### Scenario: Successful deletion

- **WHEN** an Admin deletes a non-protected user
- **THEN** the response is 204 and the user no longer exists

#### Scenario: Missing user on delete

- **WHEN** an Admin deletes a user ID that does not exist
- **THEN** the response is 404

### Requirement: User response excludes credentials

Every successful user response SHALL include `id`, `username`, `email`, `first_name`, `last_name`, `role`, `is_active`, and `date_joined`, and SHALL NOT include the password, password hash, or session or token data.

#### Scenario: No password in any user response

- **WHEN** a user is returned by list, create, view, or update
- **THEN** the response contains no `password`, `password_hash`, or authentication token field

#### Scenario: Role is included

- **WHEN** a user is returned
- **THEN** `role` is the assigned role, or `Admin` for a superuser
