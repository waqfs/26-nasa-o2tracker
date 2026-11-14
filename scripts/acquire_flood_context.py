"""Refresh public upstream boundary snapshots and an audit of local discharge availability."""
import argparse, hashlib, json
from datetime import datetime, timezone
import requests
from oxygen_debt.settings import SNAPSHOT_ROOT
import math

def number(value):
    try:
        parsed=float(value)
        return parsed if math.isfinite(parsed) else None
    except (TypeError,ValueError):return None

parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');args=parser.parse_args()
manifest_path=SNAPSHOT_ROOT/'provenance/flood_context_manifest.json'
if args.live:
    entries=[];availability=[]
    locations={'A4261108':817,'A4261053':781,'A4261248':846,'A4261023':768,'A4261024':770,'A4261263':855,'A4260645':744}
    for station,location in locations.items():
        response=requests.get('https://water.data.sa.gov.au/Data/Datasets/',params={'locationid':location},timeout=45)
        response.raise_for_status();datasets=response.json()
        availability.append(dict(station=station,source=response.url,discharge_series=[dict(identifier=d['DisplayText'],last_record=d['EndTime']) for d in datasets if d['Subtext']=='Discharge']))
        if station not in ['A4261023','A4261024']:continue
        for variable,parameter,unit in [('oxygen','O2 (Dis)',35),('temperature','Water Temp',169)]:
            selected=[d for d in datasets if d['Subtext']==parameter and d['Id']=='Best Available--DO Sensor-1m']
            if len(selected)!=1:raise ValueError('Boundary sensor not unique')
            dataset=selected[0]
            query=dict(DateRange='Custom',StartTime='2026-08-20 00:00',EndTime='2026-10-12 00:00',TimeZone=9.5,Calendar='CALENDARYEAR',Interval='Daily',Step=1,ExportFormat='json',TimeAligned='True',RoundData='False',IncludeGradeCodes='True',IncludeApprovalLevels='True',IncludeQualifiers='True',IncludeInterpolationTypes='True')
            query.update({'Datasets[0].DatasetName':dataset['DisplayText'],'Datasets[0].Calculation':'Aggregate','Datasets[0].UnitId':unit})
            response=requests.get('https://water.data.sa.gov.au/Export/BulkExportJson',params=query,timeout=90);response.raise_for_status()
            path=SNAPSHOT_ROOT/'observations'/f'{station}_{variable}.json';path.write_bytes(response.content)
            entries.append(dict(station=station,name=dataset['LocationName'],variable=variable,source=response.url,file='observations/'+path.name,sha256=hashlib.sha256(response.content).hexdigest()))
    manifest=dict(entries=entries,discharge_availability=availability,checked_utc=datetime.now(timezone.utc).isoformat(),scope='Queries at seven selected local stations, not a complete regional archive search. No overlap-period discharge series found among these datasets.')
    manifest_path.write_text(json.dumps(manifest,indent=2))
else:manifest=json.loads(manifest_path.read_text())
series=[]
for entry in manifest['entries']:
    path=SNAPSHOT_ROOT/entry['file'];data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=entry['sha256']:raise ValueError('Boundary source hash mismatch')
    raw=json.loads(data);rows=[]
    for row in raw['Rows']:
        point=row['Points'][0];rows.append(dict(time=row['Timestamp'],value=number(point.get('Value')),grade=point.get('GradeName')))
    series.append(dict(**entry,unit=raw['Datasets'][0]['Unit'],observations=rows))
(SNAPSHOT_ROOT/'derived/flood_context.json').write_text(json.dumps(dict(series=series,discharge_availability=manifest['discharge_availability'],scope=manifest['scope']),indent=2))
print('Boundary series:',[(s['station'],s['variable'],len(s['observations'])) for s in series])
