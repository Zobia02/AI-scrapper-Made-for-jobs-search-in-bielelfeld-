from io import BytesIO

import pandas as pd

COLUMNS = ["id", "title", "company", "location", "job_type", "workplace", "salary", "paid",
           "language", "score", "skills", "posted_at", "date_label", "first_seen", "last_verified",
           "source", "source_url", "apply_url", "all_source_urls", "potentially_expired", "collection", "application_status"]


def safe_cell(value):
    # Prevent spreadsheet formula execution in third-party listing fields and user notes.
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value


def jobs_frame(jobs):
    rows = []
    for job in jobs:
        row = {k: job.get(k) for k in COLUMNS}
        row["skills"] = ", ".join(job.get("skills", []))
        row["score"] = job.get("match", {}).get("score")
        row["all_source_urls"] = " | ".join(x["url"] for x in job.get("source_links", []))
        rows.append(row)
    return pd.DataFrame(rows, columns=COLUMNS)


def csv_bytes(frame):
    return frame.map(safe_cell).to_csv(index=False).encode("utf-8-sig")


def excel_bytes(frame):
    stream = BytesIO()
    with pd.ExcelWriter(stream, engine="openpyxl") as writer:
        frame.map(safe_cell).to_excel(writer, sheet_name="CareerScout", index=False)
        sheet = writer.sheets["CareerScout"]
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        for column in sheet.columns:
            sheet.column_dimensions[column[0].column_letter].width = min(60, max(16, len(str(column[0].value)) + 3))
    return stream.getvalue()


def applications_frame(applications, jobs):
    lookup = {j["id"]: j for j in jobs}
    rows = []
    for application in applications:
        job = lookup.get(application["job_id"], {})
        rows.append({**application, **{k: job.get(k, "") for k in ["title", "company", "source_url", "apply_url"]}})
    return pd.DataFrame(rows)
