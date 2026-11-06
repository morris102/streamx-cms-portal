# AGENTS.md

## 1. Project Overview

### Project Description
CMS Portal is a web-based Content Management System (CMS) built with Python and Django.

The application uses Django for backend development and PostgreSQL as its primary relational database.

### Technology Stack
- **Programming Language:** Python
- **Backend Framework:** Django
- **Database:** PostgreSQL
- **ORM:** Django ORM
- **Package Management:** pip and virtual environments
- **Database Migrations:** Django Migrations

### Architecture Guidelines
- Follow Django's Model-View-Template (MVT) architecture.
- Organize business functionality into independent Django applications.
- Keep business logic separate from HTTP request handling.
- Use Django ORM for database operations.
- Use Django Forms or Django REST Framework serializers (if applicable) for input validation.
- Keep configuration and environment-specific settings separate.
- Avoid unnecessary dependencies and over-engineered abstractions.
- Reuse existing project patterns before introducing new architectural approaches.

### Project Structure
Follow the existing repository structure. A typical organization is:

```text
cms-portal/
├── config/              # Django project configuration
├── apps/                # Business applications
├── templates/           # HTML templates
├── static/              # Static assets
├── media/               # Uploaded media files
├── tests/               # Shared tests (if applicable)
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
└── AGENTS.md
```

Do not create new directories or reorganize existing applications without a clear requirement.

---

## 2. Build and Test Commands

### Environment Setup

Create and activate a Python virtual environment:

```bash
python3 -m venv .venv

source .venv/bin/activate
```

Install project dependencies:

```bash
pip install -r requirements.txt
```

### Environment Configuration

Configure the required environment variables in `.env`:

```env
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=cms_portal
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432
```

Never commit actual secrets or production credentials.

### Database Setup

Create the PostgreSQL database if it does not exist:

```sql
CREATE DATABASE cms_portal;
```

Apply database migrations:

```bash
python manage.py migrate
```

Create a superuser:

```bash
python manage.py createsuperuser
```

### Development Server

Start the Django development server:

```bash
python manage.py runserver
```

Default URL:

```text
http://127.0.0.1:8000/
```

### Build and Validation

Check the Django project configuration:

```bash
python manage.py check
```

Check production-specific configuration:

```bash
python manage.py check --deploy
```

Generate database migrations:

```bash
python manage.py makemigrations
```

Apply migrations:

```bash
python manage.py migrate
```

Collect static files:

```bash
python manage.py collectstatic --noinput
```

### Dependency Management

Update dependencies only when necessary.

After introducing a new dependency:
- Add it to the project's dependency management file.
- Use compatible and maintained package versions.
- Avoid adding dependencies when Python or Django already provides the required functionality.

---

## 3. Code Style Guidelines

### Python Guidelines
- Follow PEP 8 conventions.
- Use 4 spaces for indentation.
- Use descriptive variable, function, and class names.
- Use `snake_case` for variables and functions.
- Use `PascalCase` for classes.
- Use `UPPER_SNAKE_CASE` for constants.
- Prefer simple, readable code over unnecessary abstractions.
- Add type hints to functions where they improve clarity.
- Write docstrings for public classes and complex functions.

Example:

```python
def get_active_articles():
    return Article.objects.filter(
        status="published",
        is_active=True,
    )
```

### Django Guidelines

**Models**
- Define database models in `models.py` or an existing domain-specific module.
- Use meaningful field names and appropriate field types.
- Define `related_name` for relationships when useful.
- Add database indexes for frequently queried fields when justified.
- Use database constraints to enforce important data integrity rules.

**Views**
- Keep views focused on handling HTTP requests and responses.
- Move reusable or complex business logic into appropriate service modules when necessary.
- Use Django's built-in authentication and authorization mechanisms.
- Avoid unnecessary database queries.

**URLs**
- Define application-specific routes in each app's `urls.py`.
- Use descriptive URL names.
- Prefer Django's `reverse()` and `{% url %}` instead of hardcoded URLs.

**Templates**
- Keep business logic out of templates.
- Reuse common layouts through template inheritance.
- Escape user-generated content by default.
- Use Django template tags and filters appropriately.

**Database**
- Use Django ORM instead of raw SQL whenever practical.
- Use `select_related()` and `prefetch_related()` to avoid N+1 queries.
- Use transactions for operations requiring atomicity.
- Never modify database schemas manually without corresponding Django migrations.

### Naming Conventions

| Component | Convention | Example |
|---|---|---|
| Variables | snake_case | user_name |
| Functions | snake_case | get_articles() |
| Classes | PascalCase | ArticleService |
| Constants | UPPER_SNAKE_CASE | MAX_UPLOAD_SIZE |
| Django apps | snake_case | content_management |
| Database tables | Django conventions | app_article |

### General Principles
- Follow existing coding patterns.
- Avoid duplicated code.
- Keep functions small and focused.
- Do not introduce unnecessary design patterns.
- Do not change unrelated functionality.
- Prefer maintainability and simplicity.

---

## 4. Testing Instructions

### Testing Framework

Use Django's built-in testing framework by default.

If the project already uses pytest and pytest-django, follow the existing test setup instead of introducing another testing framework.

### Running Tests

Run all Django tests:

```bash
python manage.py test
```

Run tests for a specific application:

```bash
python manage.py test apps.content
```

Run a specific test module:

```bash
python manage.py test apps.content.tests.test_views
```

If pytest is configured:

```bash
pytest
```

### Testing Requirements

When implementing new functionality:

1. Write tests for new business logic.
2. Test successful and unsuccessful scenarios.
3. Test input validation and error handling.
4. Test authentication and authorization where applicable.
5. Test database interactions.
6. Test API responses and HTTP status codes when applicable.
7. Ensure existing tests continue to pass.

### Test Organization

Prefer organizing tests by functionality:

```text
apps/
└── content/
    ├── models.py
    ├── views.py
    ├── services.py
    └── tests/
        ├── __init__.py
        ├── test_models.py
        ├── test_views.py
        └── test_services.py
```

### Before Completing a Task

Always:
- Run relevant tests.
- Run `python manage.py check`.
- Verify that database migrations are valid.
- Fix regressions introduced by your changes.
- Report tests that could not be executed and explain why.

Do not claim that tests passed unless they were actually executed successfully.

---

## 5. Security Considerations

Security must be considered in every implementation.

### Django Security
- Never expose `SECRET_KEY` in source code.
- Set `DEBUG=False` in production.
- Configure `ALLOWED_HOSTS` explicitly.
- Use Django's built-in CSRF protection.
- Keep Django and third-party dependencies updated.
- Never disable security middleware without a documented reason.
- Do not expose sensitive information in error responses.

### Database Security
- Never hardcode PostgreSQL credentials.
- Store database credentials in environment variables or a secure secrets manager.
- Use a dedicated database user with the minimum required privileges.
- Do not use PostgreSQL superuser accounts for application connections.
- Use parameterized queries when raw SQL is necessary.
- Validate database input and enforce appropriate constraints.

### Authentication and Authorization
- Use Django's built-in authentication system.
- Enforce permissions on the backend, not only in the frontend.
- Apply role-based access control where required.
- Never trust user-supplied user IDs or permission values.
- Protect administrative endpoints.
- Use secure password hashing mechanisms provided by Django.

### Input Validation
- Validate all user-provided input.
- Use Django Forms, ModelForms, or serializers where appropriate.
- Prevent SQL injection by using Django ORM or parameterized SQL.
- Prevent Cross-Site Scripting (XSS) by escaping untrusted output.
- Validate uploaded files, including file type and size.
- Do not trust file extensions alone when validating uploads.

### Production Security
- Enable HTTPS.
- Configure secure session and CSRF cookies.
- Set appropriate security headers.
- Configure secure static and media file serving.
- Avoid exposing internal exception details.
- Ensure sensitive files such as `.env`, database backups, and private keys are excluded from version control.

### AI Agent Security Rules

When modifying this project, AI agents MUST:

1. Never reveal, log, or commit secrets and credentials.
2. Never modify production database records without explicit authorization.
3. Never execute destructive database operations without explicit approval.
4. Never disable authentication, authorization, CSRF, or security protections to bypass errors.
5. Never introduce insecure SQL queries or unsafe file-handling logic.
6. Never overwrite environment-specific configuration without understanding its impact.
7. Review security implications before introducing new dependencies or external integrations.

---

## General Instructions for AI Agents

- Read this file before making changes.
- Inspect the existing implementation before modifying code.
- Follow established project conventions.
- Make the smallest change that correctly solves the requested problem.
- Do not introduce unnecessary dependencies or abstractions.
- Do not modify unrelated files.
- Update or add tests when changing functionality.
- Explain important architectural or database changes.
- Report commands executed and their results.
- Ask for clarification before performing destructive or security-sensitive operations.