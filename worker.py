"""Value Duo v2 – ATLAS, QUANT och analysuppföljning."""

import json
from datetime import datetime, timezone
from pathlib import Path

from engine import evaluate
from odds_feed import fetch_quotes

DATA = Path("data")
LATEST = DATA / "latest.json"
HISTORY = DATA / "history.json"


def read_history():
    if not HISTORY.exists():
        return []
    try:
        data = json.loads(HISTORY.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (ValueError, OSError):
        return []


def run():
    now = datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )

    rows, source = fetch_quotes()
    offers = evaluate(rows)

    reviewed = [
        item for item in offers
        if item["decision"] == "GRANSKA"
    ]

    sports = sorted({
        row["sport"] for row in rows
        if row.get("sport")
    })

    # Visa bara de starkaste preliminära kandidaterna.
    candidates = sorted(
        reviewed,
        key=lambda x: x.get("ev") or 0,
        reverse=True
    )[:5]

    discussion = [
        {
            "agent": "ATLAS",
            "text": (
                f"Jag analyserade {len(offers)} erbjudanden "
                f"inom {', '.join(sports) if sports else 'ingen sport'}. "
                f"Jag hittade {len(reviewed)} preliminära "
                "prisavvikelser."
            ),
            "ts": now,
        }
    ]

    if candidates:
        top = candidates[0]

        discussion.append({
            "agent": "ATLAS",
            "text": (
                f"Min högst rankade kandidat är "
                f"{top['outcome']} hos {top['bookmaker']} "
                f"till odds {top['odds']}. "
                f"Marknadsbaserat fair odds: {top['fair']}. "
                f"Beräknat EV: {top['ev']} %. "
                "Detta är en preliminär uppskattning."
            ),
            "ts": now,
        })

        discussion.append({
            "agent": "QUANT",
            "text": (
                "Jag godkänner inte kandidaten som ett "
                "verifierat lönsamt spel. Vi måste kontrollera "
                "att referenskällorna är oberoende, att "
                "marknadsreglerna matchar, att priset är "
                "spelbart och att vår sannolikhetsmodell "
                "är kalibrerad mot verkliga resultat."
            ),
            "ts": now,
        })

        discussion.append({
            "agent": "ATLAS",
            "text": (
                "Jag klassificerar därför kandidaten som "
                "GRANSKA, inte som ett färdigt speltips. "
                "Vi behöver samla tidsstämplade observationer "
                "och utvärdera resultat över tid."
            ),
            "ts": now,
        })
    else:
        discussion.append({
            "agent": "QUANT",
            "text": (
                "Inga kandidater passerade filtren. "
                "Vi avstår från att föreslå spel."
            ),
            "ts": now,
        })

    history = read_history()

    history.append({
        "generated_at": now,
        "sports": sports,
        "input_rows": len(rows),
        "offer_count": len(offers),
        "reviewed_count": len(reviewed),
    })

    # Behåll de senaste 180 körningarna.
    history = history[-180:]

    DATA.mkdir(parents=True, exist_ok=True)

    HISTORY.write_text(
        json.dumps(history, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    result = {
        "generated_at": now,
        "mode": "REGELBASERAD ANALYS",
        "live": bool(rows),
        "data_kind": source,
        "input_rows": len(rows),
        "offer_count": len(offers),
        "reviewed_count": len(reviewed),
        "results": offers[:100],
        "discussion": discussion,
        "history_count": len(history),
        "notice": (
            "Preliminära prisjämförelser, inte verifierade "
            "speltips. Ingen historisk ROI är fastställd."
        ),
    }

    LATEST.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(
        "Sport:", sports,
        "| Erbjudanden:", len(offers),
        "| Kandidater:", len(reviewed),
        "| Historik:", len(history)
    )
  if __name__ == "__main__":
    run()
