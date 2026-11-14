"""Sensor dependency audit and deterministic evidence dossiers, without invented flood constraints."""
import hashlib
import json
from datetime import datetime, timezone
from functools import lru_cache
from .settings import read_json
from .investigation import timestamp

ARMS={'A':'Field and water quality','B':'Field + conventional satellites','C':'Field + conventional satellites + NISAR'}


def digest(value):
    # Equivalent int/float inputs (100 versus 100.0) must share a physical fingerprint.
    # No rounding of unequal floating-point values; booleans and strings retain type.
    def normalize(item):
        if isinstance(item,dict):return {k:normalize(v) for k,v in item.items()}
        if isinstance(item,list):return [normalize(v) for v in item]
        if isinstance(item,(int,float)) and not isinstance(item,bool):return float(item) if item!=0 else 0.0
        return item
    return hashlib.sha256(json.dumps(normalize(value),sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


@lru_cache(maxsize=4)
def dated_sources(name):
    data=read_json('provenance/'+name+'_stac.json')
    return [(f['id'],f['properties'].get('datetime')) for f in data['features']]


def source_times(name,date):
    platform={'20260823':'S2B_','20260929':'S2A_','20261007':'S2C_'}
    return [time for identifier,time in dated_sources(name) if time and time[:10].replace('-','')==date and (name!='sentinel2' or identifier.startswith(platform.get(date,'')))]


def dossier(location='candidate-2',pass_index=1,arm='C'):
    if arm not in ARMS or not 0 <= pass_index <= 2:raise ValueError('Unsupported evidence arm or pass')
    all_data=read_json('derived/flood_evidence.json')
    area=next(x for x in all_data['locations'] if x['id']==location)
    acquired=area['nisar'][pass_index]['time'];cutoff=timestamp(acquired)
    field=area.get('nearby_field')
    field=dict(field,visits=[v for v in field['visits'] if v[2]=='GOOD' and timestamp(v[0])<=cutoff]) if field else None
    conventional={}
    if arm in ['B','C']:
        # Use full UTC source times, not date-only midnight, at the selected recorded-observation cutoff.
        for label,catalog in [('sentinel1','sentinel1rtc'),('optical','sentinel2')]:
            conventional[label]=[]
            for row in area[label]:
                times=[t for t in source_times(catalog,row['date']) if timestamp(t)<=cutoff]
                if times:conventional[label].append(dict(row,observation_times=sorted(set(times))))
        conventional['landsat']=[]
        for row in area['landsat']:
            times=[t for source in all_data['landsat_sources'] if source['date']==row['date'] for t in source['observation_times'] if timestamp(t)<=cutoff]
            if times:conventional['landsat'].append(dict(row,observation_times=times))
    nisar=area['nisar'][:pass_index+1] if arm=='C' else []
    diagnostic=None
    if len(nisar)>1:
        first,last=nisar[0],nisar[-1]
        hh=last['HHHH']-first['HHHH'];hv=last['HVHV']-first['HVHV']
        audit=read_json('derived/radar_audit.json')['changes_100m'][f'0_{pass_index}']
        offsets={name:audit['HHHH'][name]['percentiles'][3] for name in ['built_up_proxy','bare_sparse_proxy']}
        residuals={name:hh-value for name,value in offsets.items()}
        diagnostic=dict(hh_change_db=hh,hv_change_db=hv,hh_minus_hv_change_db=hh-hv,
                        regional_hh_median_change_db=audit['HHHH']['all']['percentiles'][3],
                        assumed_reference_offsets_db=offsets,local_hh_residuals_under_assumed_offsets_db=residuals,
                        interpretation='Measured local changes and sensitivity to two assumed common offsets. Proxies are not invariant; residuals are not calibrated uncertainty bounds or water labels. No correction is applied.',
                        support='Local native centered 5x5 20m power mean, versus matched-grid 100m reference medians; footprints may differ by one native-pixel edge.')
    optical_rows=conventional.get('landsat',[])
    clear=[r for r in optical_rows if r['clear_fraction']>0]
    hypotheses=[
      dict(question='Did radar measure a surface change?',status='MEASURED CHANGE' if diagnostic else 'NO REPEAT NISAR IN THIS ARM',
           finding=(f"HH {diagnostic['hh_change_db']:+.3f} dB, HV {diagnostic['hv_change_db']:+.3f} dB" if diagnostic else 'No two retained NISAR dates are visible.'),
           missing='A change in backscatter does not identify the environmental cause.'),
      dict(question='Does exposed-water evidence establish candidate inundation?',status='DERIVED LABELS, NO CANOPY TRUTH' if clear else 'NO VISIBLE CLEAR LANDSAT SUPPORT',
           finding='; '.join(f"{r['date']}: {100*r['clear_fraction']:.0f}% clear, {100*r['water_fraction_clear_only']:.0f}% of clear support labeled water" for r in clear) or 'This arm/cutoff supplies no clear candidate Landsat labels.',
           missing='Date mismatch, vegetation occlusion and classification errors prevent a validated candidate-to-flooded-area conversion.'),
      dict(question='Can a common scene shift explain the radar signal?',status='UNRESOLVED RADIOMETRIC / ENVIRONMENTAL MIXTURE' if diagnostic else 'NOT TESTABLE WITH VISIBLE L-BAND DATA',
           finding='Built/bare reference proxies also change; compare the displayed uncorrected local measurement with both offset sensitivity calculations.' if diagnostic else 'No NISAR reference-area comparison is exposed in this arm.',
           missing='Invariant targets, per-acquisition calibration/QA and matched field soil/water observations.'),
      dict(question='Does the floodplain affect this river sensor?',status='HYDRAULIC CONNECTION UNVERIFIED',finding='Geographic proximity is not outlet flow or travel-time evidence.',
           missing='Wetland outlet discharge, routing/travel time and paired outlet/river oxygen and DOC.')]
    plan=[dict(purpose='Distinguish water from soil/vegetation/radiometric explanations',where=dict(latitude=area['lat'],longitude=area['lon'],support_m=100),
               measurement='Retrieve a dated, georeferenced archived wet/dry/depth and canopy observation matching the studied interval; for a future repeat collect paired water-depth, soil-moisture and canopy observations at this fixed block.',
               why='This block has no validated radar-to-water label. NISAR adds a local HH/HV question in C, but not proof that this is the best place to sample.',
               basis='Fixed existing location and visible measurement gap; no optimal placement or validated decision improvement'),
          dict(purpose='Separate shared radiometry from environmental change',where='Stable reference targets spanning the scene; exact sites not established',measurement='Check invariant radiometric targets and full acquisition QA, alongside moisture observations. Built/bare land cover alone is insufficient.',basis='Shared reference-proxy shifts' if diagnostic else 'General calibration requirement; no L-band comparison in this arm'),
          dict(purpose='Connect landscape exposure to oxygen',where='The actual wetland outlet and receiving reach; hydraulic route not established',measurement='Measure outlet discharge, DOC bioavailability and subdaily oxygen upstream/downstream, with travel-time evidence.',basis='Missing causal pathway; geographic distance is insufficient')]
    return dict(arm=arm,arm_name=ARMS[arm],location=location,name=area['name'],latitude=area['lat'],longitude=area['lon'],
                fixed_anchor_utc=acquired,anchor_caution='Original NISAR-derived schedule held fixed in all arms. Recorded observation times, not historical availability; no forecast test.',
                field=field,conventional=conventional,nisar=nisar,diagnostic=diagnostic,hypotheses=hypotheses,measurement_plan=plan,
                constrained_oxygen_parameters=[],quantitative_flood_constraint=None,oxygen_uncertainty_reduction_demonstrated=False,
                selection_caution='The fixed 26-location set was originally selected using radar candidates plus monitoring contexts. This is not a sensor-blind test population or a placement-benefit validation.',
                verdict='SUPPORTIVE surface-change evidence; oxygen benefit CURRENTLY UNPROVEN',
                interpretation='No area, depth, carbon or oxygen distribution changes merely because this evidence arm changes.')


def numeric_delta(a,b):
    """Largest absolute difference over numeric leaves, preserving structure and avoiding strings/bools."""
    if isinstance(a,dict):
        if a.keys()!=b.keys():raise ValueError('Output keys differ')
        return max([numeric_delta(a[k],b[k]) for k in a] or [0.])
    if isinstance(a,list):
        if len(a)!=len(b):raise ValueError('Output shapes differ')
        return max([numeric_delta(x,y) for x,y in zip(a,b)] or [0.])
    if isinstance(a,(int,float)) and not isinstance(a,bool):return abs(a-b)
    if a!=b:raise ValueError('Nonnumeric output differs')
    return 0.
