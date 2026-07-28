# MyCasaPro Premium Home and Pro Plan

## Product Position

MyCasaPro is the private operating system for a home and the professional work desk for the people who maintain it.

It must feel like a premium residential concierge to a homeowner and like serious field-service software to a licensed contractor, specialty trade, or independent handyman. The two experiences share one trusted job record, but they do not share the same interface or information density.

## Non-Negotiable Product Rules

1. The home, not the user account, is the primary homeowner object.
2. Every screen must reflect real records. Empty accounts remain intentionally empty.
3. No contractor receives an exact address, access instructions, private documents, or unrestricted photo access merely because a request exists.
4. A contractor cannot seize a homeowner request. Contractors may be invited, express interest, or submit a quote; the homeowner awards the work.
5. Handymen and licensed trades are both first-class professionals. Credential requirements depend on the service and jurisdiction.
6. Estimates, approvals, appointments, changes, invoices, payments, receipts, and warranties remain attached to one repair timeline.
7. The interface must work cleanly on a phone at a job site and on a larger homeowner screen.

## Experience Architecture

### Homeowner Routes

- `/home` selects or creates a home.
- `/home/{homeID}` is the personalized home concierge.
- `/home/{homeID}/repairs` contains open and completed work.
- `/home/{homeID}/maintenance` contains recurring and preventive care.
- `/home/{homeID}/calendar` contains visits, reminders, and maintenance dates.
- `/home/{homeID}/people` contains household members and trusted professionals.
- `/home/{homeID}/documents` contains manuals, warranties, quotes, invoices, and receipts.
- `/home/{homeID}/payments` contains deposits, balances, payment history, and refunds.
- `/home/{homeID}/settings` contains home profile, permissions, privacy, and notification preferences.

### Professional Routes

- `/pro` is the daily work desk.
- `/pro/opportunities` contains eligible homeowner opportunities.
- `/pro/jobs` contains awarded and active work.
- `/pro/calendar` contains availability, travel blocks, and appointments.
- `/pro/clients` contains recurring homeowner relationships and service history.
- `/pro/estimates` contains drafts, sent estimates, revisions, and approvals.
- `/pro/payments` contains invoices, payouts, refunds, and tax records.
- `/pro/business` contains identity, credentials, services, coverage area, team, and notification settings.
- `/pros/{slug}` is the homeowner-facing professional profile.

## The Personalized Home Experience

### Home Identity

Every property receives a Home Passport containing:

- nickname and full address
- homeowner-supplied cover photo
- home type, approximate age, size, and occupancy
- rooms and outdoor areas
- major systems and appliances
- manuals, warranties, and serial numbers
- preferred access windows and carefully protected entry instructions
- household members and permissions
- trusted professionals
- full repair and maintenance history

If no cover photo exists, the interface uses the address, home nickname, and an elegant neutral architectural pattern. It never invents a fake home image.

### Home Concierge Dashboard

The first screen answers four questions:

1. What needs attention now?
2. Who is coming next?
3. What decision or payment is waiting?
4. What should be maintained soon?

The page structure is:

- personalized home header with home switcher
- one primary action based on current state
- `Needs attention` queue for quote approvals, schedule decisions, and payment actions
- `Coming up` timeline for visits and reminders
- `Home care` section for active repairs and preventive tasks
- `Your home team` section for preferred contractors and recent professionals
- `Home record` summary for documents, systems, completed work, and spend history

The interface does not lead with abstract KPI cards. Counts support decisions but do not replace the home narrative.

### Repair Intake

Repair creation becomes a guided, saveable flow:

1. Select home and room or system.
2. Describe what is happening in plain language.
3. Add photos, video, or documents.
4. Select urgency and safety indicators.
5. Choose access and scheduling preferences.
6. Choose request visibility:
   - preferred professional only
   - invite selected professionals
   - request qualified local quotes
7. Review exactly what a professional will see.
8. Submit.

Drafts stay private. Emergency language provides immediate safety guidance without pretending MyCasaPro is an emergency service.

### Repair Timeline

Every repair has one chronological record:

- request submitted
- professionals invited or interested
- questions and replies
- estimate versions
- homeowner approval or revision request
- deposit
- scheduled visit and arrival window
- work updates and completion photos
- change orders
- invoice and payment
- completion confirmation
- warranty and follow-up

## Professional Experience

### Professional Types

Onboarding supports:

- licensed contractor
- specialty licensed trade
- independent handyman
- property maintenance company
- crew member working under an organization

The product never presents `unlicensed` as a blanket negative label. It presents credential status in context:

- license verified
- license submitted and pending verification
- license required for this work
- license not required for this work category
- insurance verified
- identity verified

### Professional Profile

Required profile fields:

- public display name and legal business identity
- individual or organization type
- services and excluded work
- service area and travel radius
- license jurisdiction, class, identifier, and expiration when applicable
- insurance status and expiration when applicable
- years of experience
- minimum job size and pricing approach
- languages
- availability and emergency availability
- portfolio with real project photos
- response expectations

Trust metrics appear only after sufficient real activity. No profile receives fabricated ratings, completed-job counts, or response statistics.

### Daily Work Desk

The professional homepage prioritizes execution:

- today’s visits with route-aware times
- messages requiring response
- quotes needing completion or follow-up
- jobs blocked on homeowner decisions
- invoices ready to send
- qualified opportunities matching trade, geography, availability, and job preferences

Licensed businesses get team and dispatch controls. Solo handymen get a simpler mode with the same core records and fewer administrative surfaces.

## Matching and Privacy Model

### Request Visibility

Each request has one explicit mode:

- `private`: homeowner draft or record only
- `preferred_only`: visible to one selected professional
- `invite_only`: visible to selected professionals
- `qualified_marketplace`: visible only to professionals eligible for the work
- `awarded`: visible to the chosen professional organization
- `closed`: retained by participants as history

### Pre-Award Contractor View

A qualified professional may see:

- approximate neighborhood or distance band
- work category and room or system
- description approved for professional sharing
- urgency
- preferred timing
- homeowner-approved attachments
- property type details relevant to the work

They do not see:

- exact address
- access instructions
- household member information
- unrelated home documents
- unrelated repair history

### Opportunity Lifecycle

`available -> viewed -> interested | declined -> invited_to_quote -> quote_submitted -> awarded | lost | expired`

Submitting interest never creates a project. Awarding a quote creates the shared project and releases the exact service address to the selected professional.

### Preferred Professional Relationships

After successful work, a homeowner can add a professional to the home team. The relationship supports:

- one-tap private requests
- recurring maintenance
- service reminders
- property-specific notes
- past work history
- preferred scheduling windows

This creates the recurring-home model contractors want without forcing homeowners back into a marketplace for every issue.

## Money and Scope Transparency

The commercial record must support:

- versioned line-item estimates
- optional upgrade choices
- homeowner approval or revision request
- deposits
- milestone payments for larger jobs
- signed change orders before added work
- invoices linked to approved scope
- payment status and receipts
- tips only after completion
- refunds and adjustments with reason codes
- warranty terms and expiration

The platform should use a regulated payment provider rather than hold funds itself. Every money movement must be visible to the homeowner and professional with amount, status, date, purpose, and receipt.

## Data Model Additions

### Home Domain

- `home_profiles`
- `home_members`
- `home_spaces`
- `home_assets`
- `home_documents`
- `maintenance_plans`
- `maintenance_tasks`
- `home_professional_relationships`
- `home_access_profiles`

### Professional Domain

- `professional_profiles`
- `professional_services`
- `service_areas`
- `professional_credentials`
- `insurance_records`
- `availability_rules`
- `portfolio_items`
- `professional_team_members`

### Marketplace Domain

- `request_visibility`
- `request_invites`
- `opportunity_interests`
- `quote_requests`
- `quote_revisions`
- `job_awards`

Sensitive access instructions are encrypted separately and released only to authorized project participants at the appropriate lifecycle stage.

## Visual Direction

### Homeowner

- warm ivory canvas, dark ink, muted mineral colors, and one home-specific accent
- editorial typography and generous spacing
- real homeowner photography as atmosphere, never stock filler
- quiet transitions for state changes and timeline reveals
- concise language that sounds like a concierge, not property-management software
- fewer cards, stronger hierarchy, and one clear action per section

### Professional

- same brand family with denser layouts and stronger operational contrast
- fast scanning for status, time, location, value, and next action
- mobile controls sized for field use
- persistent access to schedule, messages, job scope, photos, and payment status
- separate `solo` and `team` complexity modes

## Build Order

### Phase 0: Correct the Current Trust Boundary

- remove exact addresses and unrestricted attachments from open contractor inbox responses
- replace `Accept into jobs` with `Express interest` and homeowner award
- add request visibility and invite state
- enforce field-level authorization in the API, not only the interface
- add authorization tests for every request state

Exit criteria: an unrelated contractor cannot retrieve a private request, exact address, attachment, or project record.

### Phase 1: Home Passport Foundation

- add the home profile, spaces, assets, documents, members, and home switcher
- change homeowner routes from account-centric to home-centric
- create personalized home onboarding
- create real empty states and owner-supplied home photography

Exit criteria: two homes under one account look and behave as distinct homes with separate records.

### Phase 2: Premium Homeowner Concierge

- rebuild the home dashboard around attention, schedule, maintenance, people, and records
- implement draft repair intake and visibility preview
- create repair detail and complete timeline
- add document organization and search

Exit criteria: a homeowner can understand the current state of the home and every repair without contacting support.

### Phase 3: Professional Identity and Eligibility

- build solo and business onboarding
- add service, geography, credential, insurance, portfolio, and availability records
- implement credential review states and expiration handling
- build professional public profiles with only real trust data

Exit criteria: the system can determine whether a professional is eligible to see or quote a request.

### Phase 4: Matching, Quotes, and Award

- implement preferred-only, invite-only, and qualified-marketplace flows
- build professional opportunities and interest responses
- build homeowner comparison of profiles and quotes
- award one professional and create the shared project
- release exact address only after authorization

Exit criteria: a homeowner controls who receives the job and every losing professional loses access after award.

### Phase 5: Shared Work and Payments

- complete appointments, arrival updates, shared messaging, estimates, change orders, invoices, payments, and receipts
- add completion approval and warranty records
- add preferred-professional relationships and recurring maintenance
- add email and SMS notifications with preference controls

Exit criteria: a real repair can run from intake through paid completion without side-channel paperwork.

### Phase 6: Production Hardening

- Postgres integration and migration tests
- durable object storage and backup/restore validation
- payment-provider sandbox and webhook replay tests
- accessibility and keyboard testing
- mobile device and poor-network testing
- image malware scanning and metadata stripping policy
- audit logs, rate limits, monitoring, and recovery runbooks
- account export and deletion flows

Exit criteria: launch checklist passes with no sample data, no unauthorized cross-account access, and deterministic recovery from failed uploads, payments, and notifications.

## Release Acceptance Matrix

| Actor | Must be able to do | Must never happen |
| --- | --- | --- |
| Homeowner | Create multiple distinct Home Passports | Records from one home bleed into another |
| Homeowner | Choose who sees each repair | A request becomes public by accident |
| Homeowner | Compare and award quotes | A contractor self-assigns work |
| Homeowner | Follow scope, schedule, money, and warranty | Payment or scope changes are unexplained |
| Licensed pro | Prove credentials and receive eligible work | Credential claims appear verified without review |
| Handyman | Receive work that fits legal and service limits | The interface treats all handyman work as untrustworthy |
| Contractor team | Dispatch and collaborate on awarded jobs | Crew sees unrelated homeowner records |
| Solo pro | Quote, schedule, invoice, and get paid quickly | Team-only complexity blocks field use |

## Immediate Engineering Slice

The next implementation slice is Phase 0 followed by the Home Passport skeleton. Do not begin another visual polish pass until request visibility, contractor interest, homeowner award, and field-level privacy are modeled correctly.
