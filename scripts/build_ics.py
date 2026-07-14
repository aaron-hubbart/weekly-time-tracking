#!/usr/bin/env python3
"""Build a validated .ics file of Time Tracking calendar events.

Usage:
    python build_ics.py entries.json output.ics [--logged logged.json] [--daily-min 8.0]
                        [--config customers.json]

entries.json: list of [name, "YYYY-MM-DD HH:MM", minutes] for NEW events (times in UTC).
logged.json (optional): list of ["YYYY-MM-DD", minutes] for events already in the
Time Tracking calendar, counted toward daily totals but not written to the .ics.
customers.json (optional): list of customer name strings read from the workbook Config sheet.
  If omitted, falls back to DEFAULT_CUSTOMERS.

Validation (hard failures):
  - every name matches exactly one category pattern
  - every new duration is a multiple of 30 minutes
  - every weekday covered reaches the daily minimum (default 8.0 hours)
Prints a per-day, per-bucket summary on success.
"""
import json
import math
import sys
import datetime
from collections import defaultdict

# Fallback only — prefer passing --config sourced from the workbook Config sheet.
DEFAULT_CUSTOMERS = ["Bank", "EY", "First American", "JPMC", "Optum", "Toyota", "UPS", "Wells"]

# Aliases: additional patterns that map to a canonical customer name.
# Key = pattern substring (lowercase), value = canonical customer name.
CUSTOMER_ALIASES = {
    "c :: first am": "First American",
    "c::first am": "First American",
}

INTERNAL_PATTERNS = [
    ("admin :: onboarding", "TAM Onboarding"), ("admin::onboarding", "TAM Onboarding"),
    ("training :: onboarding", "TAM Onboarding"), ("training::onboarding", "TAM Onboarding"),
    ("admin :: training", "TAM Enablement"), ("admin::training", "TAM Enablement"),
    ("admin :: team meeting", "Team Meetings"), ("admin::team meeting", "Team Meetings"),
    ("admin :: 1:1", "1:1"), ("admin::1:1", "1:1"),
    ("admin :: kickoff", "Kickoff"), ("admin::kickoff", "Kickoff"),
    ("admin :: general", "Overhead"), ("admin::general", "Overhead"),
    ("admin :: travel", "Internal Travel"), ("admin::travel", "Internal Travel"),
    ("admin :: pto", "Private Absence"), ("admin::pto", "Private Absence"),
    ("admin :: ooo", "Private Absence"), ("admin::ooo", "Private Absence"),
    ("admin :: holiday", "Private Absence"), ("admin::holiday", "Private Absence"),
]


def build_patterns(customers):
    """Build the full pattern list from a customer name list."""
    patterns = []
    for c in customers:
        patterns.append((f"c :: {c.lower()}", c))
        patterns.append((f"c::{c.lower()}", c))
    for pattern, bucket in CUSTOMER_ALIASES.items():
        patterns.append((pattern, bucket))
    patterns.extend(INTERNAL_PATTERNS)
    return patterns


def categorize(name, patterns):
    return {b for p, b in patterns if p in name.lower()}


def hours(mins):
    return math.ceil((mins / 60) / 0.25) * 0.25


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        sys.exit(__doc__)
    entries = json.load(open(args[0]))
    out_path = args[1]
    logged = []
    daily_min = 8.0
    customers = list(DEFAULT_CUSTOMERS)
    if "--logged" in args:
        logged = json.load(open(args[args.index("--logged") + 1]))
    if "--daily-min" in args:
        daily_min = float(args[args.index("--daily-min") + 1])
    if "--config" in args:
        customers = json.load(open(args[args.index("--config") + 1]))
        print(f"Loaded {len(customers)} customers from config: {', '.join(customers)}")
    else:
        print(f"No --config supplied; using default customer list: {', '.join(customers)}")
    patterns = build_patterns(customers)

    errors = []
    daily = defaultdict(lambda: defaultdict(float))
    for name, start, mins in entries:
        buckets = categorize(name, patterns)
        if len(buckets) != 1:
            errors.append(f"'{name}': matches {len(buckets)} patterns ({buckets or 'none'})")
            continue
        if mins % 30 != 0:
            errors.append(f"'{name}': {mins} minutes is not a 30-minute multiple")
            continue
        day = start[:10]
        daily[day][buckets.pop()] += hours(mins)
    for day, mins in logged:
        daily[day]["(already logged)"] += hours(mins)

    for day in sorted(daily):
        total = sum(daily[day].values())
        if total < daily_min:
            errors.append(f"{day}: {total} hours is below the {daily_min} minimum")

    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print("  -", e)
        sys.exit(1)

    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0",
             "PRODID:-//weekly-time-tracking//EN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH"]
    for i, (name, start, mins) in enumerate(entries):
        dt = datetime.datetime.strptime(start, "%Y-%m-%d %H:%M")
        end = dt + datetime.timedelta(minutes=mins)
        lines += ["BEGIN:VEVENT",
                  f"UID:tt-{dt.strftime('%Y%m%d')}-{i+1:02d}-{stamp}@weekly-time-tracking",
                  f"DTSTAMP:{stamp}",
                  f"DTSTART:{dt.strftime('%Y%m%dT%H%M%SZ')}",
                  f"DTEND:{end.strftime('%Y%m%dT%H%M%SZ')}",
                  f"SUMMARY:{name}",
                  "END:VEVENT"]
    lines.append("END:VCALENDAR")
    with open(out_path, "w") as f:
        f.write("\r\n".join(lines) + "\r\n")

    week_total = 0.0
    bucket_totals = defaultdict(float)
    print(f"Wrote {len(entries)} events to {out_path}")
    for day in sorted(daily):
        total = sum(daily[day].values())
        week_total += total
        detail = ", ".join(f"{b} {v}" for b, v in sorted(daily[day].items()))
        print(f"  {day}: {total} h ({detail})")
        for b, v in daily[day].items():
            bucket_totals[b] += v
    print(f"Week total: {week_total} h")
    for b, v in sorted(bucket_totals.items()):
        print(f"  {b}: {v} h")


if __name__ == "__main__":
    main()
