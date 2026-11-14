"""Evidence selection and outcome reveal remain separate from the scenario calculation."""
from datetime import timedelta
from .settings import read_json
from .investigation import timestamp, good_rows, compare


def context(station, location, pass_index):
    if not 0 <= pass_index <= 2:raise ValueError('Unknown radar pass')
    evidence=read_json('derived/flood_evidence.json')
    area=next(x for x in evidence['locations'] if x['id']==location)
    if station not in ['A4261108','A4261053']:raise ValueError('Unknown station')
    acquired=timestamp(area['nisar'][pass_index]['time'])
    boundary='A4261024' if station=='A4261108' else 'A4261023'
    boundary_context=read_json('derived/flood_context.json')
    inputs={}
    for variable in ['oxygen','temperature']:
        series=next(s for s in boundary_context['series'] if s['station']==boundary and s['variable']==variable)
        candidates=[r for r in good_rows(series) if abs((timestamp(r['time'])-acquired).total_seconds())<=43200]
        row=min(candidates,key=lambda r:abs((timestamp(r['time'])-acquired).total_seconds())) if candidates else None
        inputs[variable]=dict(station=boundary,name=series['name'],source=series['source'],unit=series['unit'],observation=row,
                             offset_hours=(timestamp(row['time'])-acquired).total_seconds()/3600 if row else None,
                             excluded_grades=sorted({r['grade'] for r in series['observations'] if abs((timestamp(r['time'])-acquired).total_seconds())<=43200 and r['grade']!='GOOD'}))
    return dict(location=area,radar_time=area['nisar'][pass_index]['time'],boundary_inputs=inputs,
                quantitative_inundation_verdict=evidence['quantitative_inundation_verdict'],
                field_caution=evidence['field_caution'],landsat_caution=evidence['landsat_caution'],
                boundary_caution='River Murray sensor upstream of the named wetland outlet, not a verified inflow to the selected candidate or target station. Constant forcing and routing remain educational assumptions. Daily aggregate window unverified.',
                local_flow=boundary_context['scope'],publication_parameters=read_json('provenance/flood_parameters.json'))


def reveal(station,location,pass_index,mode='retrospective'):
    selected=compare(station,location,mode=mode)['pairs'][pass_index]
    radar=timestamp(selected['radar_time'])
    source=next(s for s in read_json('derived/stations.json')['stations'] if s['id']==station)['variables']['oxygen']
    records=[dict(**r,relative_day=(timestamp(r['time'])-radar).total_seconds()/86400) for r in good_rows(source)
             if radar <= timestamp(r['time']) <= radar+timedelta(days=14) and (mode!='as_of' or timestamp(r['time'])<=radar)]
    return dict(selected=selected,observations=records,station=station,unit=source['unit'],source=source['source'],
                comparison='Recorded daily station means and hypothetical instantaneous scenario trajectories use different support and unverified hydraulic pathways. No error score, causal attribution or model validation is justified. Scenario day zero is the selected radar timestamp for display, not a verified inundation onset.')
