# Category Mappings

The workbook categorizes an event by searching its name for a pattern (case-insensitive substring). Every generated event name must contain exactly one pattern; descriptive suffixes after the pattern are fine ("C :: Bank - triage session" matches C :: Bank). A name matching two patterns breaks the workbook's FILTER formula, so never combine patterns in one name.

## Customer patterns

ES subscriber accounts use the format `C :: [Customer]`.
Non-subscriber accounts use the format `NS :: [Customer]`.

Subscriber status for each account is determined at runtime from the Enterprise Success Customers portfolio in Asana (see step 2 of the skill). This file does not encode that status.

Short-name tokens used in event names should match what the workbook's Config sheet expects. Common conventions:

- Multi-word names are shortened to a single word or acronym (e.g., "JPMC", "EY")
- Use the token that appears in the Config sheet; if uncertain, check there first
- Descriptive suffixes after the token are fine and do not affect matching

## Internal patterns

These map to the Internal Overhead [Enterprise-Success] phase in Precursive PSA.

| Pattern | PSA bucket |
|---|---|
| Admin :: 1:1 | 1-1s and PR Meetings |
| Admin :: Company Meeting | Company Meetings |
| Admin :: General | General Overhead (Email + Slack) |
| Admin :: Travel | Internal Travel |
| Admin :: Other Meeting | Other Meetings |
| Admin :: Team Meeting | Team Meetings |
| Admin :: 360 | 360 Feedback |
| Admin :: Recruiting | Interviews and Recruiting Support |
| Admin :: Ops | Administration & Operations |
| Admin :: Education | Education Team |
| Admin :: NA Event | NA Team Event |
| Admin :: DACH Offsite | DACH EMEA-S Offsite |
| Admin :: ILT | ILT Management & User/Partner Support |
| Admin :: Comms Training | Internal Meetings, Communication & Training |
| Admin :: People | People & Team Management |
| Admin :: Onboarding | TAM Onboarding (use during onboarding ramp only) |
| Admin :: PTO | Private Absence |
| Admin :: OOO | Private Absence |
| Admin :: Holiday | Private Absence |

## Categorization heuristics

Customer sessions, triage calls, and customer-topic working sessions map to `C :: [Customer]` for ES subscribers or `NS :: [Customer]` for non-subscribers. Subscriber status comes from the live Asana portfolio lookup in step 2, not from this file.

Admin :: 1:1 covers 1:1s, skip levels, and PR meetings. Suffix the person's name: "Admin :: 1:1 [Name]".

Admin :: General is the default catch-all for email/Slack follow-up blocks, Asana updates, SR reviews, ad-hoc colleague syncs, CS toolkit PR work, internal tooling, and any unscheduled fill the user attributes to general overhead.

Admin :: Team Meeting covers team meetings and bi-weeklies.

Admin :: Other Meeting covers internal syncs that do not clearly fit another bucket (tiger team calls, cross-functional ad-hoc meetings, and so on).

Admin :: Comms Training covers required compliance training, enablement sessions, AI office hours, and professional development.

Admin :: Ops covers administrative and operational work not covered by another bucket (expense reports, system access, tooling setup).

Admin :: People covers people management activities, performance conversations, and mentoring.

Admin :: Recruiting covers interview panels, candidate debriefs, and sourcing support.

## Rounding

The workbook computes hours as CEILING(minutes / 60, 0.25). Keep all generated durations in 30-minute multiples so entries land on 0.5-hour increments. Already-logged entries may be 25 or 50 minutes; they round to 0.5 and 1.0 respectively and count as such toward daily totals.

## Exclusions

Skip anything with the z-Personal category, medication reminders, workouts, family time, and declined or tentative meetings without Zoom attendance evidence.
