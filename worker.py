"""Scheduled offline analysis: licensed/user-supplied CSV only, no unsupported scraping."""
import csv,json,os
from datetime import datetime, timezone
from pathlib import Path
from engine import evaluate
BASE=Path(__file__).resolve().parent
INPUT=BASE/'inputs'/'quotes.csv'
DEST=BASE/'docs'/'data'/'latest.json'

def run():
    rows=[]
    if INPUT.exists():
        with INPUT.open(encoding='utf-8-sig',newline='') as fh:
            reader=csv.DictReader(fh)
            needed={'sport','event','market','line','outcome','bookmaker','odds','source','observed_at','role'}
            if not needed.issubset(reader.fieldnames or ()):
                raise ValueError('CSV måste innehålla: '+', '.join(sorted(needed)))
            rows=list(reader)[:50000]
    offers=evaluate(rows)
    reviewed=[r for r in offers if r['decision']=='GRANSKA']
    now=datetime.now(timezone.utc).isoformat(timespec='seconds')
    discussion=[
        {'agent':'ATLAS','text':f'Analyserade {len(offers)} aktiva erbjudna odds från importerade källor. {len(reviewed)} preliminära prisavvikelser för granskning.','ts':now},
        {'agent':'QUANT','text':'Inga verifierade spelrekommendationer: prisavvikelse är inte bevisad modellfördel. Kräver oberoende kalibrering, jämförbara marknadsregler och framåttest.','ts':now},
    ]
    # Public website must not expose licensed raw datasets, credentials or private analysis history.
    result={'generated_at':now,'mode':'REGELBASERAD ANALYS','live':False,'data_kind':'IMPORTED_CSV' if rows else 'NO_SOURCE',
            'input_rows':len(rows),'offer_count':len(offers),'reviewed_count':len(reviewed),
            'results':offers[:200],'discussion':discussion,
            'notice':'Preliminära forskningskandidater, inte verifierat lönsamma speltips. Inga spel placeras.'}
    DEST.parent.mkdir(parents=True,exist_ok=True)
    DEST.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'offer_count':len(offers),'reviewed_count':len(reviewed)}))

if __name__=='__main__':run()
