"""
Timezone-aware market reference date utilities.

Each market closes at a different local time:
  NSE (India): 15:30 Asia/Kolkata (no DST)
  XETRA (Germany): 17:30 Europe/Berlin (DST-aware)
  NYSE (US): 16:00 America/New_York (DST-aware)

get_market_reference_date(market, as_of) returns the date string YYYY-MM-DD
representing the most recently closed session for that market.

If it is before market close today (in market local time), the most recent
closed session is yesterday. If it is at or after market close today, the
most recent closed session is today.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
CET = ZoneInfo("Europe/Berlin")
ET = ZoneInfo("America/New_York")

_MARKET_CONFIG: dict = {
    "NSE":   {"tz": IST, "close_hour": 15, "close_minute": 30},
    "XETRA": {"tz": CET, "close_hour": 17, "close_minute": 30},
    "NYSE":  {"tz": ET,  "close_hour": 16, "close_minute":  0},
}


def get_market_reference_date(market: str, as_of: datetime = None) -> str:
    """
    Return the YYYY-MM-DD date of the most recently closed session for *market*.

    Parameters
    ----------
    market : str
        One of "NSE", "XETRA", "NYSE".
    as_of : datetime, optional
        The reference moment in time (timezone-aware). Defaults to now (UTC).

    Returns
    -------
    str
        ISO 8601 date string "YYYY-MM-DD".

    Raises
    ------
    ValueError
        If *market* is not one of the supported market codes.
    """
    if market not in _MARKET_CONFIG:
        raise ValueError(f"Unknown market: {market}. Must be one of {list(_MARKET_CONFIG.keys())}")

    if as_of is None:
        as_of = datetime.now(ZoneInfo("UTC"))

    cfg = _MARKET_CONFIG[market]
    tz = cfg["tz"]

    # Convert the reference moment to market local time
    as_of_local = as_of.astimezone(tz)

    # Build the close time for today in the market's local timezone
    close_today = as_of_local.replace(
        hour=cfg["close_hour"],
        minute=cfg["close_minute"],
        second=0,
        microsecond=0,
    )

    # If we are before close today, the most recent closed session is yesterday
    if as_of_local < close_today:
        ref_date = (as_of_local - timedelta(days=1)).date()
    else:
        ref_date = as_of_local.date()

    return ref_date.isoformat()
