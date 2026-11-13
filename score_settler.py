
"""Value Duo – automatisk kontroll av slutresultat, SIM ONLY."""

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from paper_tracker import load_bets, save_bets, settle_bet

SPORTS = {
    "basketball_nba",
    "soccer_epl",
    "icehockey_nhl",
    "americanfootball_nfl",
}


def parse_time(value):
    try:
        result = datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        )
        if result.tzinfo is None:
            return None
        return result.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def fetch_scores(sport, api_key):
    params = urllib.parse.urlencode({
        "apiKey": api_key,
        "daysFrom": 3,
        "dateFormat": "iso",
    })
    url = (
        "https://api.the-odds-api.com/v4/sports/"
        + sport + "/scores/?" + params
    )
    request = urllib.request.Request(
        url, headers={"User-Agent": "ValueDuo/3.1"}
    )
    with urllib.request.urlopen(
        request, timeout=25
    ) as response:
        data = json.load(response)
        remaining = response.headers.get(
            "x-requests-remaining", "unknown"
        )
    if not isinstance(data, list):
        raise ValueError("Ogiltigt API-svar")
    print(sport, "| API-krediter kvar:", remaining)
    return data


def match_result(bet, game):
    """Returnera WIN/LOSS/VOID eller None om osäkert."""

    if not game.get("completed"):
        return None

    if game.get("id") != bet.get("event"):
        return None

    if game.get("sport_key") != bet.get("sport"):
        return None

    home = bet.get("home_team")
    away = bet.get("away_team")

    if not home or not away:
        return None

    if (
        home != game.get("home_team")
        or away != game.get("away_team")
    ):
        return None

    if (
        bet.get("market") != "h2h"
        or bet.get("line") != "full_time"
    ):
        return None

    start = parse_time(bet.get("commence_time"))
    observed = parse_time(bet.get("observed_at"))
    actual_start = parse_time(game.get("commence_time"))

    if not start or not observed or not actual_start:
        return None

    if observed > start or observed > actual_start:
        return None

    # Kräver rimlig överensstämmelse i matchstart.
    if abs((actual_start - start).total_seconds()) > 86400:
        return None

    scores = game.get("scores")
    if not isinstance(scores, list) or len(scores) != 2:
        return None

    try:
        score_map = {
            row["name"]: int(row["score"])
            for row in scores
        }
    except (KeyError, ValueError, TypeError):
        return None

    if set(score_map) != {home, away}:
        return None

    home_score = score_map[home]
    away_score = score_map[away]

    if home_score < 0 or away_score < 0:
        return None

    sport = bet["sport"]
    outcome = bet.get("outcome")

    if sport == "soccer_epl":
        # Premier League: 1X2, ordinarie matchtid.
        if home_score > away_score:
            winner = home
        elif away_score > home_score:
            winner = away
        else:
            winner = "Draw"

        if outcome not in (home, away, "Draw"):
            return None

        return "WIN" if outcome == winner else "LOSS"

    if sport == "icehockey_nhl":
        # NHL h2h kan avse olika marknadsregler.
        # Avräkna inte utan verifierad 2-vägsmarknad.
        if bet.get("settlement_rules") != "including_overtime":
            return None

    if sport not in {
        "basketball_nba",
        "icehockey_nhl",
        "americanfootball_nfl",
    }:
        return None

    if outcome not in (home, away):
        return None

    if home_score == away_score:
        # Exempelvis oavgjord NFL-match:
        # kräver separat kontroll av marknadsregler.
        return None

    winner = home if home_score > away_score else away
    return "WIN" if outcome == winner else "LOSS"


def settle_pending():
    """Kontrollera endast relevanta öppna observationer."""
    api_key = os.getenv("ODDS_API_KEY", "").strip()
    bets = load_bets()
    now = datetime.now(timezone.utc)

    pending_by_sport = {}

    for bet in bets:
        if bet.get("status") != "PENDING":
            continue

        sport = bet.get("sport")
        start = parse_time(bet.get("commence_time"))

        # Äldre poster utan matchstart lämnas orörda.
        if sport not in SPORTS or start is None:
            continue

        # Vänta tills matchen rimligen kan vara avslutad.
        if (now - start).total_seconds() < 4 * 3600:
            continue

        # API:t erbjuder endast en kort resultathistorik.
        if (now - start).total_seconds() > 3 * 86400:
            continue

        pending_by_sport.setdefault(sport, []).append(bet)

    if not pending_by_sport:
        print("Inga relevanta matcher att kontrollera.")
        return 0

    if not api_key:
        print("ODDS_API_KEY saknas.")
        return 0

    settled = 0

    for sport, sport_bets in pending_by_sport.items():
        try:
            games = fetch_scores(sport, api_key)
        except Exception as exc:
            print("Resultathämtning misslyckades:", sport, exc)
            continue

        by_id = {
            game["id"]: game
            for game in games
            if isinstance(game, dict) and game.get("id")
        }

        for bet in sport_bets:
            game = by_id.get(bet["event"])
            if game is None:
                continue

            result = match_result(bet, game)
            if result is None:
                continue

            settle_bet(bet, result)
            bet["settled_at"] = now.isoformat(
                timespec="seconds"
            )
            bet["final_scores"] = game.get("scores")
            bet["settlement_source"] = "THE_ODDS_API"
            settled += 1

    if settled:
        save_bets(bets)

    print("Automatiskt avräknade observationer:", settled)
    return settled


if __name__ == "__main__":
    settle_pending()
