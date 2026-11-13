
"""Hämtar odds från The Odds API utan att exponera nyckeln."""
import json
import os
import urllib.parse
import urllib.request

def fetch_quotes():
    key = os.getenv("ODDS_API_KEY", "").strip()
    if not key:
        return [], "NO_SOURCE"

    params = urllib.parse.urlencode({
        "apiKey": key,
        "regions": "eu",
        "markets": "h2h",
        "oddsFormat": "decimal",
    })
    url = (
        "https://api.the-odds-api.com/v4/"
        "sports/soccer_epl/odds/?" + params
    )

    req = urllib.request.Request(
        url, headers={"User-Agent": "ValueDuo/1.0"}
    )
    with urllib.request.urlopen(req, timeout=25) as response:
        events = json.load(response)
        remaining = response.headers.get(
            "x-requests-remaining", "unknown"
        )

    rows = []
    for event in events:
        home = event.get("home_team")
        away = event.get("away_team")
        if not home or not away:
            continue

        for book in event.get("bookmakers", []):
            source = book.get("key")
            if not source:
                continue

            for market in book.get("markets", []):
                if market.get("key") != "h2h":
                    continue

                outcomes = market.get("outcomes", [])
                names = {o.get("name") for o in outcomes}
                if not {home, away}.issubset(names):
                    continue
                if len(names) != len(outcomes):
                    continue

                updated = market.get("last_update")
                if not updated:
                    continue

                for outcome in outcomes:
                    for role in ("offer", "reference"):
                        rows.append({
                            "sport": "soccer_epl",
                            "event": event["id"],
                            "market": "h2h",
                            "line": "full_time",
                            "outcome": outcome["name"],
                            "bookmaker": source,
                            "source": source,
                            "odds": outcome["price"],
                            "observed_at": updated,
                            "role": role,
                        })

    print("API credits remaining:", remaining)
    return rows, "API_ODDS"

