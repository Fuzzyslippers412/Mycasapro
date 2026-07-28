# MyCasaPro Redesign and Real-Data Build Plan

## Status

This document is the active product and interface plan for the next build cycle. It supersedes the visual direction and demo-first assumptions in the earlier homeowner and contractor dashboard plans.

## Product standard

MyCasaPro should feel like a dependable operating system for a home, not a marketing page wrapped around forms.

The interface must answer four questions quickly:

1. What needs my attention?
2. What is happening next?
3. What has changed?
4. What money is due or already paid?

Homeowners should feel calm and in control. Contractors should be able to move through real work quickly from a phone.

## Real-data policy

Production and normal local development must never invent records to make a screen look populated.

### Required rules

- No fallback `homeowner-demo` or `contractor-demo` identities in the application UI.
- No automatic seed records in the default server startup path.
- No hard-coded properties, repairs, appointments, estimates, invoices, messages, counts, or activity.
- No explanatory cards that imply a feature or record exists when it does not.
- No in-memory store in the normal product run command. PostgreSQL is the default source of truth.
- Loading states use skeletons, not temporary numbers or sample records.
- Empty states describe the real account state and offer one relevant action.
- Test fixtures remain isolated in test files and are never included in a production bundle.
- An optional demo environment may exist later, but it must use a separate database and display a visible `Demo` badge.

### Fresh-account behavior

A newly registered homeowner sees an onboarding screen with one primary action: add the first property. The dashboard does not render four zero-value statistic cards.

A newly registered contractor sees organization setup. Job, quote, schedule, and invoice surfaces appear only after the organization exists.

## Visual direction

### Concept: architectural clarity

The new design combines the precision of a residential plan set with the warmth of a trusted home service. It should be crisp, bright, and operational.

### Color system

- Canvas: cool off-white `#F5F7FA`
- Surface: white `#FFFFFF`
- Primary ink: deep slate `#172033`
- Secondary ink: `#5B6475`
- Primary action: cobalt `#2457D6`
- Action hover: `#1C45AD`
- Urgent/action required: safety orange `#E9673F`
- Success/completed: `#2F8A68`
- Warning: `#D99A2B`
- Border: `#DCE1E8`

Color communicates state. The app will not use decorative beige gradients, glass panels, or blurred ambient shapes.

### Typography

- Interface and data: a highly legible modern sans face.
- Brand wordmark: may use a restrained display face, but never for metric values or long headings.
- Headings use compact scale and strong hierarchy.
- Body copy stays short; the product does not explain itself inside every card.

### Shape and depth

- 10-14px card radius, not oversized pill-shaped containers.
- 1px structural borders and restrained shadows.
- Buttons use 8-10px radius; only tags and status chips are fully rounded.
- Dense information uses rows and tables where they scan better than cards.

### Motion

- One short page-entry transition.
- Clear loading skeletons.
- State changes animate only when they help users notice an update.
- Respect `prefers-reduced-motion`.

## Application shell

### Desktop

- 232px left navigation rail.
- Property or organization switcher at the top of the main workspace.
- Compact page header with title, context, and one primary action.
- Main content width up to 1440px with a deliberate 12-column layout.
- Persistent account/help controls at the bottom of the rail.

### Mobile

- Compact top bar with current property or organization.
- Bottom navigation for the four most-used destinations.
- Sticky primary action for `Report an issue` or `New job update` where appropriate.
- Forms open as focused full-screen flows instead of living permanently on dashboards.

## Homeowner information architecture

Primary navigation:

- Overview
- Repairs
- Calendar
- Payments
- Home record
- Messages

### Homeowner overview

The first screen is ordered by urgency, not by database entity.

1. Header with property switcher and `Report an issue` action.
2. `Needs your attention` queue for estimates, schedule confirmations, and unpaid invoices.
3. `Next at your home` appointment card with contractor, date, arrival window, and project.
4. Active repairs shown as a compact progress list.
5. Financial summary using actual outstanding and recently paid amounts.
6. Recent activity from the real project timeline.

If a section has no records, it collapses or shows one small empty row. The page must not become a wall of empty cards.

### Repair intake

`Report an issue` is a dedicated guided flow:

1. Select property and room/area.
2. Describe the problem.
3. Add photos or video.
4. Set urgency and access preferences.
5. Review and submit.

Inputs use visible labels. Example values may appear as helper copy, never as fake saved content.

## Contractor information architecture

Primary navigation:

- Today
- Requests
- Jobs
- Calendar
- Clients
- Invoices

### Contractor overview

1. Today's visits and overdue actions.
2. New requests requiring a response.
3. Estimates awaiting homeowner action.
4. Active jobs grouped by stage.
5. Receivables and payout status from real ledger data.

The contractor surface is denser than the homeowner surface. It prioritizes scanning and one-handed mobile actions.

## Shared project workspace

Every project uses the same factual record for both parties, with role-appropriate controls.

Tabs:

- Overview
- Scope and estimates
- Schedule
- Updates
- Files
- Payments

The overview shows current status, next action, next visit, approved amount, paid amount, and latest update. Long forms move into drawers or dedicated flows.

## State model

Every data surface must implement these states explicitly:

| State | Required treatment |
| --- | --- |
| Loading | Layout-matched skeleton; no sample values |
| Empty | Accurate explanation plus one useful action |
| Error | Plain-language failure, retry action, preserved user input |
| Partial | Render available sections and identify the failed section |
| Ready | Real API data only |
| Mutating | Disable duplicate submission and show progress |
| Success | Confirm the saved action and update the affected data |

## Build order

### Stage 1: data truth and identity

- Make PostgreSQL the normal local and production backend.
- Add account registration, login, logout, secure cookie sessions, and current-user API.
- Replace path IDs and environment demo IDs with the authenticated user identity.
- Add role-aware authorization to every homeowner and contractor route.
- Remove local seeded memory records and restart the preview with a fresh database.

Exit criteria:

- A new browser session starts with no records.
- A user can create an account and only access their own data.
- Restarting the app preserves all created records.
- No `*-demo` identity appears in a production frontend bundle.

### Stage 2: design system and application shell

- Replace the current global tokens, gradient background, glass cards, and giant serif hero.
- Add the desktop navigation rail and mobile bottom navigation.
- Build reusable page header, action queue, data row, status badge, empty state, skeleton, form field, modal/drawer, and toast components.
- Add accessible focus, keyboard, contrast, and reduced-motion behavior.

Exit criteria:

- Homeowner and contractor shells feel like one product with role-specific workflows.
- Layout passes at 360px, 768px, 1280px, and 1440px.
- All controls have visible labels and keyboard focus.

### Stage 3: homeowner rebuild

- Replace the current card wall with the priority-based overview.
- Move property creation into first-run onboarding and settings.
- Move repair creation into the dedicated intake flow.
- Build repairs list/detail, calendar, payment center, and home record navigation surfaces.
- Connect every count, amount, date, and event to a real API field.

Exit criteria:

- A new homeowner can add a home and report an issue without seeing sample content.
- A returning homeowner can identify the next action in under five seconds.
- No setup form permanently occupies the dashboard.

### Stage 4: contractor rebuild

- Add contractor onboarding and organization setup.
- Build Today, Requests, Jobs, Calendar, Clients, and Invoices surfaces.
- Replace `Convert to project` with explicit accept, decline, and assignment workflow.
- Add responsive field actions for updates, photos, schedule, estimates, and invoices.

Exit criteria:

- A contractor can handle a new request through invoice from a phone.
- Internal notes never leak into homeowner views.
- Every job action updates the shared timeline.

### Stage 5: real files and payments

- Add signed object-storage upload and download flows.
- Add attachment metadata, ownership checks, file limits, and malware scanning hook.
- Integrate Stripe payments and Stripe Connect payouts.
- Replace manual `record payment` behavior with provider-confirmed webhook events.
- Add an immutable payment ledger and reconciliation jobs.

Exit criteria:

- Photos and documents survive app restarts and are access-controlled.
- Money states come from payment-provider events, not user-entered claims.
- Every payment is tied to an approved estimate, change order, or invoice.

### Stage 6: quality gate

- Add end-to-end tests for fresh onboarding and the full homeowner/contractor workflow.
- Add visual regression coverage for key desktop and mobile screens.
- Add empty, error, partial, slow-network, and retry test cases.
- Run accessibility, performance, security, and authorization checks.

Exit criteria:

- No fake-data paths exist in normal runtime.
- Core flows pass against a fresh PostgreSQL database.
- The web app has no critical accessibility violations.
- Mobile field workflows work on narrow and low-bandwidth connections.

## Immediate implementation slice

The next build slice is intentionally narrow and foundational:

1. Remove demo identity fallbacks.
2. Add real session-backed identity.
3. Make the standard local command use PostgreSQL.
4. Rebuild the application shell and fresh-account onboarding.
5. Rebuild the homeowner overview against empty and real account states.

We should not spend time polishing the current dashboard because its information architecture is being replaced.
