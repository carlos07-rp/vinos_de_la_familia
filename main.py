from pathlib import Path
from datetime import datetime
import os, io, json, sqlite3, secrets
import pandas as pd, numpy as np, joblib
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from plotly.offline import get_plotlyjs
import db, ml, reports
ROOT=Path(__file__).parent
DATA=Path(os.environ.get('VINTALYTICS_DATA',ROOT/'data')); DATA.mkdir(parents=True,exist_ok=True)
if not (DATA/'academico.csv').exists(): (DATA/'academico.csv').write_bytes((ROOT/'data/academico.csv').read_bytes())
# All persistent records share the configured storage directory.
db.ROOT=DATA.parent if DATA.name=='data' else db.ROOT
original=db.connect
def connection(path=None): return original(path or DATA/'finca.sqlite')
db.connect=connection; db.init()
app=FastAPI(title='VINTALYTICS'); app.mount('/static',StaticFiles(directory=ROOT/'frontend'),name='static')
@app.middleware('http')
async def protect(request:Request,call_next):
    password=os.getenv('VINTALYTICS_PASSWORD'); user=os.getenv('VINTALYTICS_USER','admin')
    if password:
        import base64
        try: valid=secrets.compare_digest(base64.b64decode(request.headers.get('authorization','').split()[1]),f'{user}:{password}'.encode())
        except Exception: valid=False
        if not valid:return Response('Autenticación requerida',401,headers={'WWW-Authenticate':'Basic realm="VINTALYTICS"'})
    return await call_next(request)
@app.exception_handler(ValueError)
async def invalid(req,e):return JSONResponse({'detail':str(e)},422)
@app.exception_handler(sqlite3.IntegrityError)
async def conflict(req,e):return JSONResponse({'detail':'Código duplicado o lote inexistente.'},409)
def records(t,l=None):return db.rows(t,l)
def lot(i):
    r=next((x for x in records('lotes') if x['id']==i),None)
    if not r:raise HTTPException(404,'Lote no encontrado')
    return r
def academic():return pd.read_csv(DATA/'academico.csv')
def serial(d):return json.loads(d.to_json(orient='records'))
def bundle():
    p=DATA/'modelos.joblib'
    if not p.exists():raise HTTPException(409,'Entrena los modelos primero.')
    return joblib.load(p)
@app.get('/')
def home():return FileResponse(ROOT/'frontend/index.html')
@app.get('/plotly.js')
def plotly():return Response(get_plotlyjs(),media_type='application/javascript')
@app.get('/api/lotes')
def lots():return records('lotes')
@app.post('/api/lotes')
def create(d:dict):return {'id':save_lot(d)}
@app.put('/api/lotes/{i}')
def edit(i:int,d:dict):lot(i);return {'id':save_lot(d,i)}
def save_lot(d,i=None):
    for k in ['codigo','nombre','variedad','anada','etapa','fecha']:d[k]=str(d.get(k,''))
    if d['etapa'] not in ['Elaboración','Fermentación','Crianza','Almacenamiento','Finalizado']:raise ValueError('Etapa inválida')
    return db.save_lote(d,i)
@app.delete('/api/lotes/{i}')
def delete(i:int):lot(i);db.delete_lote(i);return {'ok':True}
@app.get('/api/registros/{t}')
def get_records(t:str,lote_id:int|None=None):
    if t not in db.TABLES:raise HTTPException(404)
    return records(t,lote_id)
@app.post('/api/registros/{t}')
def create_record(t:str,d:dict):return save_record(t,d)
@app.put('/api/registros/{t}/{i}')
def edit_record(t:str,i:int,d:dict):return save_record(t,d,i)
def save_record(t,d,i=None):
    if t not in db.TABLES or t=='prediccion':raise HTTPException(404)
    l=int(d.pop('lote_id'));lot(l);date=d.pop('fecha');datetime.fromisoformat(date)
    if i and not any(r['id']==i for r in records(t,l)):raise HTTPException(404)
    if t=='analisis':
        for k in ml.FEATURES+['acidez_total_medida','glucosa','fructosa','malico','lactico']:
            if k in d and d[k] not in ('',None):
                d[k]=float(d[k]);
                if not np.isfinite(d[k]) or d[k]<0:raise ValueError('Medición inválida: '+k)
            else:d.pop(k,None)
    return {'id':db.save(t,l,date,d,i)}
@app.get('/api/historial/{i}')
def history(i:int):lot(i);return db.timeline(i)
@app.get('/api/dataset')
def dataset(page:int=0):
    d=academic();return {'total':len(d),'columns':list(d.columns),'rows':serial(d.iloc[max(page,0)*50:max(page,0)*50+50]),'clean':len(ml.clean(d)),'stats':serial(d.describe().T.reset_index())}
@app.post('/api/dataset')
async def upload(request:Request):
    d=pd.read_csv(io.BytesIO(await request.body())); c=ml.clean(d)
    if len(c)<20:raise ValueError('Dataset insuficiente')
    d.to_csv(DATA/'academico.csv',index=False);(DATA/'modelos.joblib').unlink(missing_ok=True);return {'total':len(d)}
@app.get('/api/modelos')
def models():return {'actual':bundle()['meta'] if (DATA/'modelos.joblib').exists() else None,'historial':records('modelo')}
@app.post('/api/entrenar')
def train():
    b=ml.train(academic(),DATA/'modelos.joblib');db.register_model(b['meta']);return b['meta']
@app.post('/api/predecir')
def predict(d:dict):
    b=bundle(); name=d.get('modelo',b['meta']['seleccion']); vals=d.get('variables',{});
    if name not in b['models'] or any(k not in vals or vals[k] in ('',None) for k in ml.FEATURES):raise ValueError('Completa las 11 variables y selecciona un modelo válido.')
    p,out,e=ml.predict(b,vals,name); r={'quality':p,'modelo':name,'version':b['meta']['version'],'variables':vals,'fuera_rango':out,'sensibilidad':e}
    if d.get('lote_id'):lot(int(d['lote_id']));db.save('prediccion',int(d['lote_id']),datetime.now().isoformat(),r)
    return r
@app.post('/api/explorar')
def explore(d:dict):
    frame=academic() if d.get('fuente')=='academico' else pd.DataFrame(records('analisis')); cols=d.get('variables',ml.FEATURES)
    if any(c not in ml.FEATURES or c not in frame for c in cols):raise ValueError('Variables no disponibles en esta fuente')
    x=frame[cols].apply(pd.to_numeric,errors='coerce'); return {'correlacion':json.loads(x.corr().to_json(orient='values')),'puntos':serial(ml.patterns(x,cols,int(d.get('k',3)))),'distribucion':x[cols[0]].dropna().tolist(),'rangos':{c:[float(x[c].min()),float(x[c].max())] for c in cols}}
@app.get('/api/reporte/{i}/{fmt}')
def report(i:int,fmt:str):
    l=lot(i)
    if fmt=='pdf':data=reports.pdf(l);mime='application/pdf'
    elif fmt=='xlsx':data=reports.excel(l);mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    elif fmt=='csv':data=pd.DataFrame(db.timeline(i)).to_csv(index=False).encode('utf-8-sig');mime='text/csv'
    else:raise HTTPException(404)
    return Response(data,media_type=mime,headers={'Content-Disposition':f'attachment; filename="lote-{i}.{fmt}"'})
