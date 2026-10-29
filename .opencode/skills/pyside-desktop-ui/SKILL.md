---
name: pyside-desktop-ui
description: Design, review, and improve the Resale Manager PySide6 desktop interface with polished desktop UX, consistent spacing, reusable components, themes, localization, tables, forms, dashboards, and clear visual hierarchy.
compatibility: opencode
---

# PySide6 Desktop UI Design

Use this skill when designing, reviewing, or implementing the Resale Manager desktop interface.

## Goal

Build a polished, modern desktop interface for Resale Manager.

The application must not look like a default Qt application.

## Visual Direction

Prioritize:

- Clear visual hierarchy
- Consistent spacing
- Strong typography hierarchy
- Professional tables
- Clear primary and secondary actions
- Good information density without clutter
- Consistent radius and border system
- Accessible contrast
- Subtle elevation
- Reusable visual patterns
- Light, dark, and system themes
- English and Spanish compatibility

Avoid:

- Default-looking Qt widgets
- Random colors
- Excessive gradients
- Excessive rounded cards
- Oversized controls
- Inconsistent padding
- Too many borders
- Decorative elements that reduce clarity

## Layout System

Use a consistent spacing scale:

- 4
- 8
- 12
- 16
- 24
- 32
- 48

Prefer:

- Sidebar navigation
- Page header
- Main content area
- Stat/metric cards
- Filter/action toolbar
- Table or structured content region

Use Qt layouts instead of fixed positioning.

## Typography

Use a hierarchy:

- Page title
- Section title
- Metric value
- Body text
- Secondary text
- Caption

Do not make every label bold.

## Reusable Components

Prefer:

- PageHeader
- SidebarItem
- StatCard
- DataTable
- EmptyState
- SearchField
- FilterBar
- PrimaryButton
- SecondaryButton
- DestructiveButton
- StatusBadge
- CurrencyBadge
- FormField
- SectionCard
- ConfirmDialog

## Dashboard

Prioritize:

- Available capital
- Inventory value
- Revenue
- Gross profit
- Net profit
- Expenses

Charts should improve interpretation, not decorate the page.

## Tables

Tables should provide:

- Clear headers
- Consistent row height
- Proper numeric alignment
- Search/filter support where applicable
- Empty state
- Selection state
- Hover state where appropriate
- Clear row actions

## Forms

Clearly distinguish:

- Required
- Optional
- Conditionally required

Hide or disable irrelevant conditional fields.

Show validation errors near the relevant control.

## Theme System

Support:

- LIGHT
- DARK
- SYSTEM

Use semantic tokens:

- background
- surface
- surface_elevated
- text_primary
- text_secondary
- border
- primary
- success
- warning
- danger

Do not hardcode theme colors inside widgets.

Prefer centralized QSS.

## Localization

Support English and Spanish.

Internal identifiers and enums remain in English.

User-created business data is never automatically translated.

Avoid hardcoded translatable user-facing strings.

## PySide6 Rules

- Use layouts, not fixed coordinates.
- Avoid repeated inline setStyleSheet().
- Prefer centralized QSS.
- Keep Presentation separate from Domain/Application.
- Widgets must not calculate FIFO, COGS, profit, account balances, or exchange-rate business rules.

## UX States

Every major screen should consider:

- Empty
- Populated
- Validation error
- Operation error
- Success feedback
- Disabled state
- Loading/progress when relevant

## Review Checklist

1. Is visual hierarchy obvious?
2. Is spacing consistent?
3. Does it avoid the default Qt look?
4. Are primary actions obvious?
5. Are tables readable?
6. Are empty/error states useful?
7. Does dark mode remain readable?
8. Does Spanish text fit correctly?
9. Are reusable components used?
10. Is business logic outside Presentation?
