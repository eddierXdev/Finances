---
name: reviewing-interface-quality
description: Audit the current Resale Manager interface for visual hierarchy, consistency, spacing, accessibility, localization risks, duplicated styling, Qt-default appearance, and maintainability.
compatibility: opencode
---

# Reviewing Interface Quality

Use this skill to audit an existing Resale Manager screen or UI implementation.

Do not change Domain or Application logic unless a UI issue reveals a genuine architectural violation.

## Review Categories

### Visual Hierarchy

Check:

- Page title prominence
- Section boundaries
- Primary action prominence
- Secondary action de-emphasis
- Metric readability
- Clear information grouping

### Spacing

Check:

- Consistent margins
- Consistent padding
- Row spacing
- Section spacing
- Alignment across components

### Typography

Check:

- Too many font sizes
- Excessive bold text
- Poor contrast
- Weak distinction between primary/secondary text
- Inconsistent number formatting

### Qt Default Appearance

Identify raw/default Qt-looking controls.

Prefer reusable components and centralized QSS.

Do not fix this with scattered inline styles.

### Tables

Check:

- Header readability
- Numeric alignment
- Row density
- Selection state
- Empty state
- Action placement
- Long text handling
- Column sizing

### Forms

Check:

- Required/optional clarity
- Conditional fields
- Validation placement
- Overly long forms
- Label alignment
- Field grouping

### Themes

Review both light and dark:

- Contrast
- Borders
- Disabled controls
- Selection colors
- Hover states
- Tables/charts

Flag hardcoded colors in widgets.

### Localization

Check English and Spanish compatibility.

Look for:

- Hardcoded user-facing strings
- Fixed-width controls that break in Spanish
- Truncated labels
- Untranslated enum values
- Layouts dependent on English text length

### Accessibility

Check:

- Contrast
- Keyboard focus visibility
- Logical tab order
- Reliance on color alone
- Descriptive labels
- Readable font sizes

### Architecture

UI must not contain:

- FIFO calculations
- COGS calculations
- Profit calculations
- Account balance rules
- Exchange-rate business rules
- Raw SQL

## Output Format

When reviewing, produce:

1. Critical issues
2. Important improvements
3. Minor polish
4. Reusable component opportunities
5. Architecture violations
6. Localization/theme risks

Then implement only UI changes.
