"""Pre-watering optical imagery and Copernicus DSM on the measured mesh grid."""
import json,requests,rasterio,numpy as np
from pathlib import Path
from shapely.geometry import shape,box
from rasterio.warp import reproject,Resampling
from canopy_pulse.comparison import ROOT,TRANSFORM,CRS,BBOX,subset,write
from canopy_pulse.raster import sha256
out=ROOT/'outputs/validation';raw=ROOT/'data/validation'
url='https://earth-search.aws.element84.com/v1/search'
r=requests.get(url,params={'collections':'sentinel-2-l2a','bbox':','.join(map(str,BBOX)),'datetime':'2026-06-20T00:00:00Z/2026-07-15T23:59:59Z','limit':100},timeout=60);r.raise_for_status()
(raw/'prewatering_stac.json').write_bytes(r.content)
features=r.json()['features'];groups={}
for f in features:groups.setdefault((f['properties']['datetime'][:10],f['properties']['platform']),[]).append(f)
from shapely.ops import unary_union
aoi=box(*BBOX)
rank=[]
for key,items in groups.items():
    covered=unary_union([shape(i['geometry']) for i in items]).intersection(aoi).area/aoi.area
    if covered>.995:rank.append((np.mean([i['properties']['eo:cloud_cover'] for i in items]),key,items))
_,date,items=min(rank,key=lambda x:x[0])
mosaic=None
for i in items:
    a=subset(i,'scl')
    if mosaic is None:mosaic=np.full_like(a,np.nan)
    valid=np.isfinite(a)&(a>0);mosaic[valid]=a[valid]
p=raw/'prewatering_scl.tif';write(p,mosaic)
record={'acquisition':date,'items':[i['id'] for i in items],'urls':[i['assets']['scl']['href'] for i in items],'sha256':sha256(p),'clear_fraction':float(np.isin(mosaic,[4,5,6]).mean())}
(out/'prewatering.json').write_text(json.dumps(record,indent=2));print(record,flush=True)
tile='Copernicus_DSM_COG_10_S35_00_E140_00_DEM'
url=f'https://copernicus-dem-30m.s3.amazonaws.com/{tile}/{tile}.tif'
p=raw/'surface_elevation.tif'
r=requests.get(url,timeout=90);r.raise_for_status();p.write_bytes(r.content)
mesh=json.loads((ROOT/'outputs/real/signal_mesh.json').read_text())
rows,cols=np.shape(mesh['values']);x,y=mesh['sample_centers_origin_utm']
dst=np.full((rows,cols),np.nan,dtype='float32')
with rasterio.open(p) as src:
    reproject(rasterio.band(src,1),dst,src_transform=src.transform,src_crs=src.crs,src_nodata=src.nodata,dst_transform=rasterio.transform.from_origin(x-200,y+200,400,400),dst_crs=CRS,dst_nodata=np.nan,resampling=Resampling.bilinear)
assert np.isfinite(dst).all()
(ROOT/'outputs/real/terrain.json').write_text(json.dumps(dict(source=url,sha256=sha256(p),values=dst.round(2).tolist(),units='m',datum='EGM2008',type='Copernicus GLO-30 digital surface model',spacing_m=400)))
