import requests,json,pathlib
u='https://planetarycomputer.microsoft.com/api/stac/v1/search'
r=requests.get(u,params={'collections':'esa-worldcover','bbox':'140.45,-34.55,140.95,-34.15','datetime':'2021-01-01T00:00:00Z/2021-12-31T23:59:59Z','limit':20},timeout=60);r.raise_for_status();d=r.json();pathlib.Path('data/acquisition/worldcover_stac.json').write_text(json.dumps(d,indent=2));print([(f['id'],list(f['assets'])) for f in d['features']])
