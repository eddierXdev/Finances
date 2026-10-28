# OpenCode Instructions — Resale Manager

You are assisting with the implementation of Resale Manager.

Before proposing code, read:

1. `docs/REQUIREMENTS.md`
2. `docs/ARCHITECTURE.md`
3. `docs/DATABASE.md`
4. `docs/ERD.md`
5. `docs/TECH_STACK.md`
6. `docs/ROADMAP.md`

## Core Behavior

- Follow the documented V1 scope.
- Do not introduce new major features without explicit user approval.
- Do not silently change architecture decisions.
- Do not implement credit or partial payments.
- Inventory costing is FIFO.
- Money uses Decimal, never float.
- Core application must work offline.
- elTOQUE is an optional Infrastructure provider, not a dependency.
- Direct account operations require matching account/operation currency.
- Cross-currency movement is explicit.
- Code identifiers, comments, docstrings, UI labels and technical docs should be in English.
- Explanations to the user may be in Spanish.

## Architecture Boundaries

- Presentation must not access the DB directly.
- Presentation must not calculate FIFO, COGS, profit or account balances.
- Domain must not import PySide6, SQLAlchemy, httpx or filesystem-specific code.
- Application coordinates use cases.
- Infrastructure implements persistence, providers, files and external services.
- Repositories isolate persistence.
- Do not put raw SQL in Application or Presentation.

## Implementation Style

- Work incrementally.
- Prefer small coherent commits/changes.
- Before modifying multiple files, explain the intended change briefly.
- Do not generate empty files just to mirror the architecture tree.
- Add tests with business-critical logic.
- Prefer explicit code over unnecessary abstractions.
- Do not over-engineer future cloud/mobile/multi-user requirements.
- Preserve historical data rules.

## Safety Against Scope Creep

If a requested change conflicts with existing V1 decisions:

1. Point out the conflict.
2. Explain which docs are affected.
3. Ask for approval only when the design decision truly needs to change.
4. Otherwise implement the smallest compatible change.

## First Milestone

Start only with:

- repository/project bootstrap
- pyproject
- test setup
- SQLAlchemy base/session
- SQLite
- Alembic
- Currency
- ExchangeRate
- Account
- Product
- ProductVariant

Do not implement the entire application in the first pass.
