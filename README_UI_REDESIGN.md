# Resale Manager — UI Redesign Plan

## 1. Purpose

This document defines the incremental UI modernization plan for Resale Manager.

The current V1 business functionality is already mostly complete. The goal is to improve the Presentation layer without rewriting or destabilizing the application.

The redesign must preserve:

- Domain rules
- Application use cases
- FIFO logic
- Inventory behavior
- Purchases
- Sales
- Customer returns
- Supplier returns
- Accounts
- Capital
- Expenses
- Exchange-rate behavior
- Database integrity
- Offline-first behavior

This is a Presentation-layer modernization, not a business-logic rewrite.

---

# 2. Main Goals

The redesigned application should feel like a polished desktop business-management application rather than a default Qt prototype.

Primary goals:

- Modern visual hierarchy
- Consistent spacing
- Better typography
- Professional sidebar/navigation
- Reusable UI components
- High-quality tables
- Clear forms
- Better Dashboard
- Light theme
- Dark theme
- System theme
- English
- Spanish
- Accessible keyboard navigation
- Good empty/error/success states
- Better chart visualization
- Consistent visual language across screens

---

# 3. Non-Goals

The UI redesign must not:

- Rewrite the application from scratch
- Replace the Domain layer
- Replace Application use cases
- Change FIFO behavior
- Move business logic into widgets
- Add raw SQL to Presentation
- Let widgets calculate COGS
- Let widgets calculate profit
- Let widgets calculate account balances
- Let charts query the database directly
- Add credit or partial payments
- Introduce unrelated V2 business features
- Redesign every screen in a single change

---

# 4. UI Architecture

The Presentation layer should progressively evolve toward:

```text
app/
└── presentation/
    └── desktop/
        ├── views/
        │   ├── dashboard/
        │   ├── products/
        │   ├── inventory/
        │   ├── purchases/
        │   ├── sales/
        │   ├── returns/
        │   ├── finances/
        │   ├── currencies/
        │   └── settings/
        ├── components/
        │   ├── page_header.py
        │   ├── stat_card.py
        │   ├── status_badge.py
        │   ├── data_table.py
        │   ├── buttons.py
        │   ├── section_card.py
        │   ├── empty_state.py
        │   ├── search_field.py
        │   └── filter_bar.py
        ├── navigation/
        │   └── sidebar.py
        ├── i18n/
        │   ├── translator.py
        │   ├── en.json
        │   └── es.json
        ├── themes/
        │   ├── theme_manager.py
        │   ├── light.qss
        │   └── dark.qss
        └── charts/
            ├── chart_widget.py
            ├── sales_chart.py
            ├── profit_chart.py
            └── product_chart.py
```

Do not create empty files merely to match this structure. Create components only when they are needed.

---

# 5. Visual Direction

The visual direction is:

```text
Modern business desktop application
```

The interface should be clean, professional, compact but not cramped, consistent, readable, information-dense without clutter, accessible, and suitable for long desktop sessions.

Avoid:

- Default-looking Qt widgets
- Random colors
- Excessive gradients
- Excessive rounded cards
- Huge buttons
- Excessive shadows
- Too many borders
- Arbitrary margins
- Inconsistent padding
- Decorative elements that reduce clarity

---

# 6. Design System

## Spacing

Use a consistent spacing scale:

```text
4
8
12
16
24
32
48
```

## Typography

Use a clear hierarchy:

```text
Page Title
Section Title
Metric Value
Body Text
Secondary Text
Caption
```

Do not make every label bold.

## Semantic Colors

Use semantic design concepts instead of hardcoding colors throughout widgets:

```text
background
surface
surface_elevated
text_primary
text_secondary
border
primary
success
warning
danger
```

---

# 7. Reusable Components

Initial component candidates:

```text
PageHeader
SidebarItem
StatCard
StatusBadge
PrimaryButton
SecondaryButton
DestructiveButton
DataTable
SectionCard
EmptyState
SearchField
FilterBar
FormField
ConfirmDialog
```

Do not create an abstraction for something used only once without a clear reason.

---

# 8. Localization

Supported V1 UI languages:

```text
English (en)
Spanish (es)
```

Rules:

- Code identifiers remain English.
- Enum values remain English.
- Database values remain language-independent.
- User-created business data is never automatically translated.
- User-facing application text should use translation keys.
- Spanish text must not break layouts.
- The selected language is persisted locally.

Concept:

```text
Presentation
     ↓
Translator
     ↓
Translation Catalog
     ├── en.json
     └── es.json
```

Examples:

```text
navigation.dashboard
navigation.inventory
common.save
common.cancel
dashboard.net_profit
order_status.partially_received
```

---

# 9. Theme System

Supported themes:

```text
LIGHT
DARK
SYSTEM
```

Rules:

- Styling must be centralized.
- Prefer QSS/theme infrastructure.
- Avoid repeated inline setStyleSheet().
- Individual widgets should not own unrelated hardcoded theme colors.
- Theme selection is persisted locally.
- Runtime theme switching should work where practical.

---

# 10. Dashboard Visualization

The Dashboard should prioritize:

- Available capital
- Inventory value
- Revenue
- Gross profit
- Net profit
- Expenses

Recommended layout:

```text
┌────────────────────────────────────────────────────┐
│ Dashboard                            Period filter  │
│ Business overview                                  │
│                                                    │
│ ┌───────────┐ ┌───────────┐ ┌───────────┐         │
│ │ Capital   │ │ Revenue   │ │ Net Profit│         │
│ │ $1,220    │ │ $2,840    │ │ $630      │         │
│ └───────────┘ └───────────┘ └───────────┘         │
│                                                    │
│ ┌────────────────────────┐ ┌─────────────────────┐ │
│ │ Sales Evolution        │ │ Revenue / Expenses  │ │
│ │        CHART           │ │        CHART        │ │
│ └────────────────────────┘ └─────────────────────┘ │
│                                                    │
│ ┌──────────────────────┐ ┌───────────────────────┐ │
│ │ Top Products         │ │ Low Stock             │ │
│ └──────────────────────┘ └───────────────────────┘ │
└────────────────────────────────────────────────────┘
```

---

# 11. Charts

Plotly may be used for Dashboard charts if it can be integrated without violating architecture boundaries.

Recommended flow:

```text
Database
    ↓
Repository
    ↓
Application / Analytics Use Case
    ↓
Prepared Chart Data
    ↓
Presentation
    ↓
Plotly
```

Charts must not query the database, call repositories directly, calculate FIFO, calculate COGS, calculate profit, calculate account balances, or implement financial rules.

Use a reusable abstraction:

```text
ChartWidget
    ↓
QWebEngineView
    ↓
Plotly
```

Charts must support Light, Dark, English and Spanish.

---

# 12. Tables

Tables should have:

- Clear headers
- Consistent row height
- Proper numeric alignment
- Sensible column sizing
- Selection states
- Hover states when appropriate
- Empty states
- Clear actions
- Good handling of long text

Money values should align consistently.

---

# 13. Forms

Forms should clearly distinguish:

```text
REQUIRED
OPTIONAL
CONDITIONALLY_REQUIRED
```

Rules:

- Group related information.
- Hide or disable irrelevant conditional fields.
- Display validation near the relevant control.
- Avoid giant unstructured forms.
- Preserve valid user input when validation fails.
- Do not rely on placeholders as the only labels.

---

# 14. Accessibility

The redesigned UI must preserve or improve:

- Keyboard navigation
- Visible focus state
- Logical tab order
- Readable contrast
- Descriptive labels
- Error communication
- Status communication that does not rely only on color

---

# 15. Redesign Phases

The redesign must be incremental.

## Phase UI-0 — Freeze and Audit Current V1

Goal: establish a stable baseline before visual refactoring.

Tasks:

- Create a dedicated UI-redesign Git branch.
- Run the current test suite.
- Verify critical workflows manually.
- Review current Presentation structure.
- Identify inline styles and hardcoded strings.
- Identify shared visual patterns.
- Identify architecture violations in UI code.

Critical workflows:

```text
Products
Purchases
Receiving
Inventory
Sales
FIFO
Customer Returns
Supplier Returns
Accounts
Expenses
Capital
Exchange Rates
```

Exit criteria:

- Existing V1 functionality is known to work.
- Current failures are documented before UI changes.
- UI redesign has an isolated Git branch.

---

## Phase UI-1 — Localization Infrastructure

Goal: add English/Spanish support before further UI expansion.

Implement:

```text
Translator
en.json
es.json
```

Persist:

```text
ui.language
```

Exit criteria:

- English works.
- Spanish works.
- Language selection persists.
- Existing screens remain functional.

---

## Phase UI-2 — Theme Infrastructure

Goal: centralize the application's visual theme.

Implement:

```text
ThemeManager
light.qss
dark.qss
SYSTEM behavior
```

Persist:

```text
ui.theme
```

Exit criteria:

- Light theme works.
- Dark theme works.
- System mode works or has a documented fallback.
- Existing screens remain usable.

---

## Phase UI-3 — Core Design System

Goal: create the reusable visual foundation.

Initial components:

```text
PageHeader
PrimaryButton
SecondaryButton
StatusBadge
StatCard
EmptyState
SectionCard
```

Establish spacing, typography, semantic colors and border/radius conventions.

Exit criteria:

- Shared components are reusable.
- Styling is centralized.
- New UI work does not require arbitrary styling on each screen.

---

## Phase UI-4 — Application Shell and Navigation

Goal: modernize the application's main visual structure.

Implement/improve:

- Main window
- Sidebar
- Sidebar items
- Page content container
- Page headers
- Navigation states
- Settings placement

Exit criteria:

- Navigation works exactly as before.
- Current screen is visually identifiable.
- Layout works in English and Spanish.
- Light/dark themes work.

---

## Phase UI-5 — Dashboard V2

Goal: turn the Dashboard into the visual reference for the rest of the application.

Implement:

- Page header
- Date/period filter
- Metric cards
- Sales evolution
- Revenue vs expenses
- Top products
- Low-stock / attention area
- Empty states

Initial metrics:

```text
Available Capital
Inventory Value
Revenue
Gross Profit
Net Profit
Expenses
```

Exit criteria:

- Dashboard uses existing business data.
- No business calculation was moved into widgets.
- Dashboard works in both themes.
- Dashboard works in English and Spanish.

---

## Phase UI-6 — Chart Infrastructure

May be implemented together with UI-5 when practical.

Goal: introduce reusable interactive visualizations.

Implement:

```text
ChartWidget
SalesEvolutionChart
RevenueExpenseChart
```

Use Plotly only for visualization.

Exit criteria:

- No direct DB access from charts.
- No chart-specific business logic.
- Charts work offline with local data.

---

## Phase UI-7 — Products and Inventory

Goal: migrate product/inventory screens to the new design system.

Improve:

- Product table
- Variant display
- Search/filter controls
- Stock values
- Low-stock status
- Empty state
- Add/edit product flow

---

## Phase UI-8 — Purchases and Receiving

Goal: modernize purchase and order workflows.

Improve:

- Purchase list
- Purchase statuses
- Supplier display
- Purchase form
- Additional costs
- Partial receipt flow
- Order tracking
- Cost allocation presentation

---

## Phase UI-9 — Sales and Customer Returns

Goal: modernize sales workflows.

Improve:

- Sale list
- Register-sale UI
- Product selection
- Price/discount presentation
- Customer selection
- Refund/return UI
- SELLABLE/DAMAGED presentation

Do not alter FIFO or refund business logic.

---

## Phase UI-10 — Supplier Returns

Goal: bring supplier-return workflows into the same visual system.

Improve:

- Supplier return list
- Return form
- Lot/product identification
- Supplier refund presentation
- Status feedback

---

## Phase UI-11 — Finances

Goal: modernize:

- Accounts
- Expenses
- Capital
- Transfers
- Transactions

Visual priorities:

- Currency clarity
- Money alignment
- Inflow/outflow distinction
- Account balance readability

Color must not be the only indicator of financial direction.

---

## Phase UI-12 — Currency and Exchange Rates

Goal: modernize:

- Manual rates
- Automatic rates
- Rate history
- Converter
- Stale-rate warnings
- Provider information

Clearly display:

```text
Rate
Source
Timestamp
Age
Stale status
```

---

## Phase UI-13 — Settings

Goal: complete centralized preferences.

Settings include:

### Appearance

```text
Language
Theme
```

### Currency

```text
Base Currency
Enabled Currencies
```

### Exchange Rates

```text
Provider
Automatic Updates
Freshness Threshold
```

### Application

```text
Date Format
Backup Location
```

---

## Phase UI-14 — Global Interface Review

Goal: audit the complete UI after all screens are migrated.

Review:

- Visual hierarchy
- Spacing
- Typography
- Tables
- Forms
- Themes
- Localization
- Accessibility
- Empty states
- Error states
- Success feedback
- Reusable component usage
- Architecture boundaries

Do not add new business functionality in this phase.

---

## Phase UI-15 — Polish and Release Validation

Tasks:

- Run all tests.
- Manually test English.
- Manually test Spanish.
- Test Light theme.
- Test Dark theme.
- Test System theme.
- Test common window sizes.
- Test keyboard navigation.
- Test Dashboard charts.
- Test empty databases.
- Test populated databases.
- Test validation errors.
- Test offline mode.

Exit criteria:

- Existing V1 functionality remains intact.
- All migrated screens share one design system.
- Themes are consistent.
- Localization is consistent.
- Charts follow architecture rules.
- Core workflows remain usable with keyboard navigation.

---

# 16. OpenCode Workflow

OpenCode should work one phase at a time.

Before every phase:

1. Read this document.
2. Inspect current implementation.
3. Identify files that will change.
4. Identify regression risks.
5. Explain the intended change briefly.

After every phase:

1. List changed files.
2. Run relevant tests.
3. Explain manual verification steps.
4. Stop before beginning the next phase.

Do not automatically continue to another redesign phase.

---

# 17. OpenCode Prompt — Phase UI-1 to UI-3

```text
Read README_UI_REDESIGN.md and the existing project documentation.

Implement only:
- Phase UI-1
- Phase UI-2
- Phase UI-3

Do not redesign screens yet.

Preserve all existing business functionality.

Before editing:
1. inspect the current Presentation structure,
2. list planned file changes,
3. identify regression risks.

After implementation:
1. run relevant tests,
2. list changed files,
3. explain manual verification,
4. stop.
```

---

# 18. OpenCode Prompt — Shell and Dashboard

After UI-1 through UI-3 are stable:

```text
Read README_UI_REDESIGN.md.

Implement only:
- Phase UI-4
- Phase UI-5
- Phase UI-6

Preserve all business logic and existing workflows.

Do not redesign Products, Inventory, Purchases, Sales, Returns, Finances, Currencies, or Settings yet.

Charts must receive prepared data from Application/use cases and must not access the database directly.

Before editing:
- audit the current shell and Dashboard,
- list critical UI issues,
- list reusable component opportunities,
- list planned file changes.

After implementation:
- run tests,
- provide manual verification steps for themes, languages, navigation and Dashboard,
- stop.
```

---

# 19. OpenCode Prompt — Individual Screen Migration

```text
Read README_UI_REDESIGN.md.

Implement only Phase UI-X.

Use the existing design system established by the Dashboard.

Do not change Domain or Application business logic.

Do not begin another phase after completing this one.

Before editing:
- audit the current screen,
- identify reusable components,
- identify regression risks.

After implementation:
- run relevant tests,
- list changed files,
- explain manual verification,
- stop.
```

---

# 20. Final Rule

The UI redesign is successful only if the application becomes visually better **without reducing the reliability of the existing V1**.

Presentation may change substantially.

Business behavior must remain stable.
