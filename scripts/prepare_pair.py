"""Write a native radar pair configuration from exact retained Harmony provenance."""
import argparse
import json
from pathlib import Path
from canopy_pulse.raster import MASK_CONVENTION, sha256
from oxygen_debt.settings import DATA_ROOT, read_json

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--before', default='2026-08-23')
parser.add_argument('--after', default='2026-09-28')
parser.add_argument('--polarization', choices=['HHHH', 'HVHV'], default='HHHH')
parser.add_argument('--output', default='outputs/local/pair.json')
args = parser.parse_args()
jobs = read_json('provenance/jobs.json')
acquisitions = read_json('provenance/request.json')['acquisitions']
configuration = {'polarization': args.polarization, 'mask_convention': MASK_CONVENTION}
for label, date in [('before', args.before), ('after', args.after)]:
    matches = [item for item in acquisitions if item['record']['start'].startswith(date + 'T')]
    if len(matches) != 1:
        parser.error(f'Expected one retained acquisition for {date}')
    acquisition = matches[0]
    specification = {'granule_id': acquisition['granule_id']}
    for key, layer in [('power', args.polarization), ('mask', 'mask'), ('looks', 'numberOfLooks')]:
        record = jobs[acquisition['concept_id'] + '_' + layer]['file']
        source = record['path'].replace('\\', '/')
        path = DATA_ROOT / source.removeprefix('data/')
        if not path.is_file():
            parser.error(f'Missing {date} {layer}: acquire the source files and set OXYGEN_DATA_ROOT')
        if sha256(path) != record['sha256']:
            parser.error(f'Checksum mismatch for {date} {layer}; the retained source must be restored')
        specification[key] = str(path)
    configuration[label] = specification
destination = Path(args.output)
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(configuration, indent=2), encoding='utf-8')
print('Wrote native radar pair configuration')
