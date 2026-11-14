"""Verify immutable retained granule identity and geometry against the current official CMR records."""
import json, requests
from datetime import datetime, timezone
from oxygen_debt.settings import SNAPSHOT_ROOT, read_json

checks=[]
for acquisition in read_json('provenance/request.json')['acquisitions']:
    response=requests.get('https://cmr.earthdata.nasa.gov/search/granules.umm_json',params={'concept_id':acquisition['concept_id']},timeout=35)
    response.raise_for_status();items=response.json()['items']
    if len(items)!=1:raise ValueError('Expected one official catalog granule')
    item=items[0];umm=item['umm'];attrs={v['Name']:v.get('Values') for v in umm.get('AdditionalAttributes',[])}
    if umm['GranuleUR']!=acquisition['granule_id'] or umm['TemporalExtent']['RangeDateTime']['BeginningDateTime']!=acquisition['record']['start']:raise ValueError('Catalog identity/time mismatch')
    keys=['ASCENDING_DESCENDING','TRACK_NUMBER','FRAME_NUMBER','FREQUENCY_A_RANGE_BANDWIDTH','FREQUENCY_A_POLARIZATION','PRODUCTION_PIPELINE','PRODUCT_VERSION','ORBIT_TYPE','FULL_FRAME','JOINT_OBSERVATION']
    for key in keys:
        if attrs[key]!=acquisition['record']['attributes'][key]:raise ValueError('Geometry/processing mismatch: '+key)
    checks.append(dict(concept_id=acquisition['concept_id'],granule_id=umm['GranuleUR'],acquired=umm['TemporalExtent']['RangeDateTime']['BeginningDateTime'],source=response.url,attributes={k:attrs[k] for k in keys},current_revision_id=item['meta'].get('revision-id'),status='MATCHES retained acquisition metadata'))
(SNAPSHOT_ROOT/'provenance/nisar_metadata_recheck.json').write_text(json.dumps(dict(checked_utc=datetime.now(timezone.utc).isoformat(),granules=checks,scope='Catalog identity and geometry recheck, not independent radiometric calibration or raw telemetry'),indent=2),encoding='utf-8')
print('Official CMR acquisitions verified:',len(checks))
