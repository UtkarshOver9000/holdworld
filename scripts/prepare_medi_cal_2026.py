"""Build the static dashboard payload from the California DHCS 2026 CSV snapshot."""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "benchmarks" / "medi_cal_2026"
OUTPUT = ROOT / "site" / "data" / "medi_cal_2026.json"


def read_table(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    header_index = next(
        i for i, row in enumerate(rows) if row and row[0].strip() == "Reporting Period"
    )
    headers = [value.strip() for value in rows[header_index]]
    return [
        dict(zip(headers, row))
        for row in rows[header_index + 1 :]
        if row and any(value.strip() for value in row)
    ]


def month_key(value: str) -> tuple[str, str]:
    value = value.strip()
    for pattern in ("%b-%y", "%B %Y"):
        try:
            month = datetime.strptime(value, pattern)
            return month.strftime("%Y-%m"), month.strftime("%b %Y")
        except ValueError:
            pass
    raise ValueError(f"Unrecognized reporting period: {value!r}")


def number(value: str | None) -> int | None:
    if not value or not value.strip():
        return None
    cleaned = re.sub(r"[^0-9.-]", "", value)
    return int(float(cleaned)) if cleaned else None


def seconds(value: str | None) -> int | None:
    if not value or not value.strip():
        return None
    hours, minutes, secs = (int(part) for part in value.strip().split(":"))
    return hours * 3600 + minutes * 60 + secs


def main() -> None:
    counties: dict[str, dict[str, dict]] = {}

    for row in read_table(SOURCE / "total_call_volume.csv"):
        key, label = month_key(row["Reporting Period"])
        county = row["County Name"].strip()
        record = counties.setdefault(key, {}).setdefault(county, {"county": county})
        record.update(
            calls_working_hours=number(row.get("Number of Calls Received During Working Hours")),
            calls_after_hours=number(row.get("Number of Calls Received After Working Hours")),
            total_calls=number(row.get("Total Number of Calls Received")),
        )

    for row in read_table(SOURCE / "average_call_wait_time.csv"):
        key, label = month_key(row["Reporting Period"])
        county = row["County Name"].strip()
        record = counties.setdefault(key, {}).setdefault(county, {"county": county})
        record["average_wait_seconds"] = seconds(row.get("Average Wait Time All Languages"))
        record["language_wait_seconds"] = {
            re.sub(r"^Average Wait Time ", "", name): seconds(value)
            for name, value in row.items()
            if name.startswith("Average Wait Time ")
            and name != "Average Wait Time All Languages"
            and seconds(value) is not None
        }

    for row in read_table(SOURCE / "average_call_abandonment_rate.csv"):
        key, label = month_key(row["Reporting Period"])
        county = row["County Name"].strip()
        record = counties.setdefault(key, {}).setdefault(county, {"county": county})
        raw_rate = row.get("Average Abandonment Rate", "").strip()
        try:
            record["abandonment_rate"] = float(raw_rate) if raw_rate else None
        except ValueError:
            record["abandonment_rate"] = None

    months = []
    for key in sorted(counties):
        records = list(counties[key].values())
        label = datetime.strptime(key, "%Y-%m").strftime("%b %Y")
        wait_values = [r["average_wait_seconds"] for r in records if r.get("average_wait_seconds") is not None]
        abandon_values = [r["abandonment_rate"] for r in records if r.get("abandonment_rate") is not None]
        months.append(
            {
                "month": key,
                "label": label,
                "total_calls": sum(r.get("total_calls") or 0 for r in records),
                "working_hours_calls": sum(r.get("calls_working_hours") or 0 for r in records),
                "after_hours_calls": sum(r.get("calls_after_hours") or 0 for r in records),
                "counties_with_volume": sum(r.get("total_calls") is not None for r in records),
                "county_median_wait_seconds": round(median(wait_values)) if wait_values else None,
                "counties_with_wait": len(wait_values),
                "county_median_abandonment_rate": median(abandon_values) if abandon_values else None,
                "counties_with_abandonment": len(abandon_values),
                "counties": sorted(
                    records,
                    key=lambda r: (r.get("average_wait_seconds") is None, -(r.get("average_wait_seconds") or 0), r["county"]),
                ),
            }
        )

    payload = {
        "source": {
            "title": "County Medi-Cal Call Center Data",
            "publisher": "California Department of Health Care Services",
            "dataset_url": "https://publish.data.ca.gov/dataset/county-medi-cal-call-center-data",
            "license": "Creative Commons Attribution (CC BY)",
            "coverage": "January–June 2026",
            "data_updated": "2026-09-30",
            "metadata_updated": "2026-10-08",
            "snapshot_retrieved": "2026-10-23",
        },
        "months": months,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} ({len(months)} months, {sum(len(m['counties']) for m in months)} county-month rows)")


if __name__ == "__main__":
    main()
