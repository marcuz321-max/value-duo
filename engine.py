"""Conservative independent market-data evaluator; no money or bets placed."""
from datetime import datetime,timezone
from math import isfinite

def ts(value):
    try:
        t=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return t.astimezone(timezone.utc) if t.tzinfo else None
    except (ValueError,TypeError): return None

def evaluate(rows, now=None, max_age_min=30, min_ev=.03, max_disagreement=.10):
    now=now or datetime.now(timezone.utc)
    groups={}
    for row in rows:
        try:
            r={k:str(v).strip() for k,v in row.items()}
            r['odds']=float(r['odds'])
            if not (isfinite(r['odds']) and 1<r['odds']<1001):continue
            if r.get('role') not in ('offer','reference'): continue
            required=['sport','event','market','line','outcome','bookmaker','source','observed_at']
            if any(not r.get(k) for k in required):continue
            t=ts(r['observed_at'])
            if t is None or not (-5 <= (now-t).total_seconds()/60 <= max_age_min):continue
            key=tuple(r[k].casefold() for k in ('sport','event','market','line'))
            groups.setdefault(key,[]).append(r)
        except (KeyError,ValueError,TypeError):pass
    all_offers=[]
    for key,quotes in groups.items():
        # Reference partitions are valid only for complete exhaustive market sides.
        by_source={}
        for q in quotes:
            if q['role']=='reference':by_source.setdefault(q['source'],[]).append(q)
        distributions={}
        for source,items in by_source.items():
            names=[x['outcome'].casefold() for x in items]
            if len(names)<2 or len(names)!=len(set(names)):continue
            inv={x['outcome'].casefold():1/x['odds'] for x in items}
            raw=sum(inv.values())
            if .9<=raw<=1.35:
                distributions[source]={k:v/raw for k,v in inv.items()}
        # References must have exactly identical outcome sets for this market.
        for q in (x for x in quotes if x['role']=='offer'):
            result={k:q[k] for k in ('sport','event','market','line','outcome','bookmaker','source','observed_at')}
            result.update(odds=q['odds'],prob=None,fair=None,ev=None,decision='AVSTÅ',reason='För få tillförlitliga referensmarknader',reference_sources=[])
            target=q['outcome'].casefold()
            pool=[(s,p) for s,p in distributions.items() if s!=q['source'] and target in p]
            # Sources with different outcome sets must not be combined.
            if pool:
                signature=set(pool[0][1]);pool=[(s,p) for s,p in pool if set(p)==signature]
            if len(pool)>=2:
                ps=[p[target] for _,p in pool]
                result['reference_sources']=[s for s,_ in pool]
                if max(ps)-min(ps)>max_disagreement:
                    result['reason']='Referenskällorna oense'
                else:
                    p=sum(ps)/len(ps);ev=p*q['odds']-1
                    result.update(prob=round(p*100,2),fair=round(1/p,3),ev=round(ev*100,2))
                    if ev<min_ev:result['reason']='EV under gränsen'
                    elif ev>.25:result['reason']='Extremt EV – undersök marknadsmatchning'
                    else:
                        result.update(decision='GRANSKA',reason='Preliminär prisavvikelse; kräver kalibrering och separat verifiering')
            all_offers.append(result)
    return sorted(all_offers,key=lambda r:(r['ev'] is not None, r['ev'] or -999),reverse=True)
