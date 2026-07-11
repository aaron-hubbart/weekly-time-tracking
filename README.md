# weekly-time-tracking

A Claude skill that reconstructs weekly time entries from Outlook calendar and Zoom history, categorizes them by customer or internal bucket, and generates an `.ics` file for import into the Time Tracking Outlook calendar.

## Structure

```
SKILL.md                        Skill definition and process instructions
references/
  category-mappings.md          Pattern syntax and internal bucket definitions
scripts/
  build_ics.py                  Validates entries and generates the .ics file
  patterns.json                 Generated at runtime from the workbook Config sheet (gitignored)
```

## Usage

The skill is triggered by Claude when you ask to track, log, or fill your time. It pulls from Outlook calendar, Zoom history, and Slack/Asana for context, then walks through gap allocation and produces a validated `.ics` file.

See `SKILL.md` for the full process.

## Runtime files

`patterns.json` is generated at runtime from the workbook's Config sheet and is not committed. It maps customer tokens and internal bucket names to category patterns. Do not commit this file; it may contain customer names.

## Security note

This repo contains no credentials, API keys, Drive file IDs, Asana GIDs, or customer-identifying information. All such values are stored in Claude's memory and resolved at runtime.
