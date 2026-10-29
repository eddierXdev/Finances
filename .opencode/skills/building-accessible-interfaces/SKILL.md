---
name: building-accessible-interfaces
description: Improve accessibility of the Resale Manager PySide6 desktop UI, including keyboard navigation, focus states, contrast, labels, status communication, and color-independent meaning.
compatibility: opencode
---

# Building Accessible Interfaces

Use this skill when implementing or reviewing desktop controls, forms, tables, navigation, dialogs, themes, or validation.

## Keyboard Navigation

Review:

- Logical tab order
- Focus visibility
- Dialog navigation
- Buttons reachable by keyboard
- Table keyboard usability
- Escape/close behavior where appropriate

Do not remove visible focus indicators.

## Labels

Inputs need clear labels.

Do not rely only on placeholder text.

Labels should work in English and Spanish.

## Contrast

Ensure sufficient contrast for:

- Primary text
- Secondary text
- Disabled text
- Borders
- Selected rows
- Error messages
- Warning messages
- Buttons

Review both light and dark themes.

## Color Independence

Do not communicate state using color alone.

Use text and/or icons together with color.

## Validation

Validation must:

- Identify the field
- Explain the problem
- Remain visible long enough to understand
- Not rely only on red borders

## Status and Feedback

Important states need text labels.

Examples:

- Received
- Partially received
- Cancelled
- Refunded
- Damaged
- Sellable

## Tables

Tables should have:

- Readable headers
- Predictable keyboard focus
- Clear selected state
- Sufficient contrast
- Accessible action controls

## Dialogs

Dialogs should:

- Have clear title
- State consequences
- Identify primary/secondary actions
- Use explicit destructive labels

Prefer "Cancel sale" over "Yes".

## Text Scaling and Layout

Avoid layouts that break when labels grow.

Spanish strings may be longer than English.

Avoid unnecessary fixed widths.

## Accessibility Review Checklist

1. Can workflows be completed with keyboard navigation?
2. Is focus visible?
3. Do controls have labels?
4. Is contrast acceptable in light/dark themes?
5. Is status understandable without color?
6. Are validation messages descriptive?
7. Are dialogs explicit?
8. Does Spanish text fit?
9. Are disabled states readable?
10. Are important actions discoverable?
