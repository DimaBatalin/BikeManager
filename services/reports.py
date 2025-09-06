from datetime import datetime, timedelta
from calendar import monthrange

def get_weekly_totals(archive_list: list):
    result = []
    today = datetime.now()
    for i in range(4):
        end = today - timedelta(days=7*i)
        start = end - timedelta(days=6)
        week_sum = 0
        for r in archive_list:
            closed = datetime.fromisoformat(r["date_closed"])
            if start.date() <= closed.date() <= end.date():
                week_sum += r["cost"]
        result.append(((start.date(), end.date()), week_sum))
    return result[::-1]


def get_monthly_totals(archive_list: list):
    result = []
    today = datetime.now()
    year = today.year
    month = today.month
    for i in range(12):
        y = year
        m = month - i
        if m <= 0:
            m += 12
            y -= 1
        start = datetime(y, m, 1)
        last_day = monthrange(y, m)[1]
        end = datetime(y, m, last_day, 23, 59, 59)
        month_sum = 0
        for r in archive_list:
            closed = datetime.fromisoformat(r["date_closed"])
            if start <= closed <= end:
                month_sum += r["cost"]
        result.append(((y, m), month_sum))
    return result[::-1]
