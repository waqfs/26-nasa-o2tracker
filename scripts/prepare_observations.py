"""Normalize retained DEW source responses, preserving missing values and quality."""
import json
import math
import re
from pathlib import Path
from datetime import datetime, timezone
import requests
from oxygen_debt.settings import SNAPSHOT_ROOT
from canopy_pulse.raster import sha256

def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None

def main():
    manifest = json.loads((SNAPSHOT_ROOT/'provenance/station_manifest.json').read_text(encoding='utf-8'))
    sites = []
    for station, location_id in [('A4261108',817),('A4261053',781)]:
        metadata_path = SNAPSHOT_ROOT/'provenance'/f'{station}_location.json'
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text())
        else:
            response = requests.get('https://water.data.sa.gov.au/Data/Location_Summary/',params={'location':location_id},timeout=45)
            response.raise_for_status()
            match = re.search(r"GoTo\('map',\s*([\d.]+),\s*(-[\d.]+)\)",response.text)
            if not match:
                raise ValueError('Station coordinate missing from official location summary')
            lon,lat = map(float,match.groups())
            metadata = dict(id=station,longitude=lon,latitude=lat,datum='GDA94',source=response.url,
                            retrieved_utc=datetime.now(timezone.utc).isoformat())
            metadata_path.write_text(json.dumps(metadata,indent=2))
        entries = [entry for entry in manifest if entry['station']==station]
        site = dict(**metadata,name=entries[0]['dataset']['LocationName'],variables={})
        for entry in entries:
            dataset = entry['dataset']
            parameter = dataset['Subtext']
            if parameter=='Water Temp' and '--DO Sensor' not in dataset['Id']:
                continue
            variable = {'O2 (Dis)':'oxygen','Water Temp':'temperature','Water Level':'level'}.get(parameter)
            if variable is None:
                continue
            path = SNAPSHOT_ROOT/'observations'/Path(entry['path'].replace('\\','/')).name
            raw = json.loads(path.read_text())
            observations = []
            for row in raw['Rows']:
                point = row['Points'][0]
                observations.append(dict(time=row['Timestamp'],value=number(point.get('Value')),
                                         grade=point.get('GradeName'),grade_code=point.get('GradeCode')))
            site['variables'][variable] = dict(unit=raw['Datasets'][0]['Unit'],identifier=raw['Datasets'][0]['Identifier'],
                source=entry['request_url'],raw_file='data/observations/'+path.name,sha256=sha256(path),
                aggregation='Daily aggregate, source timestamp UTC+09:30. Aggregate-window convention unverified.',
                observations=observations)
        from pyproj import Transformer
        from canopy_pulse.comparison import TRANSFORM
        x,y = Transformer.from_crs(4283,32754,always_xy=True).transform(site['longitude'],site['latitude'])
        site['mesh_position'] = dict(row=(TRANSFORM.f-y)/100-.5,col=(x-TRANSFORM.c)/100-.5)
        sites.append(site)
    result = dict(stations=sites,quality_rule='Numeric finite values with source GradeName GOOD only in analysis. All rows retained.',
                  missing_drivers=['No same-station discharge or rainfall series in the retained two-station snapshot',
                                   'Hydraulic connectivity from candidate blocks to oxygen stations unverified',
                                   'No DOC, BOD or wetland-outlet carbon loading measurements'])
    (SNAPSHOT_ROOT/'derived/stations.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print([(s['id'],s['latitude'],s['longitude'],list(s['variables'])) for s in sites])

if __name__=='__main__':main()
