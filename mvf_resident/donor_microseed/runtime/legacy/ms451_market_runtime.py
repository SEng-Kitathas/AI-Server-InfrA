#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, pathlib, time

MODE_RANK={'NAKED':0,'EQUIPPED':1,'FEDERATED':2}
def sha(p):
    h=hashlib.sha256();
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('capture'); ap.add_argument('output'); ap.add_argument('--hold',type=float,default=0.8); a=ap.parse_args()
    time.sleep(a.hold)  # gives the separate observer a real lifecycle window
    c=json.load(open(a.capture))
    obs=c['observations']
    assert len(obs)>=2
    left,right=obs[0],obs[1]
    same_label=left['instrument_label']==right['instrument_label']
    same_referent=left['provider_referent']==right['provider_referent']
    mode=max((o['resource_mode'] for o in obs),key=lambda x:MODE_RANK[x])
    current=all(o['currentness']=='CURRENT' for o in obs)
    l=float(left['normalized']['last']); r=float(right['normalized']['last'])
    result={
      'schema':'microseed.ms451.market-comparison-result.v0.1',
      'status':'WITNESS',
      'relation':'CROSS_VENUE_PAYLOAD_COMPARISON',
      'instrument_label':'BTC/EUR' if same_label else 'MIXED',
      'left_referent':left['provider_referent'],
      'right_referent':right['provider_referent'],
      'same_instrument_label':same_label,
      'same_market_referent':same_referent,
      'canonical_price_claim':'REJECTED',
      'corroboration_claim':'NOT_APPLICABLE_TO_DISTINCT_VENUE_REFERENTS',
      'captured_last_delta_eur':round(r-l,8),
      'captured_last_delta_percent_of_left':round((r-l)/l*100,8),
      'simultaneity_or_current_spread_claim':'UNKNOWN_INCOMPLETE' if not current else 'SUPPORTED_WITHIN_CAPTURE_BOUND',
      'currentness_inputs':[o['currentness'] for o in obs],
      'resource_mode':mode,
      'authority':'DERIVED_READ_ONLY',
      'input_sha256':sha(a.capture),
      'scar_checks':{
        'same_instrument_label_not_same_referent': same_label and not same_referent,
        'provider_count_not_currentness': not current,
        'federated_not_downlabelled': mode=='FEDERATED'
      }
    }
    pathlib.Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
if __name__=='__main__': main()
