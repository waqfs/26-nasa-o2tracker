"""Spatially held-out optical-label comparison. Optical transitions are an exposed-water proxy."""
from pathlib import Path
import json,numpy as np,rasterio
from scipy.special import expit
from scipy.optimize import minimize
from scipy.stats import rankdata
from pyproj import Transformer
import os
root=Path(os.environ.get('OXYGEN_WORKSPACE_ROOT','.'));out=root/'outputs/validation'
def read(path):
    with rasterio.open(path) as ds:return ds.read(1),ds.transform
features=[]
for band in ['vv','vh','HHHH','HVHV']:
    a,tr=read(root/f'outputs/real/matched100m_{band}_change_db.tif');features.append(a)
X=np.stack(features,axis=-1);h,w=X.shape[:2]
def fraction(a):return a[:h*5,:w*5].reshape(h,5,w,5).mean((1,3))
maps=[read(p)[0] for p in ['data/validation/prewatering_scl.tif','outputs/comparison/sentinel2_20260823_scl.tif','outputs/comparison/sentinel2_20260929_scl.tif']]
july,aug,sep=maps
dry=fraction(np.isin(aug,[4,5]))>=.8
def auc(y,s):
    n=int(y.sum());m=len(y)-n
    if min(n,m)==0:return None
    return float((rankdata(s)[y].sum()-n*(n+1)/2)/(n*m))

def spatial_interval(labels,scores,tiles,alpha=.05):
    """Paired tile bootstrap of fixed out-of-fold rankings (conditional on fitted models)."""
    unique,group=np.unique(tiles,return_inverse=True)
    wins=np.zeros((len(unique),len(unique)))
    for column,sign in [(0,-1),(2,1)]:
        positives=scores[labels,column]
        for g in range(len(unique)):
            negatives=np.sort(scores[(~labels)&(group==g),column])
            less=np.searchsorted(negatives,positives,side='left')
            equal_or_less=np.searchsorted(negatives,positives,side='right')
            wins[:,g]+=sign*np.bincount(group[labels],weights=(less+equal_or_less)/2,minlength=len(unique))
    rng=np.random.default_rng(123)
    weights=rng.multinomial(len(unique),np.full(len(unique),1/len(unique)),size=2000)
    pairs=(weights@np.bincount(group[labels],minlength=len(unique)))*(weights@np.bincount(group[~labels],minlength=len(unique)))
    good=pairs>0
    gains=np.sum((weights[good]@wins)*weights[good],axis=1)/pairs[good]
    return np.percentile(gains,[100*alpha/2,100*(1-alpha/2)]).tolist()
from canopy_pulse.validation_metrics import average_precision

def predict(a,y,b):
    mu=a.mean(0);sd=np.maximum(a.std(0),.01);a=(a-mu)/sd;b=(b-mu)/sd
    weight=np.where(y,.5/y.sum(),.5/(~y).sum())
    def objective(coef):
        score=a@coef[:-1]+coef[-1];err=weight*(expit(score)-y)
        loss=weight@(np.logaddexp(0,score)-y*score)+.01*np.dot(coef[:-1],coef[:-1])
        return loss,np.r_[a.T@err+.02*coef[:-1],err.sum()]
    opt=minimize(objective,np.zeros(a.shape[1]+1),jac=True,method='L-BFGS-B')
    if not opt.success:raise RuntimeError(opt.message)
    return expit(b@opt.x[:-1]+opt.x[-1])
rows,cols=np.indices((h,w));results=[]
for threshold in [.4,.6,.8]:
    yes=fraction(sep==6)>=threshold
    no=fraction(np.isin(sep,[4,5]))>=.9
    valid=dry&(yes|no)&np.isfinite(X).all(2)
    y=yes[valid];data=X[valid];tile=(rows[valid]//50)*100+cols[valid]//50
    # Geographic 5 km tile holdouts. Five interleaved folds; report only folds containing both classes.
    fold=(tile//100+2*(tile%100))%5
    preds=np.full((len(y),3),np.nan)
    if y.sum()>=2:
        for f in range(5):
            test=fold==f;train=~test
            if np.unique(y[train]).size<2 or not test.any():continue
            for k,bands in enumerate([[0,1],[2,3],[0,1,2,3]]):
                preds[test,k]=predict(data[train][:,bands],y[train],data[test][:,bands])
    ok=np.isfinite(preds).all(1)
    scores=[auc(y[ok],p[ok]) for p in preds.T]
    results.append(dict(sep_water_fraction=threshold,positive=int(y.sum()),negative=int((~y).sum()),positive_tiles=int(len(np.unique(tile[y]))),scored=int(ok.sum()),aucs_s1_nisar_both=scores,by_fold=[dict(fold=f,positive=int(y[fold==f].sum()),auc=[auc(y[ok&(fold==f)],p[ok&(fold==f)]) for p in preds.T]) for f in range(5)]))
    results[-1]['paired_tile_bootstrap_delta_interval']=spatial_interval(y[ok],preds[ok],tile[ok])
locs=json.loads(Path('outputs/validation/station_joins.json').read_text());proj=Transformer.from_crs(4283,32754,always_xy=True)
station=[]
for s in locs:
    x,y=proj.transform(s['lon'],s['lat']);col,row=~tr*(x,y);row,col=int(row)*5+2,int(col)*5+2
    station.append(dict(station=s['station'],scl_300m=[{'clear':int(np.isin(a[row-7:row+8,col-7:col+8],[4,5,6]).sum()),'water':int((a[row-7:row+8,col-7:col+8]==6).sum())} for a in maps]))
c=json.loads(Path('outputs/real/candidate_investigation_points.geojson').read_text())['features']
coords=Transformer.from_crs(4326,32754,always_xy=True)
controls=[]
for f in c:
    col,row=~tr*coords.transform(*f['geometry']['coordinates']);r,k=int(row)*5,int(col)*5
    controls.append([float(np.isin(a[r:r+5,k:k+5],[4,5]).mean()) for a in maps])
(out/'proxy_comparison.json').write_text(json.dumps(dict(benchmark=results,station_optical=station,candidate_land_fractions_jul_aug_sep=controls),indent=2))
print(results,station)

# Independent Landsat target. Include Sentinel-2 in the conventional predictors.
dry0=read('data/validation/dea_2026-08-23.tif')[0]
optical_features=[fraction(aug==6),fraction(sep==6)]
combined=np.concatenate([X,np.stack(optical_features,axis=-1)],axis=-1)
records=[]
for day in ['2026-09-24','2026-10-02']:
    target=read('data/validation/dea_'+day+'.tif')[0]
    for cutoff in [.4,.6,.8]:
        positive=fraction(target==128)>=cutoff
        negative=fraction(target==0)>=.9
        selected=(fraction(dry0==0)>=.8)&(fraction(np.isfinite(target))>=.9)&(positive|negative)&(fraction(np.isin(aug,[4,5,6]))>=.9)&(fraction(np.isin(sep,[4,5,6]))>=.9)&np.isfinite(X).all(2)
        y=positive[selected];features=combined[selected]
        tile=(rows[selected]//50)*100+cols[selected]//50
        fold=(tile//100+2*(tile%100))%5
        scores=np.full((len(y),3),np.nan)
        for f in range(5):
            test=fold==f;train=~test
            if np.unique(y[train]).size<2 or not test.any():continue
            for k,bands in enumerate([[0,1,4,5],[2,3],[0,1,4,5,2,3]]):
                scores[test,k]=predict(features[train][:,bands],y[train],features[test][:,bands])
        ok=np.isfinite(scores).all(1)
        # Sensitivity: inspect whether a single positive tile or spatial partition drives the selected result.
        sensitivity={}
        if cutoff==.8 and day=='2026-09-24':
            loo=[]
            for g in np.unique(tile[y]):
                keep=ok&(tile!=g)
                loo.append(auc(y[keep],scores[keep,2])-auc(y[keep],scores[keep,0]))
            sensitivity['drop_one_positive_tile_gain_range']=[min(loo),max(loo)]
            # Geographic buffer excludes training observations within 1 km of a held-out tile.
            from scipy.ndimage import distance_transform_edt
            buffered=scores.copy()
            for f in range(5):
                held=((rows//50+2*(cols//50))%5)==f
                train=(distance_transform_edt(~held)[selected]>10)&(fold!=f)
                test=fold==f
                for k,bands in [(0,[0,1,4,5]),(2,[0,1,4,5,2,3])]:
                    buffered[test,k]=predict(features[train][:,bands],y[train],features[test][:,bands])
            sensitivity['buffer_1km_auc']=[auc(y,buffered[:,k]) for k in [0,2]]
            sensitivity['buffer_1km_delta_interval']=spatial_interval(y,buffered,tile)
        # Apply the same separation audit to all six settings.
        from scipy.ndimage import distance_transform_edt
        buffered=scores.copy()
        training_counts=[]
        for f in range(5):
            held=((rows//50+2*(cols//50))%5)==f
            train=(distance_transform_edt(~held)[selected]>10)&(fold!=f)
            test=fold==f
            training_counts.append(dict(fold=f,training=int(train.sum()),training_positive=int(y[train].sum()),
                                        test=int(test.sum()),test_positive=int(y[test].sum())))
            for k,bands in [(0,[0,1,4,5]),(2,[0,1,4,5,2,3])]:
                buffered[test,k]=predict(features[train][:,bands],y[train],features[test][:,bands])
        np.savez_compressed(out/f"scores_{day}_{int(cutoff*100)}.npz",labels=y,scores=scores,buffered=buffered,
                            tiles=tile,fold=fold,row=rows[selected],col=cols[selected])
        sensitivity['all_fold_counts']=training_counts
        sensitivity['buffer_1km_auc']=[auc(y,buffered[:,k]) for k in [0,2]]
        sensitivity['buffer_1km_average_precision']=[average_precision(y,buffered[:,k]) for k in [0,2]]
        sensitivity['buffer_1km_delta_interval']=spatial_interval(y,buffered,tile)
        sensitivity['buffer_1km_delta_interval_nine_comparisons']=spatial_interval(y,buffered,tile,alpha=.05/9)
        sensitivity['delta_interval_nine_comparisons']=spatial_interval(y,scores,tile,alpha=.05/9)
        records.append(dict(sensitivity=sensitivity,date=day,water_fraction=cutoff,positive=int(y.sum()),negative=int((~y).sum()),positive_tiles=int(len(np.unique(tile[y]))),n_scored=int(ok.sum()),auc=[auc(y[ok],s[ok]) for s in scores.T],average_precision=[average_precision(y[ok],s[ok]) for s in scores.T],delta_interval=spatial_interval(y[ok],scores[ok],tile[ok])))
(out/'landsat_test.json').write_text(json.dumps(records,indent=2))
