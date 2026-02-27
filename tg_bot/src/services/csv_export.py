import csv
import io
from typing import List
from src.utils.logger import logger


def export_members_to_csv(members: List[dict]) -> io.BytesIO:
    """Export members list to CSV bytes buffer."""
    logger.info(f"Exporting {len(members)} members to CSV")
    output = io.StringIO()
    fieldnames = [
        "id", "telegram_id", "full_name", "partner_name",
        "phone", "email",
        "attendance_day1", "attendance_day2",
        "drink_pref", "wishes", "created_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for m in members:
        writer.writerow(dict(m))

    bytes_buf = io.BytesIO(output.getvalue().encode("utf-8-sig"))
    bytes_buf.name = "members.csv"
    return bytes_buf


def export_drinks_stats_to_csv(rows: List[dict]) -> io.BytesIO:
    """Export drink preferences statistics to CSV."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["drink", "count"], extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({"drink": row["drink_pref"], "count": row["count"]})

    bytes_buf = io.BytesIO(output.getvalue().encode("utf-8-sig"))
    bytes_buf.name = "drinks_stats.csv"
    return bytes_buf
