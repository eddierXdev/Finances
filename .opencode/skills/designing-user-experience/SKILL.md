---
name: designing-user-experience
description: Improve user flows, forms, navigation, states, feedback, and task completion for the Resale Manager desktop application.
compatibility: opencode
---

# Designing User Experience

Use this skill before or during implementation of a user flow.

## Core Principles

- Optimize for task completion, not decoration.
- Reduce unnecessary steps.
- Keep important actions visible.
- Avoid asking for information before it is needed.
- Show only relevant fields.
- Preserve user context.
- Make errors recoverable.
- Protect destructive actions.
- Use plain language in UI copy.
- Keep important status information visible.

## Important Flows

- Create product
- Register purchase
- Receive purchase
- Register sale
- Register customer return
- Register supplier return
- Register expense
- Add/withdraw capital
- Exchange currency
- Review dashboard
- Review inventory

## Forms

Every field is:

- REQUIRED
- OPTIONAL
- CONDITIONALLY_REQUIRED

Do not force irrelevant fields.

Group related fields.

Avoid giant unstructured forms.

## Validation

Validation should:

- Explain what is wrong
- Explain where it is wrong
- Preserve valid input
- Avoid generic "Invalid data" messages
- Prefer inline errors

## Navigation

The user should know:

- Where they are
- What they are editing
- How to go back
- Whether changes are saved
- What the primary action is

## Empty States

Do not show blank panels.

Useful empty states explain:

- What belongs here
- Why it is empty
- What the user can do next

## Error States

Prefer specific and actionable errors.

Example:

"Not enough stock to complete this sale. Available: 3 units."

## Success Feedback

Use lightweight confirmation for important operations.

Avoid excessive modal dialogs for routine success messages.

## Destructive Actions

Require confirmation for significant destructive actions.

Prefer reversal/cancellation over destructive deletion where history matters.

## Progressive Disclosure

Do not show advanced options until needed.

Examples:

- Purchase cost allocation
- Manual FX override
- Additional supplier details
- Return condition details

## Review Checklist

1. What is the user trying to accomplish?
2. Can it be completed without unnecessary navigation?
3. Are required fields obvious?
4. Are irrelevant fields hidden?
5. Are errors recoverable?
6. Is the primary action obvious?
7. Are dangerous actions protected?
8. Is the empty state useful?
9. Does the workflow remain understandable in Spanish and English?
10. Does it preserve business history correctly?
