import json
import numpy as np
import rasterio
from pyproj import Transformer
from pathlib import Path
out=Path('outputs/validation')
c=json.loads(Path('outputs/real/candidate_investigation_points.geojson').read_text())['features']
proj=Transformer.from_crs(4326,32754,always_xy=True)
records=[]
for i,f in enumerate(c):
    x,y=proj.transform(*f['geometry']['coordinates']);rec={'rank':i+1}
    for d in ['2026-08-23','2026-09-24','2026-10-02']:
        with rasterio.open('data/validation/dea_'+d+'.tif') as ds:
            row,col=ds.index(x,y);a=ds.read(1,window=rasterio.windows.Window(col-2,row-2,5,5))
            rec[d]={'wet':int((a==128).sum()),'clear':int(np.isfinite(a).sum())}
    records.append(rec)
(out/'candidate_landsat.json').write_text(json.dumps(records,indent=2))
for d in ['2026-08-23','2026-09-24','2026-10-02']:
    print(d,[(r['rank'],r[d]) for r in records if r[d]['wet']],sum(r[d]['clear']>=23 for r in records))
