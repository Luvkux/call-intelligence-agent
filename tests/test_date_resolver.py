from datetime import datetime
from src.intelligence.date_resolver import DateResolver

def test_relative_date_resolution():
    # Wednesday 1 July 2026 (from PDF problem statement)
    ref_date = datetime(2026, 7, 1)

    # "15th of next month" -> 2026-08-15
    assert DateResolver.resolve_date("15th of next month", ref_date) == "2026-08-15"

    # "Friday" -> 2026-07-03
    assert DateResolver.resolve_date("Friday", ref_date) == "2026-07-03"

    # "today" -> 2026-07-01
    assert DateResolver.resolve_date("today", ref_date) == "2026-07-01"

    # "tomorrow" -> 2026-07-02
    assert DateResolver.resolve_date("tomorrow", ref_date) == "2026-07-02"
