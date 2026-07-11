---
name: weekly-time-tracking
description: Reconstruct Aaron's time tracking for any date range from Outlook calendar, Zoom history, and the Time Tracking calendar, then generate an .ics file of properly named events for import. Supports today, yesterday, this week, last week, week ending X, multi-week spans like last two weeks or a full month, or any explicit date range. Use this skill whenever the user mentions time tracking, timesheets, logging hours, booking time, time entry, a time breakdown by customer or bucket, or filling out time for a day or week. Also trigger on phrases like "track my time", "log my hours", "do my timesheet", "time for today", "time for last week", "track time for week ending 7/3", "run my time process", or any request to reconcile hours against the Master Time Tracking workbook.
---

# Weekly Time Tracking

Reconstruct time entries for a target date range, allocate every hour to a customer or internal bucket, fill each covered workday to a minimum of 8.0 hours, and deliver an .ics file the user imports into the "Time Tracking" Outlook calendar. The user's existing sync then flows those events into the Master Time Tracking workbook, where formulas categorize and roll up automatically. The calendar is the source of truth; never write rows into the workbook's Data sheet directly, since the sync would duplicate them.

## Process

### 1. Scope the date range

Resolve the range from the user's request. Supported presets:

| Phrase | Range |
|---|---|
| today | current date only |
| yesterday | previous date only (if that lands on a weekend, confirm before proceeding) |
| this week | Monday of the current week through today |
| last week | Monday through Friday of the previous week |
| week ending X | Monday through Friday of the week whose Friday is X (if X is not a Friday, treat X as the last day and go back to that week's Monday) |

Multi-week ranges are supported: "last two weeks", "the last 3 weeks", "month of June", or any explicit span ("6/8 through 6/26"). Resolve these to consecutive Mon-Fri workweeks. Explicit ranges ("6/22 through 6/24") work too. If the user gives no range at all, ask with the interactive question interface, offering today, yesterday, this week, and last week as options. Confirm the resolved dates in the first response. Weekends are excluded unless the user explicitly includes them.

For ranges longer than one week, work week by week: gather and categorize the whole range up front, but present each week's confirmed breakdown separately and ask the gap-allocation question per week, since unscheduled time rarely went to the same place every week. Produce one .ics covering the full range, and give per-week and grand totals in the summary.

The 8.0-hour daily minimum applies to each complete workday in the range. For "today" or a "this week" range that includes the current in-progress day, ask whether to fill the current day to 8.0 or record only confirmed activity (pass --daily-min 0 to the script for that case).

### 2. Read the config and resolve account status

Fetch the master workbook from Google Drive (search for "Master Time Tracking.xlsx" in the Time Tracking folder). Read the Config sheet to get the current customer list and name patterns. If the Drive fetch fails, use `references/category-mappings.md` as the fallback mapping source.

Then fetch live subscriber status from the Enterprise Success Customers portfolio in Asana. Use `get_items_for_portfolio` with `opt_fields=name,custom_fields` and read the `Non-Subscriber?` custom field on each item. The portfolio GID and field GID are stored in your memory; do not hardcode them here.

Use the `Non-Subscriber?` field solely to determine prefix: `"Yes"` → `NS :: [Customer]`, `"No"` → `C :: [Customer]`. Do not use the portfolio to determine which accounts are yours; account assignment comes from the user's own customer list and calendar activity, not from portfolio membership.

If a customer name appears in calendar or Zoom activity but you cannot determine its subscriber status from the portfolio, stop and ask the user: "I found activity for [Customer] but could not confirm its subscriber status. Is this account a subscriber or non-subscriber?" Do not guess.

Use the live portfolio data as the source of truth for subscriber status. Do not rely on `references/category-mappings.md` for that; the mappings file covers pattern syntax only.

### 3. Check what is already logged

Search the "Time Tracking" calendar (calendarName parameter on the Outlook calendar search) for the target range. These entries are already in the system. Never regenerate them; count their hours toward daily totals using the workbook's rounding (minutes / 60, ceiling to 0.25).

### 4. Gather activity

Pull from all available sources:

- Main Outlook calendar for the range. Exclude events with the z-Personal category and obviously personal items (medication reminders, workouts, family blocks).
- Zoom meeting history for the same range. Zoom gives actual attendance and durations, which beat scheduled times. Solo meetings sourced from "my_notes" are heads-down working sessions; their topics usually reveal the customer.
- If gaps remain, check recent Slack activity or Asana tasks for evidence of what was worked on.

Tentative calendar events with no Zoom evidence of attendance do not count.

### 5. Categorize and round

Map each activity to exactly one bucket using `references/category-mappings.md`. There are three bucket types:

- `C :: [Customer]` for ES subscriber accounts
- `NS :: [Customer]` for non-subscriber accounts
- `Admin :: [bucket]` for internal overhead, mapped to the Internal Overhead [Enterprise-Success] phase in Precursive PSA

Subscriber vs. non-subscriber status for each account comes from the live Asana portfolio lookup in step 2.

Event durations must be multiples of 30 minutes so hours land in 0.5 increments. Use actual durations where Zoom provides them, rounded to the nearest 0.5 hour; drop fragments under 15 minutes or fold them into an adjacent related entry.

### 6. Confirm the gap allocation

Sum the confirmed hours per day and present a concise breakdown. Each complete workday must reach at least 8.0 hours (40.0 for a full Mon-Fri week). Ask the user, with the interactive question interface, where unscheduled heads-down time went (customer work, internal tooling, toolkit PRs, and so on) and which internal bucket applies if unclear. Default unclear internal work to Admin :: General. Distribute the fill so each day reaches exactly 8.0 unless the user says otherwise.

### 7. Generate the .ics

Write an entries list and run `scripts/build_ics.py`. The script validates that every name matches exactly one pattern, every duration is a 30-minute multiple, and every day (new entries plus already-logged hours passed via --logged) reaches the daily minimum. Fix validation failures rather than overriding them. Schedule new events at plausible times that do not overlap the already-logged entries; only the date affects the rollup, but a clean calendar matters.

### 8. Deliver

Present the .ics with a short summary: hours per ES customer bucket (C ::), hours per non-subscriber bucket (NS ::), hours per internal bucket (Admin ::), range total, and any assumptions made. Name the file time-tracking-YYYY-MM-DD.ics using the range start date, or time-tracking-YYYY-MM-DD_to_YYYY-MM-DD.ics for multi-week ranges. Include the import instructions: in Outlook on the web, Add calendar, Upload from file, select the .ics, choose the Time Tracking calendar. Do not update the workbook; the user's sync handles that after import.

## Style

Lead with the answer. Keep the breakdown in prose or a compact table, not nested bullets. State assumptions briefly and proceed; ask only questions that change the allocation.
