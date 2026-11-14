"""Fetch DEA Landsat water observations independently of the Sentinel labels and radar."""
import json,requests
import numpy as np
from pathlib import Path
from canopy_pulse.comparison import subset,write,SHAPE
from canopy_pulse.raster import sha256
raw=Path('data/validation')
url='https://explorer.dea.ga.gov.au/stac/search'
params={'collections':'ga_ls_wo_3','bbox':'140.45,-34.55,140.95,-34.15','datetime':'2026-08-15/2026-10-15','limit':100}
r=requests.get(url,params=params,timeout=60);r.raise_for_status();(raw/'dea_water_stac.json').write_bytes(r.content)
manifest=[]
for date in ['2026-08-23','2026-09-24','2026-10-02']:
    tile=np.full(SHAPE,np.nan,dtype='float32')
    for item in r.json()['features']:
        if not item['properties']['datetime'].startswith(date):continue
        asset=item['assets']['water'];asset['href']=asset['href'].replace('s3://dea-public-data/','https://dea-public-data.s3.ap-southeast-2.amazonaws.com/')
        a=subset(item,'water');valid=np.isin(a,[0,128]);tile[valid]=a[valid]
        manifest.append({'item':item['id'],'time':item['properties']['datetime'],'asset':asset['href'],'valid_grid_cells':int(valid.sum())})
    path=raw/f'dea_{date}.tif';write(path,tile)
    manifest.append({'file':str(path),'sha256':sha256(path)})
(raw/'dea_manifest.json').write_text(json.dumps(manifest,indent=2))
