import re
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import dateparser

class DateResolver:
    """
    Resolves relative date mentions in transcripts (e.g., "15th of next month", "Friday")
    to concrete ISO dates (YYYY-MM-DD) based on a reference call date.
    """

    @staticmethod
    def resolve_date(date_str: str, reference_date: datetime) -> str:
        """
        Resolves a date string relative to reference_date.
        Returns YYYY-MM-DD string or original string if unresolvable.
        """
        if not date_str or not date_str.strip():
            return None

        text = date_str.strip().lower()

        # 1. Exact ISO date check (e.g. 2026-08-15)
        iso_match = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", text)
        if iso_match:
            return text

        # 2. "today"
        if text in ["today", "now", "this afternoon"]:
            return reference_date.strftime("%Y-%m-%d")

        # 3. "tomorrow"
        if text == "tomorrow":
            return (reference_date + timedelta(days=1)).strftime("%Y-%m-%d")

        # 4. Pattern: "15th of next month" / "15th next month" / "the 15th of next month"
        match_next_month_day = re.search(r"(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?next\s+month", text)
        if match_next_month_day:
            day = int(match_next_month_day.group(1))
            next_month_dt = reference_date + relativedelta(months=1)
            try:
                resolved_dt = datetime(next_month_dt.year, next_month_dt.month, day)
                return resolved_dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

        # 5. Pattern: "15th of this month"
        match_this_month_day = re.search(r"(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?this\s+month", text)
        if match_this_month_day:
            day = int(match_this_month_day.group(1))
            try:
                resolved_dt = datetime(reference_date.year, reference_date.month, day)
                return resolved_dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

        # 6. Pattern: Day of week e.g. "friday", "by friday", "this friday", "next friday"
        days_of_week = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for idx, day_name in enumerate(days_of_week):
            if day_name in text:
                current_weekday = reference_date.weekday()
                target_weekday = idx
                days_ahead = target_weekday - current_weekday
                if days_ahead <= 0:  # Target day already passed this week or is today
                    days_ahead += 7
                if "next" in text and days_ahead <= 7:
                    # e.g. "next Friday" when today is Wednesday -> target Friday next week
                    pass
                resolved_dt = reference_date + timedelta(days=days_ahead)
                return resolved_dt.strftime("%Y-%m-%d")

        # 7. Fallback to dateparser relative parsing
        parsed = dateparser.parse(
            text,
            settings={
                "RELATIVE_BASE": reference_date,
                "PREFER_DATES_FROM": "future"
            }
        )
        if parsed:
            return parsed.strftime("%Y-%m-%d")

        return None
