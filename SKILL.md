---
name: weekly-time-tracking
description: Reconstruct Aaron's time tracking for any date range from Outlook calendar, Zoom history, and the Time Tracking calendar, then generate an .ics file of properly named events for import. Supports today, yesterday, this week, last week, week ending X, multi-week spans like last two weeks or a full month, or any explicit date range. Use this skill whenever the user mentions time tracking, timesheets, logging hours, booking time, time entry, a time breakdown by customer or bucket, or filling out time for a day or week. Also trigger on phrases like "track my time", "log my hours", "do my timesheet", "time for today", "time for last week", "track time for week ending 7/3", or "run my time process".
---

# Weekly Time Tracking

Reconstruct time entries for a target date range, allocate every hour to a customer or internal bucket, fill each covered workday to a minimum of 8.0 hours, and deliver an .ics file the user imports into the "Time Tracking" Outlook calendar. The user's existing sync then flows those events into the Master Time Tracking workbook, where formulas categorize and roll up automatically. The calendar is the source of truth; never write rows into the workbook's Data sheet directly, since the sync would duplicate them.

## Prerequisites

**Google Drive connector required.** Before doing anything else, verify the Google Drive connector is available by checking whether Drive tools are present in the tool list. If not, stop immediately and tell the user:

> "This skill requires the Google Drive connector. Please enable it under Tools in the Claude sidebar, then re-run the skill."

Do not proceed until Drive is confirmed available.

## Config file

The skill stores all user-specific configuration in a JSON file in Google Drive:

- **Location**: `Claude Outputs/Configs/Time Tracking Config.json`
- **File ID in memory**: stored as `time_tracking_config_id`

### Loading the config

On every run, after confirming Drive is available:

1. Check memory for `time_tracking_config_id`. If present, fetch the file with `Google Drive:download_file_content` and parse the JSON. If the fetch fails, fall through to the setup flow.
2. If no ID in memory, search Drive for `title = 'Time Tracking Config.json'` under the `Claude Outputs/Configs/` folder. If found, cache the ID in memory and load it.
3. If not found anywhere, run the **First-run setup** flow below.

### First-run setup

1. Locate or create the `Claude Outputs` folder in Drive root. Then locate or create the `Configs` subfolder within it.
2. Build the config JSON with all fields set to their defaults.
3. Upload the file as `Time Tracking Config.json` to the `Configs` folder using `Google Drive:create_file` with `contentMimeType: application/json` and `disableConversionToGoogleType: true`.
4. Store the returned file ID in memory: `memory_user_edits(command="add", control="time_tracking_config_id: [ID]")`.
5. Confirm to the user: share the Drive URL and note that all values are defaulted and can be adjusted by asking the skill to update them.

### Updating the config

Any time a config value changes during a run (user corrects a value, a new account pattern is added, etc.):

1. Generate a CDT timestamp: `YYYYMMDD-HHMMSS`.
2. Copy the current config file using `Google Drive:copy_file`:
   - `fileId`: current `time_tracking_config_id`
   - `title`: `Time Tracking Config-[timestamp].json`
   - `parentId`: same folder as the original (get via `Google Drive:get_file_metadata` first)
3. Upload the updated JSON as a new file named `Time Tracking Config.json` to the same folder.
4. Update `time_tracking_config_id` in memory with the new file ID.
5. Tell the user the config was updated and share both the new file URL and the backup URL.

### Config schema

```json
{
  "time_tracking_calendar_name": "Time Tracking",
  "daily_minimum_hours": 8.0,
  "personal_calendar_exclusion_category": "z-Personal",
  "customer_short_names": {},
  "notes": ""
}
```

Field definitions:

| Field | Default | Required | Description |
|---|---|---|---|
| `time_tracking_calendar_name` | `"Time Tracking"` | No | Name of the Outlook calendar used as the target for .ics import. |
| `daily_minimum_hours` | `8.0` | No | Minimum hours required per complete workday. |
| `personal_calendar_exclusion_category` | `"z-Personal"` | No | Outlook calendar category to skip when gathering activity. |
| `customer_short_names` | `{}` | No | Map of full account name to short token used in event names, e.g. `{"Bank of America": "Bank"}`. Populated over time as accounts are categorized. |
| `notes` | `""` | No | Free-text notes field; ignored by the skill. |

The `customer_short_names` map is the runtime equivalent of what was previously hardcoded in `references/category-mappings.md`. When the skill encounters an account name from the Asana portfolio and needs to pick or confirm a short token for calendar event naming, it checks this map first. If no entry exists, it prompts the user to confirm the token and then writes it back to the config via the update flow above.

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

The daily minimum applies to each complete workday in the range (from `daily_minimum_hours` in config, default 8.0). For "today" or a "this week" range that includes the current in-progress day, ask whether to fill the current day to the minimum or record only confirmed activity (pass --daily-min 0 to the script for that case).

### 2. Load config and resolve account status

Load the config file as described in the Config file section above. Extract settings for use in subsequent steps.

Then fetch live subscriber status from the Enterprise Success Customers portfolio in Asana. Use `get_items_for_portfolio` with `opt_fields=name,custom_fields` and read the `Non-Subscriber?` custom field on each item. The portfolio GID and field GID are stored in memory; do not put them in the config file.

Use the `Non-Subscriber?` field solely to determine prefix: `"Yes"` → `NS :: [Customer]`, `"No"` → `C :: [Customer]`. Account assignment comes from the user's own calendar activity, not portfolio membership.

For each account encountered, look up its short token in `customer_short_names` from the config. If no entry exists for that account, prompt the user to confirm the token, then write it back to the config via the update flow.

If a customer name appears in calendar or Zoom activity but you cannot determine its subscriber status from the portfolio, stop and ask the user: "I found activity for [Customer] but could not confirm its subscriber status. Is this account a subscriber or non-subscriber?" Do not guess.

### 3. Check what is already logged

Search the calendar named in `time_tracking_calendar_name` (from config, default "Time Tracking") for the target range. These entries are already in the system. Never regenerate them; count their hours toward daily totals using the workbook's rounding (minutes / 60, ceiling to 0.25).

### 4. Gather activity

Pull from all available sources:

- Main Outlook calendar for the range. Exclude events with the category matching `personal_calendar_exclusion_category` (from config) and obviously personal items (medication reminders, workouts, family blocks).
- Zoom meeting history for the same range. Zoom gives actual attendance and durations, which beat scheduled times. Solo meetings sourced from "my_notes" are heads-down working sessions; their topics usually reveal the customer.
- If gaps remain, check recent Slack activity or Asana tasks for evidence of what was worked on.

Tentative calendar events with no Zoom evidence of attendance do not count.

### 5. Categorize and round

Map each activity to exactly one bucket using `references/category-mappings.md` for pattern syntax and the config's `customer_short_names` for account tokens. There are three bucket types:

- `C :: [Token]` for ES subscriber accounts
- `NS :: [Token]` for non-subscriber accounts
- `Admin :: [bucket]` for internal overhead, mapped to the Internal Overhead [Enterprise-Success] phase in Precursive PSA

Subscriber vs. non-subscriber status for each account comes from the live Asana portfolio lookup in step 2.

Event durations must be multiples of 30 minutes so hours land in 0.5 increments. Use actual durations where Zoom provides them, rounded to the nearest 0.5 hour; drop fragments under 15 minutes or fold them into an adjacent related entry.

### 6. Confirm the gap allocation

Sum the confirmed hours per day and present a concise breakdown. Each complete workday must reach the daily minimum from config. Ask the user, with the interactive question interface, where unscheduled heads-down time went and which internal bucket applies if unclear. Default unclear internal work to Admin :: General. Distribute the fill so each day reaches exactly the daily minimum unless the user says otherwise.

### 7. Generate the .ics

Write an entries list and run `scripts/build_ics.py`. The script validates that every name matches exactly one pattern, every duration is a 30-minute multiple, and every day (new entries plus already-logged hours passed via --logged) reaches the daily minimum. Fix validation failures rather than overriding them. Schedule new events at plausible times that do not overlap the already-logged entries; only the date affects the rollup, but a clean calendar matters.

### 8. Deliver

Present the .ics with a short summary: hours per ES customer bucket (C ::), hours per non-subscriber bucket (NS ::), hours per internal bucket (Admin ::), range total, and any assumptions made. Name the file time-tracking-YYYY-MM-DD.ics using the range start date, or time-tracking-YYYY-MM-DD_to_YYYY-MM-DD.ics for multi-week ranges. Include the import instructions: in Outlook on the web, Add calendar, Upload from file, select the .ics, choose the Time Tracking calendar. Do not update the workbook; the user's sync handles that after import.

## Style

Lead with the answer. Keep the breakdown in prose or a compact table, not nested bullets. State assumptions briefly and proceed; ask only questions that change the allocation.
