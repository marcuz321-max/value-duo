"""Value Duo v2 – oddsinsamling för flera sporter."""

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone

SPORTS = [
    "soccer_epl",
    "basketball_nba",
    "icehockey_nhl",
    "americanfootball_nfl",
]

def fetch_quotes():
    api_key = os.getenv("ODDS_API_KEY", "").strip()

    if not api_key:
        return [], "NO_SOURCE"

    # Välj en sport per 12-timmarsperiod.
    now = datetime.now(timezone.utc)
    slot = int(now.timestamp() // (12 * 3600))
    sport = SPORTS[slot % len(SPORTS)]

    params = urllib.parse.urlencode({
        "apiKey": api_key,
        "regions": "eu",
        "markets": "h2h",
        "oddsFormat": "decimal",
    })

    url = (
        "https://api.the-odds-api.com/v4/sports/"
        + sport + "/odds/?" + params
    )

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ValueDuo/2.0"}
    )

    with urllib.request.urlopen(
        request, timeout=25
    ) as response:
        events = json.load(response)
        remaining = response.headers.get(
            "x-requests-remaining", "unknown"
        )

    rows = []

    for event in events:
        home = event.get("home_team")
        away = event.get("away_team")
        event_id = event.get("id")
        commence_time = event.get("commence_time")

        if not home or not away or not event_id:
            continue

        for bookmaker in event.get("bookmakers", []):
            source = bookmaker.get("key")

            if not source:
                continue

            for market in bookmaker.get("markets", []):
                if market.get("key") != "h2h":
                    continue

                outcomes = market.get("outcomes", [])
                names = [o.get("name") for o in outcomes]

                if (
                    len(names) != len(set(names))
                    or not {home, away}.issubset(set(names))
                ):
                    continue

                updated = market.get("last_update")

                if not updated:
                    continue

                for outcome in outcomes:
                    price = outcome.get("price")

                    if not isinstance(price, (int, float)):
                        continue

                    for role in ("offer", "reference"):
                        rows.append({
                            "sport": sport,
                            "event": event_id,
                            "home_team": home,
                            "away_team": away,
                            "commence_time": commence_time,
                            "market": "h2h",
                            "line": "full_time",
                            "outcome": outcome["name"],
                            "bookmaker": source,
                            "source": source,
                            "odds": price,
                            "observed_at": updated,
                            "role": role,
                        })

    print(
        "Sport:", sport,
        "| Oddsregistreringar:", len(rows),
        "| API-krediter kvar:", remaining
    )

    return rows, "API_ODDS"
