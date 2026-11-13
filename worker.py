

"""Value Duo: schemalagd oddsanalys."""
import json
from datetime import datetime, timezone
from pathlib import Path

from engine import evaluate
from odds_feed import fetch_quotes

def run():
    rows, source = fetch_quotes()
    offers = evaluate(rows)
    reviewed = [
        item for item in offers
        if item["decision"] == "GRANSKA"
    ]

    now = datetime.now(timezone.utc).isoformat(
        timespec="seconds"
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
        "discussion": [
            {
                "agent": "ATLAS",
                "text": (
                    f"Analyserade {len(offers)} erbjudna odds. "
                    f"{len(reviewed)} preliminära "
                    "prisavvikelser för granskning."
                ),
                "ts": now,
            },
            {
                "agent": "QUANT",
                "text": (
                    "Prisjämförelser är inte bevisad "
                    "modellfördel. Ingen verifierad ROI. "
                    "Prospektiv testning krävs."
                ),
                "ts": now,
            },
        ],
        "notice": (
            "Preliminära forskningskandidater. "
            "Ingen garanterad avkastning."
        ),
    }

    path = Path("data/latest.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("Odds:", len(rows), "Kandidater:", len(reviewed))

if __name__ == "__main__":
    run()
