# MyCasaPro Visual System

## Direction

MyCasaPro should feel like a private residential register for homeowners and a composed work ledger for professionals. It should not resemble a generic venture-backed analytics dashboard, an apartment template, or an AI-generated landing page.

The homeowner experience is editorial, calm, warm, and property-specific. The professional experience shares the same materials and typography but uses denser information and more direct operational language.

## Research Conclusions

- BuildingLink prioritizes property-specific information and resident tasks on the home screen rather than generic product analytics: https://help-resident.buildinglink.com/en/support/solutions/articles/42000106541
- Livly combines maintenance, service booking, payments, and building context into one resident experience: https://www.livly.io/for-residents
- Jobber prioritizes schedules, job details, photos, documents, quotes, and payment actions for field professionals: https://www.getjobber.com/industries/general-contracting/
- Luxury concierge products earn trust through discretion, continuity, and personal context. Visual decoration cannot substitute for those qualities.

## Anti-Slop Rules

Do not add:

- invented homeowner records, contractor ratings, jobs, metrics, or addresses
- stock or generated home photography presented as the user’s property
- gradient blobs, blueprint grids, floating notification cards, or decorative dashboard mockups
- a grid of rounded cards when simple sections or rows communicate the hierarchy
- a bright blue default SaaS palette
- oversized metric tiles without an immediate decision attached
- pill-shaped labels for ordinary metadata
- excessive shadows, glass effects, or border radii
- generic claims such as `everything in one place` without specific product meaning
- animations that do not explain a transition or preserve context
- decorative initials standing in for a home image

## Identity

### Typography

- Editorial display: Newsreader
- Interface and forms: Instrument Sans
- Headings use sentence case and restrained weight.
- Uppercase labels are reserved for short wayfinding labels, not paragraphs or primary navigation.

### Color

- Limestone canvas: `#f1eee7`
- Warm paper surface: `#fbfaf6`
- Carbon ink: `#24251f`
- Juniper action color: `#365747`
- Oxide urgency color: `#9c513f`
- Brass warning color: `#a7743e`

Color must convey state or identity. It is not filler.

### Shape

- Default corners are square or two pixels.
- Circles are reserved for people, completion marks, or count indicators.
- Section boundaries use spacing and rules before containers.
- Shadows are reserved for overlays such as dialogs.

## Homeowner Surfaces

- The property name is the page title after onboarding.
- The full address appears once as context, not repeatedly in decorative cards.
- `Needs attention` appears before general summaries.
- Empty states remain visually quiet and offer one useful next action.
- The home record uses real property information and real uploaded imagery only.
- When a home photograph is unavailable, typography and whitespace carry the page.
- Repairs appear as chronological records, not anonymous tickets.

## Professional Surfaces

- The opening view answers what is happening today, what needs a response, and what can be invoiced.
- Counts appear in a compact ledger rather than colorful metric cards.
- Opportunity and job rows emphasize time, service type, approximate location, scope, and next action.
- On mobile, schedule, job details, photos, messages, and payment actions remain within one thumb-reachable path.
- Solo handymen receive the same quality of interface as licensed teams without unnecessary dispatch controls.

## Component Rules

- Use a card only when the content is a discrete selectable object.
- Use a row for activity, repair, appointment, invoice, or message lists.
- Use a section rule for page-level grouping.
- Use status text with a restrained underline before adding a filled badge.
- Use one primary action per page region.
- Modals are for focused creation or confirmation, not general navigation.
- Never hide meaningful status behind icon-only controls.

## Current Removal Pass

The July 2026 removal pass replaced:

- the blue gradient monogram with a typographic wordmark
- the dark generic SaaS sidebar with a warm residential navigation rail
- the blueprint landing illustration and fake repair cards with an editorial home register
- oversized authentication marketing with a restrained two-column access screen
- rounded shadow cards with ruled sections and records
- bright blue accents with a juniper, limestone, oxide, and brass system
- decorative property initials with actual property text
- pill-heavy metadata with quieter state labels
- metric tiles with a compact professional operations ledger

## Review Checklist

Before merging a visual change, verify:

1. Every displayed record can be traced to real user data.
2. The screen still makes sense with zero records.
3. Removing a container, icon, color, or label would not improve clarity.
4. Homeowner and professional hierarchy remain distinct.
5. Desktop, tablet, and phone layouts preserve the primary action.
6. Keyboard focus, contrast, labels, and reduced motion remain usable.
7. The screen would still feel intentional without gradients, shadows, or illustrations.
