"""Recompute independent water-label support at candidate blocks; never infer inundated area from radar."""
import argparse, json
from pathlib import Path
import numpy as np
import rasterio
from oxygen_debt.settings import SNAPSHOT_ROOT, read_json
from canopy_pulse.comparison import SHAPE, TRANSFORM, CRS
from canopy_pulse.raster import sha256

parser=argparse.ArgumentParser();parser.add_argument('--workspace',required=True);parser.add_argument('--radar-audit',required=True);args=parser.parse_args()
root=Path(args.workspace);manifest=read_json('provenance/dea_manifest.json');locations=read_json('derived/investigation.json')['locations']
arrays={};sources=[]
for entry in manifest:
    if 'file' not in entry:continue
    path=root/entry['file'];digest=sha256(path)
    if digest!=entry['sha256']:raise ValueError('Landsat input hash mismatch')
    date=path.stem.removeprefix('dea_')
    with rasterio.open(path) as ds:
        if ds.shape!=SHAPE or ds.transform!=TRANSFORM or str(ds.crs)!=CRS:raise ValueError('Independent grid mismatch')
        arrays[date]=ds.read(1)
    sources.append(dict(date=date,file=entry['file'],sha256=digest,observation_times=[e['time'] for e in manifest if e.get('time','').startswith(date) and e.get('valid_grid_cells',0)>0]))
field_sources={}
for entry in read_json('provenance/field_visit_manifest.json'):
    path=SNAPSHOT_ROOT/entry['file']
    if sha256(path)!=entry['sha256']:raise ValueError('Field source hash mismatch')
    data=json.loads(path.read_text(encoding='utf-8'))
    field_sources[entry['station']]=dict(entry=entry,visits=[[row['Timestamp'],row['Points'][0]['Value'],row['Points'][0]['GradeName']] for row in data['Rows']])
for location in locations:
    if location.get('nearby_field'):
        field=field_sources[location['nearby_field']['station']]
        if field['visits']!=location['nearby_field']['visits']:raise ValueError('Field visit snapshot mismatch')
        location['nearby_field'].update(source=field['entry']['source'],sha256=field['entry']['sha256'],raw_file=field['entry']['file'])
    row=location['block']['row']*5;col=location['block']['col']*5
    location['landsat']=[]
    for date,array in arrays.items():
        block=array[row:row+5,col:col+5];clear=np.isin(block,[0,128]);wet=block==128
        location['landsat'].append(dict(date=date,clear_fraction=float(clear.mean()),water_fraction_full_block=float(wet.mean()),water_fraction_clear_only=float(wet.sum()/clear.sum()) if clear.any() else None,source='DEA Landsat Water Observations',support='25 resampled 20m cells in one 100m block; original Landsat nominal resolution 30m; not 25 independent labels'))
    # Keep only contextual evidence needed; candidate ranking is not a probability.
    for key in list(location):
        if key not in ['id','name','lon','lat','block','nisar','sentinel1','optical','nearby_field','landsat']:del location[key]
audit=json.loads(Path(args.radar_audit).read_text())
if audit!=read_json('derived/radar_audit.json'):raise ValueError('New native audit differs from retained audit; scientific review required')
result=dict(locations=locations,landsat_sources=sources,radar_recheck=dict(matches_retained_snapshot=True,report='data/derived/radar_audit.json'),
            quantitative_inundation_verdict='UNSUPPORTED: calibrated power is usable for exploratory change, but no validated radar-to-flooded-area/depth conversion is established.',
            field_caution='GOOD visits demonstrate local water-level change, not inundation area or depth at a candidate. Station datums and hydraulic connection remain unresolved.',
            landsat_caution='Clear exposed-water labels only, cross-date comparison and selected candidate population. No below-canopy truth. Cloud or missing is unknown, not dry.',
            assumptions='No field level, Landsat fraction or radar candidate automatically supplies a flooded-area or volume parameter.')
(SNAPSHOT_ROOT/'derived/flood_evidence.json').write_text(json.dumps(result,indent=2))
print('Verified',len(locations),'locations and',len(arrays),'Landsat dates')
