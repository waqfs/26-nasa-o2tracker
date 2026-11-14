import json
from canopy_pulse.comparison import ROOT,subset,write
from canopy_pulse.raster import sha256
item=json.loads((ROOT/'data/acquisition/worldcover_stac.json').read_text())['features'][0]
path=ROOT/'data/raw/comparison/worldcover_2021.tif'
array=subset(item,'map',signed=True)
write(path,array)
(ROOT/'outputs/comparison/landcover_manifest.json').write_text(json.dumps(dict(item_id=item['id'],
    source_url=item['assets']['map']['href'],path=str(path.relative_to(ROOT)),sha256=sha256(path),
    interpretation='2021 land-cover class, not 2026 field truth or an inundation label',
    attribution='ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium'),indent=2))
print('Retrieved WorldCover 2021 subset')
