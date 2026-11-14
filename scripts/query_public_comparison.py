import requests,json,pathlib
p=pathlib.Path('data/acquisition');p.mkdir(exist_ok=True)
for name,url,collection in [('sentinel2','https://earth-search.aws.element84.com/v1/search','sentinel-2-l2a'),('sentinel1rtc','https://planetarycomputer.microsoft.com/api/stac/v1/search','sentinel-1-rtc')]:
 q={'collections':collection,'bbox':'140.45,-34.55,140.95,-34.15','datetime':'2026-08-20T00:00:00Z/2026-10-13T23:59:59Z','limit':100}
 try:
  r=requests.get(url,params=q,timeout=60);r.raise_for_status();d=r.json();(p/(name+'_stac.json')).write_text(json.dumps(d,indent=2));print(name,'features',len(d.get('features',[])));print([(f['id'],f['properties'].get('datetime'),f['properties'].get('eo:cloud_cover')) for f in d.get('features',[])][:10]);print('assets',list(d.get('features',[{'assets':{}}])[0]['assets']))
 except Exception as e:print(name,type(e).__name__)
