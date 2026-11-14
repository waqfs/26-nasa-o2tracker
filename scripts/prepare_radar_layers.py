"""Recreate six actual radar mesh layers from configurable external science TIFFs."""
import json
from pathlib import Path
import numpy as np
from rasterio.warp import reproject,Resampling
from oxygen_debt.settings import SNAPSHOT_ROOT,DATA_ROOT
from canopy_pulse.comparison import SHAPE,TRANSFORM,CRS
from canopy_pulse.raster import read_cogs,MASK_CONVENTION
from canopy_pulse.science import block_power,power_db

mesh=json.loads((SNAPSHOT_ROOT/'derived/signal_mesh.json').read_text())
jobs=json.loads((SNAPSHOT_ROOT/'provenance/jobs.json').read_text())
request=json.loads((SNAPSHOT_ROOT/'provenance/request.json').read_text())
height,width=SHAPE[0]//5*5,SHAPE[1]//5*5
for acquisition in request['acquisitions']:
    for polarization in ['HHHH','HVHV']:
        paths={}
        for name in [polarization,'mask','numberOfLooks']:
            original=jobs[acquisition['concept_id']+'_'+name]['file']['path'].replace('\\','/')
            relative=original.removeprefix('data/')
            paths[name]=DATA_ROOT/relative
        layer=read_cogs(paths[polarization],paths['mask'],paths['numberOfLooks'],MASK_CONVENTION)
        destination=np.full(SHAPE,np.nan,dtype='float32')
        reproject(np.where(layer.valid,layer.power,np.nan),destination,src_transform=layer.transform,src_crs=layer.crs,src_nodata=np.nan,
                  dst_transform=TRANSFORM,dst_crs=CRS,dst_nodata=np.nan,resampling=Resampling.average)
        power,coverage=block_power(destination[:height,:width],np.isfinite(destination[:height,:width])&(destination[:height,:width]>0),5)
        sampled=power_db(np.where(coverage>=.8,power,np.nan))[::4,::4]
        prefix='HH' if polarization=='HHHH' else 'HV'
        key=prefix+'_'+acquisition['record']['start'][:10].replace('-','')
        mesh['layers'][key]=np.where(np.isfinite(sampled),sampled,0).round(3).tolist()
(SNAPSHOT_ROOT/'derived/signal_mesh.json').write_text(json.dumps(mesh))
print('Recreated six real HH/HV mesh layers')
