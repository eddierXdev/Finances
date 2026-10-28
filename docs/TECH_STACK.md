# Resale Manager — Tech Stack

## V1 Recommended Stack

### Language

Python 3.12+

### Desktop UI

**PySide6**

`PySide6-Essentials` is sufficient: it ships Qt Core, Gui and Widgets without
the optional Addons (WebEngine, PDF, 3D) this application does not use.

Reasons:

- Mature Qt ecosystem
- Good desktop widgets/tables/dialogs
- Suitable for dashboards
- Works well with Python
- Better long-term desktop structure than a minimal GUI toolkit

The UI must remain isolated from Domain/Application logic.

### Database

**SQLite**

Reasons:

- Offline-first
- Zero external database server
- Easy local backup
- Good fit for single-user desktop V1

Use SQLite foreign keys explicitly.

Future target may be PostgreSQL without changing Domain rules.

### ORM

**SQLAlchemy 2.x**

Use modern typed declarative models.

Do not let ORM models become Domain entities by default.

### Migrations

**Alembic**

Every schema change after initial baseline should be represented by a migration.

### Validation / Settings

- `pydantic`
- `pydantic-settings`

Use settings for application configuration, not Domain rules.

### HTTP

**httpx**

Used only by Infrastructure providers such as elTOQUE.

Network calls must not block the main UI thread.

### Decimal Money

Python `decimal.Decimal`.

Never use `float` for business money.

### Testing

- `pytest`
- `pytest-cov`

Focus first on Domain/Application unit tests.

### Export

Start simple:

- CSV built-in / pandas only if justified
- XLSX later with `openpyxl`
- PDF only when reporting requirements are clear

Avoid adding heavy dependencies prematurely.

### Packaging

V1 development:

```text
pyproject.toml
virtual environment
```

Later desktop distribution can use PyInstaller or another packaging tool after the app is stable.

---

## Suggested Core Dependencies

```toml
sqlalchemy
alembic
pydantic
pydantic-settings
pyside6-essentials
httpx
pytest
pytest-cov
```

Do not install everything on day one if the current milestone does not need it.

---

## Engineering Rules

- Python-facing identifiers in English.
- Type hints for public functions.
- Decimal for money.
- Enums for finite business states.
- No raw SQL in Presentation/Application.
- No HTTP calls in Domain.
- No PySide imports in Domain/Application.
- No business calculation inside Qt widgets.
- Repositories hide persistence implementation.
- Tests accompany business-critical behavior.
