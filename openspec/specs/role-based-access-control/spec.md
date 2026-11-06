# role-based-access-control Specification

## Purpose

Defines the Admin, Editor, and Author roles, how roles are assigned, who may administer users, and the safeguards that prevent privilege escalation or locking the portal out of administrative access.

## Requirements

### Requirement: Three roles exist

The system SHALL support exactly three role names: `Admin`, `Editor`, and `Author`. Every non-superuser user SHALL have exactly one role. A superuser SHALL be treated as `Admin` regardless of group membership.

#### Scenario: Create a user in each role

- **WHEN** an Admin creates users with roles `Admin`, `Editor`, and `Author`
- **THEN** each user is created with exactly that role

#### Scenario: Unsupported role is rejected

- **WHEN** a role value other than `Admin`, `Editor`, or `Author` is submitted
- **THEN** the response is 400 with a validation error

#### Scenario: Superuser is Admin

- **WHEN** a superuser is returned by the user API
- **THEN** the reported role is `Admin`

### Requirement: Role assignment

An Admin SHALL be able to assign a role when creating a user and change it when updating a user. Assigning a new role SHALL replace the previous role so the user retains exactly one role.

#### Scenario: Assign role on create

- **WHEN** an Admin creates a user with role `Editor`
- **THEN** the user has exactly the `Editor` role

#### Scenario: Change role on update

- **WHEN** an Admin changes an `Author` to `Editor`
- **THEN** the user has exactly the `Editor` role and no longer has the `Author` role

#### Scenario: Non-Admin cannot assign a role

- **WHEN** an authenticated Editor or Author attempts to create or update a user with any role
- **THEN** the response is 403 and no role change occurs

### Requirement: Admin-only user management

Only users in the `Admin` role and superusers SHALL access the user-management endpoints. Unauthenticated requests SHALL return 401; authenticated users without the Admin role SHALL return 403.

#### Scenario: Admin is allowed

- **WHEN** a user in the `Admin` role requests any user-management endpoint
- **THEN** the request is authorized

#### Scenario: Superuser is allowed

- **WHEN** a superuser requests any user-management endpoint
- **THEN** the request is authorized

#### Scenario: Editor is forbidden

- **WHEN** a user in the `Editor` role requests any user-management endpoint
- **THEN** the response is 403

#### Scenario: Author is forbidden

- **WHEN** a user in the `Author` role requests any user-management endpoint
- **THEN** the response is 403

#### Scenario: Unauthenticated request is rejected

- **WHEN** a request without an authenticated session reaches a user-management endpoint
- **THEN** the response is 401

### Requirement: Inactive accounts cannot administer users

An inactive account SHALL NOT access user-management endpoints even when it holds the `Admin` role. An authenticated inactive account SHALL receive 403.

#### Scenario: Inactive Admin is forbidden

- **WHEN** an inactive user in the `Admin` role requests any user-management endpoint
- **THEN** the response is 403

#### Scenario: Deactivated Admin loses access

- **WHEN** an Admin is set to inactive and makes a subsequent user-management request
- **THEN** the response is 403

### Requirement: Superuser accounts are read-only through the API

The user-management API SHALL NOT update or delete a superuser account. Attempts SHALL return 409 and leave the account unchanged.

#### Scenario: Update superuser is rejected

- **WHEN** an Admin attempts to update a superuser's profile, password, role, or active status through the API
- **THEN** the response is 409 and the superuser is unchanged

#### Scenario: Delete superuser is rejected

- **WHEN** an Admin attempts to delete a superuser through the API
- **THEN** the response is 409 and the superuser still exists

### Requirement: Last active Admin is protected

The system SHALL reject deleting, deactivating, or removing the `Admin` role from the last active Admin. The rejection SHALL return 409 and leave the account unchanged.

#### Scenario: Delete last active Admin

- **WHEN** an Admin attempts to delete the only remaining active Admin
- **THEN** the response is 409 and the account still exists

#### Scenario: Deactivate last active Admin

- **WHEN** an Admin attempts to set the only remaining active Admin to inactive
- **THEN** the response is 409 and the account remains active

#### Scenario: Demote last active Admin

- **WHEN** an Admin attempts to change the only remaining active Admin's role to Editor or Author
- **THEN** the response is 409 and the role is unchanged

#### Scenario: Another active Admin allows the change

- **WHEN** at least two active Admins exist and one is deactivated or demoted
- **THEN** the operation is allowed

### Requirement: Self-protection for destructive actions

An Admin SHALL NOT delete or deactivate their own account. Attempts SHALL return 409 and leave the account unchanged.

#### Scenario: Admin deletes self

- **WHEN** an Admin attempts to delete their own account
- **THEN** the response is 409 and the account still exists

#### Scenario: Admin deactivates self

- **WHEN** an Admin attempts to set their own account to inactive
- **THEN** the response is 409 and the account remains active

### Requirement: Role changes take effect immediately

Authorization SHALL use the user's current role on every request. Removing or changing a role SHALL affect the user's next request.

#### Scenario: Removed Admin loses access

- **WHEN** an Admin changes another Admin's role to `Author`
- **THEN** the changed user's next user-management request returns 403

#### Scenario: Promoted user gains access

- **WHEN** an Admin changes an `Author` to `Admin`
- **THEN** the changed user's next user-management request is authorized
