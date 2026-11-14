"""Finite-carbon floodplain/river experiment. Published bounds, explicit scenario hydrology."""
from dataclasses import dataclass, asdict
import math
import numpy as np
from .settings import read_json
from .models import freshwater_equilibrium

RATIO = 32 / 12  # CH2O + O2 -> CO2 + H2O; kg O2 per kg carbon oxidized

@dataclass(frozen=True)
class FloodExperiment:
    area_ha: float = 100
    depth_m: float = .5
    exchange_per_day: float = .1
    river_flow_m3_s: float = 100
    river_volume_ml: float = 5000
    connected_fraction: float = .5
    hydrology_spread: float = .5
    upstream_oxygen_mg_l: float = 9
    temperature_c: float | None = None
    days: float = 14
    seed: int = 20261115
    samples: int = 256


def parameter_bounds(config):
    d = asdict(config)
    for k, v in d.items():
        if v is not None and not math.isfinite(v):
            raise ValueError('Inputs must be finite')
    limits = {'area_ha':(1,2000),'depth_m':(.1,3),'exchange_per_day':(0,1),
              'river_flow_m3_s':(1,1000),'river_volume_ml':(100,50000),
              'connected_fraction':(0,1),'hydrology_spread':(0,.9),'upstream_oxygen_mg_l':(0,15),
              'days':(1,30),'seed':(0,2**32-1),'samples':(64,1024)}
    for name,(low,high) in limits.items():
        if not low <= d[name] <= high:
            raise ValueError(f'Unsupported {name}')
    if config.temperature_c is not None and not 10 <= config.temperature_c <= 25:
        raise ValueError('Temperature outside published sensitivity domain 10-25 C')
    bounds = {k:(v['min'],v['max']) for k,v in read_json('provenance/flood_parameters.json')['parameters'].items()}
    if config.temperature_c is not None:
        bounds['temperature_c']=(config.temperature_c,config.temperature_c)
    # These are analyst/user scenario ranges, never presented as published hydrology.
    for name in ['area_ha','depth_m','exchange_per_day','river_flow_m3_s','river_volume_ml']:
        bounds[name]=(d[name]*(1-config.hydrology_spread),d[name]*(1+config.hydrology_spread))
    bounds['connected_fraction']=(max(0,config.connected_fraction-config.hydrology_spread/2),
                                  min(1,config.connected_fraction+config.hydrology_spread/2))
    if config.hydrology_spread == 0:
        bounds['connected_fraction']=(config.connected_fraction,config.connected_fraction)
    return bounds


def integrate(parameters, days=14, upstream=9, dt=.025, keep_paths=False):
    """Vectorized positive operator splitting; masses kg, volumes m3, time days.

    Each half-step advection solves the triangular two-box transfer exactly.
    Carbon reaction is first order, capped by available oxygen; no anaerobic loss.
    The ledger independently integrates boundary exchange for both constituents.
    """
    p={k:np.atleast_1d(np.asarray(v,dtype=float)) for k,v in parameters.items()}
    n=len(p['area_ha']); vf=p['area_ha']*10000*p['depth_m'];vr=p['river_volume_ml']*1000
    qf=vf*p['exchange_per_day'];qr=p['river_flow_m3_s']*86400;f=p['connected_fraction']
    a=qf/vf;b=(qr+f*qf)/vr;c=f*qf/vr
    t=p['temperature_c'];sat=freshwater_equilibrium(t)
    factor=.93255+.06745*np.exp(.2047*(t-20))
    # g/m2 * m2 * mg C/g * 1e-6 kg/mg
    fast=p['litter_fast_g_m2']*p['area_ha']*10000*p['yield_fast_mg_g']*factor*1e-6
    slow=p['litter_slow_g_m2']*p['area_ha']*10000*p['yield_slow_mg_g']*factor*1e-6
    initial_carbon=fast+slow
    kf=p['release_fast_per_day']*1.03**(t-20);ks=p['release_slow_per_day']*1.03**(t-20)
    kd=p['decay_per_day']*(-.2088+.0604*t);ka=p['reaeration_per_day']*1.024**(t-20)
    of=np.full(n,upstream)*vf/1000;orr=np.full(n,upstream)*vr/1000
    cf=np.zeros(n);cr=np.zeros(n)
    initial_o=of+orr;consumed=np.zeros(n);air=np.zeros(n);ocross=np.zeros(n);ccross=np.zeros(n)
    steps=math.ceil(days/dt);h=days/steps
    minimum=np.full(n,upstream);minimum_fp=minimum.copy()
    paths=[];fp_paths=[];times=[]

    def advect(mf,mr,source,step):
        xf=mf/vf-source;xr=mr/vr-source
        ea=np.exp(-a*step);eb=np.exp(-b*step)
        delta=b-a
        kernel=np.divide(ea-eb,delta,out=step*ea.copy(),where=np.abs(delta)>1e-9)
        newf=(source+xf*ea)*vf
        newr=(source+xr*eb+c*xf*kernel)*vr
        # Independent analytic integrals of deviations, including equal-rate limit.
        ia=np.divide(-np.expm1(-a*step),a,out=np.full(n,step),where=a!=0)
        ib=-np.expm1(-b*step)/b
        jk=np.divide(ia-ib,delta,out=np.zeros(n),where=np.abs(delta)>1e-9)
        equal=np.abs(delta)<=1e-9
        jk[equal]=np.divide(1-np.exp(-b[equal]*step)*(1+b[equal]*step),b[equal]**2)
        intf=source*step+xf*ia
        intr=source*step+xr*ib+c*xf*jk
        net=(qf+qr)*source*step-(1-f)*qf*intf-(qr+f*qf)*intr
        return newf,newr,net

    def release(step):
        nonlocal fast,slow,cf
        rf=fast*(-np.expm1(-kf*step));rs=slow*(-np.expm1(-ks*step))
        fast-=rf;slow-=rs;cf+=rf+rs

    def react(step):
        nonlocal cf,cr,of,orr,consumed
        decay=-np.expm1(-kd*step)
        uf=np.minimum(cf*decay,np.maximum(of,0)/RATIO)
        ur=np.minimum(cr*decay,np.maximum(orr,0)/RATIO)
        cf-=uf;cr-=ur;of-=RATIO*uf;orr-=RATIO*ur;consumed+=uf+ur

    max_o_error=0.;max_c_error=0.
    for i in range(steps+1):
        if i==0 or i%max(1,steps//140)==0 or i==steps:
            if keep_paths:paths.append(orr/vr*1000);fp_paths.append(of/vf*1000);times.append(i*h)
        if i==steps:break
        of,orr,net=advect(of,orr,upstream/1000,h/2);ocross+=net
        cf,cr,net=advect(cf,cr,0,h/2);ccross+=net
        release(h/2);react(h/2)
        newf=sat*vf/1000+(of-sat*vf/1000)*np.exp(-ka*h)
        newr=sat*vr/1000+(orr-sat*vr/1000)*np.exp(-ka*h)
        air+=(newf-of)+(newr-orr);of,orr=newf,newr
        react(h/2);release(h/2)
        of,orr,net=advect(of,orr,upstream/1000,h/2);ocross+=net
        cf,cr,net=advect(cf,cr,0,h/2);ccross+=net
        minimum=np.minimum(minimum,orr/vr*1000);minimum_fp=np.minimum(minimum_fp,of/vf*1000)
        max_o_error=max(max_o_error,float(np.max(np.abs(of+orr-(initial_o+ocross+air-RATIO*consumed)))))
        max_c_error=max(max_c_error,float(np.max(np.abs(fast+slow+cf+cr-(initial_carbon+ccross-consumed)))))
    if min(of.min(),orr.min(),cf.min(),cr.min()) < -1e-6:
        raise RuntimeError('Nonphysical negative mass')
    return dict(minimum=minimum,minimum_fp=minimum_fp,final=orr/vr*1000,
                potential_oxygen_kg=initial_carbon*RATIO,consumed_oxygen_kg=consumed*RATIO,
                carbon_remaining_kg=fast+slow+cf+cr,unreleased_carbon_kg=fast+slow,dissolved_carbon_kg=cf+cr,carbon_boundary_net_kg=ccross,
                initial_carbon_kg=initial_carbon,oxygen_balance_error_kg=max_o_error,carbon_balance_error_kg=max_c_error,
                time_days=times,paths=np.asarray(paths),fp_paths=np.asarray(fp_paths),
                floodplain_volume_m3=vf,floodplain_outflow_m3_s=qf/86400)


def experiment(config=FloodExperiment()):
    bounds=parameter_bounds(config);names=list(bounds);n=config.samples
    draws=np.random.default_rng(config.seed).random((2*n,len(names)))
    matrix=np.array([bounds[k][0]+draws[:,i]*(bounds[k][1]-bounds[k][0]) for i,k in enumerate(names)]).T
    a,b=matrix[:n],matrix[n:]
    parameters=lambda m:{k:m[:,i] for i,k in enumerate(names)}
    step=.025
    refinement_history=[]
    subset=parameters(matrix[:min(n,32)])
    for attempt in range(5):
        coarse=integrate(subset,config.days,config.upstream_oxygen_mg_l,dt=step)
        refined=integrate(subset,config.days,config.upstream_oxygen_mg_l,dt=step/2)
        refinement_error=float(np.max(np.abs(coarse['minimum']-refined['minimum'])))
        refinement_history.append(dict(step_days=step,half_step_days=step/2,max_minimum_river_difference_mg_l=refinement_error,passes=refinement_error<=.005))
        if refinement_error <= .005 or attempt==4:break
        step/=2
    base=integrate(parameters(matrix),config.days,config.upstream_oxygen_mg_l,dt=step,keep_paths=True)
    rankings=[]
    targets={'potential_oxygen_demand_kg':base['potential_oxygen_kg'],'minimum_river_oxygen_mg_l':base['minimum']}
    # Jansen total-order indices. Fixed RNG, independent-input design; finite-sample estimator can exceed one.
    estimates={key:[] for key in targets}
    bootstrap_indices=np.random.default_rng(config.seed+1).integers(0,n,size=(200,n))
    for i,name in enumerate(names):
        if bounds[name][0]==bounds[name][1]:
            for key in targets:estimates[key].append(dict(parameter=name,total_order=0.,bootstrap_95=[0.,0.]))
            continue
        mixed=a.copy();mixed[:,i]=b[:,i]
        trial=integrate(parameters(mixed),config.days,config.upstream_oxygen_mg_l,dt=step)
        for key,trialkey in [('potential_oxygen_demand_kg','potential_oxygen_kg'),('minimum_river_oxygen_mg_l','minimum')]:
            y=targets[key];variance=np.var(y,ddof=1)
            value=float(np.mean((y[:n]-trial[trialkey])**2)/(2*variance)) if variance>1e-12 else None
            numerator=(y[:n]-trial[trialkey])**2
            boot_variance=np.var(np.concatenate([y[:n][bootstrap_indices],y[n:][bootstrap_indices]],axis=1),axis=1,ddof=1)
            boot=np.divide(np.mean(numerator[bootstrap_indices],axis=1),2*boot_variance,out=np.full(200,np.nan),where=boot_variance>1e-12)
            interval=np.nanquantile(boot,[.025,.975]).tolist() if np.isfinite(boot).any() else None
            estimates[key].append(dict(parameter=name,total_order=value,bootstrap_95=interval))
    for values in estimates.values():values.sort(key=lambda v: v['total_order'] if v['total_order'] is not None else -1,reverse=True)
    quant=lambda x:np.quantile(x,[.05,.5,.95],axis=0).tolist()
    zero=parameters(matrix);zero['litter_fast_g_m2']=np.zeros(2*n);zero['litter_slow_g_m2']=np.zeros(2*n)
    control=integrate(zero,config.days,config.upstream_oxygen_mg_l,dt=step)
    dominant=estimates['minimum_river_oxygen_mg_l'][0]
    return dict(kind='EDUCATIONAL COUNTERFACTUAL / NO EVENT CALIBRATION',configuration=asdict(config),
                verdict='2026 causal attribution and dangerous oxygen depletion remain UNVERIFIED',
                independent_event_prediction=False,measurement_used_for_fit=False,
                bounds={k:dict(min=v[0],max=v[1],basis='Published sensitivity bounds' if k in read_json('provenance/flood_parameters.json')['parameters'] else 'User-selected scenario bounds') for k,v in bounds.items()},
                seed=config.seed,ensemble_members=2*n,quantile_levels=[.05,.5,.95],
                potential_oxygen_demand_kg=quant(base['potential_oxygen_kg']),
                oxygen_consumed_both_boxes_kg=quant(base['consumed_oxygen_kg']),
                minimum_river_oxygen_mg_l=quant(base['minimum']),minimum_floodplain_oxygen_mg_l=quant(base['minimum_fp']),
                paired_final_river_decrement_mg_l=quant(control['final']-base['final']),
                floodplain_volume_m3=quant(base['floodplain_volume_m3']),outlet_flow_m3_s=quant(base['floodplain_outflow_m3_s']),
                time_days=base['time_days'],river_oxygen_quantiles=quant(base['paths'].T),
                floodplain_oxygen_quantiles=quant(base['fp_paths'].T),sensitivity=estimates,
                most_informative_parameter=dominant['parameter'],
                sensitivity_caution='Jansen total-order estimates conditional on independent uniform inputs, chosen ranges and this simplified model. Not percentages, need not sum to one; finite-sample estimates can exceed one. Bootstrap intervals (200 paired row resamples) reflect Monte Carlo estimator variability only, not physical/model uncertainty. No event-specific information-gain result.',
                oxygen_balance_error_kg=base['oxygen_balance_error_kg'],carbon_balance_error_kg=base['carbon_balance_error_kg'],
                numerical_step_days=step,refinement_history=refinement_history,refinement_32_members_max_minimum_difference_mg_l=refinement_error,
                numerical_status='PASS limited refinement diagnostic' if refinement_error<=.005 else 'REFINEMENT WARNING: limited diagnostic exceeds 0.005 mg/L',
                observation_comparison='Simulated instantaneous paths/minima cannot be validated against daily station means. A wide assumed-input envelope or overlap is not causal evidence or validation.',
                missing=['Observed inundated area/depth/storage curve','Litter load and leachable/bioavailable DOC','Wetland outlet discharge and hydraulic connection','Upstream and outlet DO/DOC at subdaily resolution'],
                assumptions=['Simultaneous inundation at day zero; no growth or antecedent litter accumulation',
                 'Fixed-volume mixed floodplain and river boxes; identical assumed upstream oxygen for both',
                 'Constant input temperature and hydrology; no travel-time routing, algae, sediment demand or stratification',
                 'All released DOC treated as biodegradable on the sampled decay timescale: a strong structural assumption',
                 'Oxygen-limited carbon oxidation stops when oxygen is exhausted; remaining carbon retained',
                 'Potential stoichiometric demand is not actual depletion; downstream dilution and replenishment matter',
                 'No radar threshold-to-area conversion or field-gauge-to-depth conversion'])
