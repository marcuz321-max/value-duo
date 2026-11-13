"""Value Duo – register för simulerade spel."""

import json
from datetime import datetime, timezone
from pathlib import Path

PATH = Path("data/paper_bets.json")


def load_bets():
    if not PATH.exists():
        return []
    data = json.loads(PATH.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def save_bets(bets):
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(
        json.dumps(bets, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def register_candidates(candidates, stake=100):
    """Registrera kandidater utan att placera spel."""
    bets = load_bets()

    existing = {
        (
            b["event"], b["market"], b["line"],
            b["outcome"], b["bookmaker"]
        )
        for b in bets
    }

    added = 0

    for item in candidates:
        if item.get("decision") != "GRANSKA":
            continue

        key = (
            item["event"], item["market"], item["line"],
            item["outcome"], item["bookmaker"]
        )

        if key in existing:
            continue

        odds = float(item["odds"])

        if odds <= 1:
            continue

        bets.append({
            "sport": item["sport"],
            "event": item["event"],
            "market": item["market"],
            "line": item["line"],
            "outcome": item["outcome"],
            "bookmaker": item["bookmaker"],
            "odds": odds,
            "estimated_ev": item.get("ev"),
            "observed_at": item["observed_at"],
            "registered_at": datetime.now(
                timezone.utc
            ).isoformat(timespec="seconds"),
            "stake": stake,
            "status": "PENDING",
            "profit": None,
        })

        existing.add(key)
        added += 1

    save_bets(bets)
    return added


def settle_bet(bet, result):
    """Avräkna ett spel med ett verifierat resultat."""
    if result not in ("WIN", "LOSS", "VOID"):
        raise ValueError("Ogiltigt resultat")

    if bet["status"] != "PENDING":
        raise ValueError("Spelet är redan avräknat")

    stake = float(bet["stake"])
    odds = float(bet["odds"])

    profit = {
        "WIN": stake * (odds - 1),
        "LOSS": -stake,
        "VOID": 0.0,
    }[result]

    bet["status"] = result
    bet["profit"] = round(profit, 2)
    return bet


def calculate_roi(bets):
    settled = [
        b for b in bets
        if b["status"] in ("WIN", "LOSS", "VOID")
    ]

    total_stake = sum(float(b["stake"]) for b in settled)
    profit = sum(float(b["profit"]) for b in settled)

    return {
        "settled_bets": len(settled),
        "pending_bets": sum(
            b["status"] == "PENDING" for b in bets
        ),
        "total_stake": round(total_stake, 2),
        "profit": round(profit, 2),
        "roi_percent": (
            round(100 * profit / total_stake, 2)
            if total_stake else None
        ),
    }
