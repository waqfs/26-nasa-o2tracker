"""Execute the frozen time-forward, spatially separated final evaluation."""
import json,hashlib
from pathlib import Path
from datetime import datetime
import numpy as np
import rasterio
from rasterio.warp import reproject,Resampling
from scipy.optimize import minimize
from scipy.special import expit
from canopy_pulse.comparison import ROOT,SHAPE,TRANSFORM,CRS,subset,write
from canopy_pulse.science import block_power,power_db
from canopy_pulse.raster import read_cogs,MASK_CONVENTION,sha256
out=ROOT/'outputs/validation';raw=ROOT/'data/validation'
protocol_bytes=(raw/'final_protocol.json').read_bytes()
protocol=json.loads(protocol_bytes)
catalog=json.loads((raw/'dea_water_stac.json').read_text())['features']
manifest=[];labels={};label_times={}
for date in ['2026-08-24','2026-10-11']:
    destination=raw/f'dea_final_{date}.tif'
    items=[f for f in catalog if f['properties']['datetime'].startswith(date)]
    mosaic=np.full(SHAPE,np.nan,dtype='float32')
    for item in items:
        item['assets']['water']['href']=item['assets']['water']['href'].replace('s3://dea-public-data/','https://dea-public-data.s3.ap-southeast-2.amazonaws.com/')
        if not destination.exists():
            a=subset(item,'water');keep=np.isin(a,[0,128]);mosaic[keep]=a[keep]
        manifest.append(dict(item=item['id'],time=item['properties']['datetime'],created=item['properties'].get('created'),url=item['assets']['water']['href']))
    if not destination.exists():write(destination,mosaic)
    with rasterio.open(destination) as ds:labels[date]=ds.read(1)
    label_times[date]=min(f['properties']['datetime'] for f in items)
    manifest.append(dict(path=str(destination.relative_to(ROOT)),sha256=sha256(destination)))
(raw/'final_reference_manifest.json').write_text(json.dumps(manifest,indent=2))
height,width=SHAPE[0]//5*5,SHAPE[1]//5*5
shape100=(height//5,width//5)
def fraction(a):return a[:height,:width].reshape(shape100[0],5,shape100[1],5).mean((1,3))
jobs=json.loads((ROOT/'data/acquisition/jobs.json').read_text())
req=json.loads((ROOT/'data/acquisition/request.json').read_text())
feature_epochs=[];features=[];eligible=[];targets=[]
for ndate,sdate,odate,ldate in [('2026-08-23','20260821','20260823','2026-08-24'),('2026-10-10','20261008','20261007','2026-10-11')]:
    acq=next(a for a in req['acquisitions'] if a['record']['start'].startswith(ndate))
    assert datetime.fromisoformat(acq['record']['start'].replace('Z','+00:00'))<datetime.fromisoformat(label_times[ldate].replace('Z','+00:00'))
    layers=[];supports=[]
    for band in ['vv','vh']:
        with rasterio.open(ROOT/f'outputs/comparison/sentinel1rtc_{sdate}_{band}.tif') as ds:a=ds.read(1)
        b,c=block_power(a[:height,:width],np.isfinite(a[:height,:width])&(a[:height,:width]>0),5)
        layers.append(power_db(b));supports.append(c>=.8)
    with rasterio.open(ROOT/f'outputs/comparison/sentinel2_{odate}_scl.tif') as ds:optical=ds.read(1)
    layers.append(fraction(optical==6));supports.append(fraction(np.isin(optical,[4,5,6]))>=.8)
    for pol in ['HHHH','HVHV']:
        paths={layer:ROOT/jobs[acq['concept_id']+'_'+layer]['file']['path'] for layer in [pol,'mask','numberOfLooks']}
        layer=read_cogs(paths[pol],paths['mask'],paths['numberOfLooks'],MASK_CONVENTION)
        destination=np.full(SHAPE,np.nan,dtype='float32')
        reproject(np.where(layer.valid,layer.power,np.nan),destination,src_transform=layer.transform,src_crs=layer.crs,src_nodata=np.nan,dst_transform=TRANSFORM,dst_crs=CRS,dst_nodata=np.nan,resampling=Resampling.average)
        b,c=block_power(destination[:height,:width],np.isfinite(destination[:height,:width])&(destination[:height,:width]>0),5)
        layers.append(power_db(b));supports.append(c>=.8)
    feature_epochs.append(dict(NISAR=acq['record']['start'],Sentinel1=sdate,Sentinel2=odate,label=label_times[ldate]))
    target=labels[ldate];positive=fraction(target==128)>=.6;negative=fraction(target==0)>=.9
    x=np.stack(layers,axis=-1)
    eligible.append(np.logical_and.reduce(supports)&np.isfinite(x).all(2)&(fraction(np.isfinite(target))>=.9)&(positive|negative))
    features.append(x);targets.append(positive)
rows,cols=np.indices(shape100);eastings=TRANSFORM.c+(cols+.5)*100
midpoint=TRANSFORM.c+width*20/2
training=eligible[0]&(eastings<midpoint-500)
testing=eligible[1]&(eastings>midpoint+500)
ytrain=targets[0][training];ytest=targets[1][testing]
result=dict(protocol_sha256=hashlib.sha256(protocol_bytes).hexdigest(),protocol=protocol,epochs=feature_epochs,
            reference_clear_grid_cells={day:int(np.isfinite(a).sum()) for day,a in labels.items()},training=dict(n=int(training.sum()),positive=int(ytrain.sum())),testing=dict(n=int(testing.sum()),positive=int(ytest.sum())),
            verdict='INCONCLUSIVE',interpretation='Predefined chronological and geographic holdout within one previously investigated watering season. Historical input availability remains unverified. Surface-water labels only.')
if min(ytrain.sum(),(~ytrain).sum(),ytest.sum(),(~ytest).sum())==0:
    result['reason']='No eligible classes under the frozen protocol. The selected reference tiles have no clear wet/dry pixels on the study grid. No replacement date or split was selected.'
else:
    def fit_predict(bands):
        a=features[0][training][:,bands];b=features[1][testing][:,bands]
        mean=a.mean(0);std=np.maximum(a.std(0),.01);a=(a-mean)/std;b=(b-mean)/std
        weight=np.where(ytrain,.5/ytrain.sum(),.5/(~ytrain).sum())
        def objective(coef):
            score=a@coef[:-1]+coef[-1];error=weight*(expit(score)-ytrain)
            return weight@(np.logaddexp(0,score)-ytrain*score)+.01*(coef[:-1]@coef[:-1]),np.r_[a.T@error+.02*coef[:-1],error.sum()]
        fitted=minimize(objective,np.zeros(len(bands)+1),jac=True,method='L-BFGS-B')
        if not fitted.success:raise RuntimeError(fitted.message)
        return expit(b@fitted.x[:-1]+fitted.x[-1])
    scores=np.stack([fit_predict([0,1,2]),fit_predict([0,1,2,3,4])],axis=1)
    # Group tied scores for both weighted ROC AUC and AP.
    def metrics(score,weight):
        order=np.argsort(-score,kind='stable');v=score[order];ends=np.r_[np.flatnonzero(np.diff(v)),len(v)-1]
        positive=(weight[order]*ytest[order]).cumsum()[ends];negative=(weight[order]*(~ytest[order])).cumsum()[ends]
        if positive[-1]==0 or negative[-1]==0:return None
        recall=positive/positive[-1];precision=positive/(positive+negative)
        ap=np.diff(np.r_[0,recall])@precision
        tpr=np.r_[0,recall];fpr=np.r_[0,negative/negative[-1]]
        auc=np.trapezoid(tpr,fpr)
        return np.array([auc,ap])
    measured=[metrics(scores[:,i],np.ones(len(ytest))) for i in range(2)]
    tile=(rows[testing]//50)*100+cols[testing]//50
    unique,group=np.unique(tile,return_inverse=True);rng=np.random.default_rng(20261115);gains=[]
    for _ in range(2000):
        weights=rng.multinomial(len(unique),np.full(len(unique),1/len(unique)))[group]
        pair=[metrics(scores[:,i],weights) for i in range(2)]
        if all(m is not None for m in pair):gains.append(pair[1]-pair[0])
    intervals=np.percentile(gains,[2.5,97.5],axis=0)
    result.update(conventional=dict(zip(['roc_auc','average_precision'],measured[0])),extended=dict(zip(['roc_auc','average_precision'],measured[1])),
                  delta_95_intervals=dict(roc_auc=intervals[:,0].tolist(),average_precision=intervals[:,1].tolist()),bootstrap_valid=len(gains),
                  test_tiles=len(unique),positive_test_tiles=len(np.unique(tile[ytest])),test_prevalence=float(ytest.mean()))
    if np.all(intervals[0]>0):result['verdict']='PASS for the predefined surface-water ranking criterion only'
    np.savez_compressed(out/'final_forward_scores.npz',labels=ytest,scores=scores,row=rows[testing],col=cols[testing],tiles=tile)
(out/'final_forward_result.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
