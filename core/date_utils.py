#date_utils.py
from datetime import datetime

def normalize_date(date_str: str):
    """
    Accepts multiple formats and converts to DDMMM (e.g., 23NOV)
    """

    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d-%m-%y",
        "%d/%m/%y",
        "%d %b %Y",
        "%d %b",
        "%d %B %Y",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)

            if "%Y" not in fmt and "%y" not in fmt:
                dt = dt.replace(year=datetime.now().year)

            return dt.strftime("%d%b").upper()

        except ValueError:
            continue

    raise ValueError(f"Unsupported date format: {date_str}")