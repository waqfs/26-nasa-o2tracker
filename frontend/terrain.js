const $=id=>document.getElementById(id);
try {
 const mesh=await (await fetch('/data/derived/signal_mesh.json')).json();
 const terrain=await (await fetch('/data/derived/terrain.json')).json();
 const canvas=$('signal-canvas'),ctx=canvas.getContext('2d');let vertices=[],drag=null,moved=false;
 function draw(){
  const a=mesh.layers[$('mesh-layer').value],rows=a.length,cols=a[0].length;
  const showTerrain=$('mesh-surface').value==='terrain';
  const absolutePower=/^(HH|HV)_/.test($('mesh-layer').value);
  
  const angle=Number($('mesh-rotation').value)*Math.PI/180,tilt=Number($('mesh-tilt').value)*Math.PI/180,scale=Number($('mesh-height').value);
  const cs=Math.cos(angle),sn=Math.sin(angle),ct=Math.cos(tilt),st=Math.sin(tilt);vertices=[];
  ctx.fillStyle='#161616';ctx.fillRect(0,0,1100,600);
  function project(row,col){const x=(col/(cols-1)-.5)*650,y=(row/(rows-1)-.5)*650,z=showTerrain?terrain.values[row][col]*scale*1.5:(absolutePower?Math.max(-35,Math.min(5,a[row][col]))+20:Math.max(-8,Math.min(8,a[row][col])))*scale*12;
   const rx=x*cs-y*sn,ry=x*sn+y*cs;return {x:550+rx,y:300+ry*st-z*ct,depth:ry*ct+z*st,row,col,value:a[row][col]};}
  const cells=[];
  for(let row=0;row<rows;row++){vertices[row]=[];for(let col=0;col<cols;col++)vertices[row][col]=project(row,col)}
  const flat=vertices.flat(),xs=flat.map(p=>p.x),ys=flat.map(p=>p.y),xmin=Math.min(...xs),xmax=Math.max(...xs),ymin=Math.min(...ys),ymax=Math.max(...ys);
  const fit=Math.min(980/(xmax-xmin),470/(ymax-ymin));
  for(const p of flat){p.x=550+(p.x-(xmin+xmax)/2)*fit;p.y=300+(p.y-(ymin+ymax)/2)*fit;}
  for(let row=0;row<rows-1;row++)for(let col=0;col<cols-1;col++){
   if(!mesh.valid[row][col]||!mesh.valid[row+1][col]||!mesh.valid[row][col+1]||!mesh.valid[row+1][col+1])continue;
   const p=[vertices[row][col],vertices[row][col+1],vertices[row+1][col+1],vertices[row+1][col]];
   cells.push({p,depth:p.reduce((s,v)=>s+v.depth,0)/4,value:p.reduce((s,v)=>s+v.value,0)/4});
  }
  cells.sort((a,b)=>a.depth-b.depth);
  for(const cell of cells){const mapped=absolutePower?(cell.value+12.5)/2.5:cell.value;const v=Math.max(-5,Math.min(5,mapped)),t=Math.abs(v)/5;
   ctx.fillStyle=v<0?`rgb(${Math.round(215-180*t)},${Math.round(229-125*t)},${Math.round(232-70*t)})`:`rgb(${Math.round(215+20*t)},${Math.round(229-170*t)},${Math.round(232-180*t)})`;
   ctx.beginPath();cell.p.forEach((p,i)=>i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y));ctx.closePath();ctx.fill();
  }
  const selectedRow=Number(canvas.dataset.blockRow)/4,selectedCol=Number(canvas.dataset.blockCol)/4;
  if(canvas.dataset.blockRow!==undefined){
   const row=Math.max(0,Math.min(rows-1,Math.round(selectedRow))),col=Math.max(0,Math.min(cols-1,Math.round(selectedCol)));
   const point=vertices[row][col];ctx.beginPath();ctx.arc(point.x,point.y,8,0,Math.PI*2);ctx.strokeStyle='#fff2a6';ctx.lineWidth=3;ctx.stroke();
   ctx.fillStyle='#fff2a6';ctx.font='12px Arial';ctx.fillText('Selected area (~400 m mesh)',point.x+12,point.y-8);
  }
  if(canvas.dataset.stationRow!==undefined){
   const row=Math.max(0,Math.min(rows-1,Math.round(Number(canvas.dataset.stationRow)/4))),col=Math.max(0,Math.min(cols-1,Math.round(Number(canvas.dataset.stationCol)/4)));
   const point=vertices[row][col];ctx.beginPath();ctx.arc(point.x,point.y,7,0,Math.PI*2);ctx.fillStyle='#83c9ee';ctx.fill();ctx.font='12px Arial';ctx.fillText(canvas.dataset.stationId+' (approx.)',point.x+10,point.y+16);
  }
  ctx.fillStyle='#eeeeee';ctx.font='15px Arial';ctx.fillText($('mesh-layer').selectedOptions[0].text+' · dB',24,30);
  ctx.font='12px Arial';ctx.fillText(absolutePower?'Observed power: blue −25 | neutral −12.5 | red 0 dB · color range clipped':'Derived change: blue −5 | neutral 0 | red +5 dB · color range clipped',24,570);
  ctx.fillText(showTerrain?'Elevation: Copernicus GLO-30 DSM, metres EGM2008. Relief visually exaggerated.':(absolutePower?'Signal height: power relative to -20 dB, visually exaggerated.':'Signal height: radar change in dB, visually exaggerated.'),24,590);
  for(const [row,col,text] of [[0,0,'NW'],[0,cols-1,'NE'],[rows-1,0,'SW'],[rows-1,cols-1,'SE']]){const p=vertices[row][col];ctx.fillText(text,p.x,p.y)}
 }
 ['mesh-surface','mesh-layer','mesh-rotation','mesh-tilt','mesh-height'].forEach(id=>$(id).addEventListener('input',draw));
 $('mesh-reset').addEventListener('click',()=>{$('mesh-rotation').value=-25;$('mesh-tilt').value=50;$('mesh-height').value=1;draw()});
 canvas.addEventListener('pointerdown',e=>{drag={x:e.clientX,y:e.clientY,angle:Number($('mesh-rotation').value),tilt:Number($('mesh-tilt').value)};moved=false;canvas.setPointerCapture(e.pointerId)});
 canvas.addEventListener('pointermove',e=>{if(!drag)return;if(Math.abs(e.clientX-drag.x)+Math.abs(e.clientY-drag.y)>4)moved=true;$('mesh-rotation').value=Math.max(-180,Math.min(180,drag.angle+(e.clientX-drag.x)*.4));$('mesh-tilt').value=Math.max(15,Math.min(85,drag.tilt+(e.clientY-drag.y)*.2));draw()});
 canvas.addEventListener('pointerup',e=>{drag=null;if(moved)return;const bounds=canvas.getBoundingClientRect(),x=(e.clientX-bounds.left)*1100/bounds.width,y=(e.clientY-bounds.top)*600/bounds.height;let best=null,d=144;
  for(const row of vertices)for(const p of row)if(mesh.valid[p.row][p.col]){const next=(p.x-x)**2+(p.y-y)**2;if(next<d){d=next;best=p}}
  $('mesh-readout').textContent=best?`${$('mesh-layer').selectedOptions[0].text}: ${best.value.toFixed(3)} dB · UTM 54S easting ${mesh.sample_centers_origin_utm[0]+best.col*400} m, northing ${mesh.sample_centers_origin_utm[1]-best.row*400} m · surface elevation ${terrain.values[best.row][best.col].toFixed(1)} m EGM2008 · sampled 100 m block · environmental cause unvalidated.`:'Click closer to a displayed vertex.';
 });window.addEventListener('oxygen-location-selected',draw);canvas.addEventListener('pointercancel',()=>{drag=null});draw();
} catch(error) {document.getElementById('mesh-readout').textContent=error.message;}
