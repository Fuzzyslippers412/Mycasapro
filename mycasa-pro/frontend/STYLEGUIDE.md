# MyCasa Pro UI Rules

## Design Tokens
- Use `frontend/src/theme/tokens.ts` for spacing, radius, colors, typography, shadows.
- No raw hex colors outside theme/token files.
- Avoid inline styles unless required.

## Layout
- Each page uses `Page` layout component.
- Title row includes actions on the right.
- Use consistent paddings and max-width containers.

## Components
- Cards, Buttons, Inputs must use Mantine theme defaults.
- All widgets must use `WidgetCard`.

## States
- Loading: skeletons required.
- Empty: icon + message + CTA.
- Error: compact alert + retry.

## Accessibility
- Keep focus rings visible.
- Minimum contrast: 4.5:1.
- Keyboard navigation works on all interactive elements.
