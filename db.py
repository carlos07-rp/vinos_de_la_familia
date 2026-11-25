import sqlite3, json
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).parent
TABLES=('analisis','cata','almacenamiento','proceso','seguimiento','prediccion')
def connect(path=None):
    c=sqlite3.connect(path or ROOT/'data/finca.sqlite'); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c
def init(path=None):
    with connect(path) as c:
        c.execute('CREATE TABLE IF NOT EXISTS lotes (id INTEGER PRIMARY KEY, codigo TEXT UNIQUE NOT NULL, nombre TEXT NOT NULL, variedad TEXT, anada TEXT, etapa TEXT, fecha TEXT, datos TEXT NOT NULL)')
        for t in TABLES:
            c.execute(f'CREATE TABLE IF NOT EXISTS {t} (id INTEGER PRIMARY KEY, lote_id INTEGER NOT NULL REFERENCES lotes(id) ON DELETE CASCADE, fecha TEXT NOT NULL, datos TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS modelo (version TEXT PRIMARY KEY, fecha TEXT, datos TEXT)')
def rows(t, lote=None,path=None):
    assert t in (*TABLES,'lotes','modelo')
    with connect(path) as c:
        q=f'SELECT * FROM {t}'; args=()
        if lote is not None: q+=' WHERE lote_id=?'; args=(lote,)
        q+=' ORDER BY fecha DESC'; result=[]
        for r in c.execute(q,args):
            d=dict(r); payload=json.loads(d.pop('datos')); result.append({**payload,**d})
        return result
def save_lote(d, ident=None,path=None):
    if not d['codigo'].strip() or not d['nombre'].strip(): raise ValueError('Código y nombre son obligatorios.')
    v=tuple(d[k] for k in ('codigo','nombre','variedad','anada','etapa','fecha'))+(json.dumps(d,ensure_ascii=False),)
    with connect(path) as c:
        if ident:
            old=c.execute('SELECT etapa FROM lotes WHERE id=?',(ident,)).fetchone()
            c.execute('UPDATE lotes SET codigo=?,nombre=?,variedad=?,anada=?,etapa=?,fecha=?,datos=? WHERE id=?',v+(ident,))
            if old and old['etapa']!=d['etapa']: c.execute('INSERT INTO proceso(lote_id,fecha,datos) VALUES(?,?,?)',(ident,datetime.now().isoformat(),json.dumps({'evento':'Cambio de etapa','anterior':old['etapa'],'nueva':d['etapa']})))
            return ident
        return c.execute('INSERT INTO lotes(codigo,nombre,variedad,anada,etapa,fecha,datos) VALUES(?,?,?,?,?,?,?)',v).lastrowid
def save(t,lote,fecha,d,ident=None,path=None):
    assert t in TABLES
    with connect(path) as c:
        payload=json.dumps(d,ensure_ascii=False)
        if ident: c.execute(f'UPDATE {t} SET fecha=?,datos=? WHERE id=? AND lote_id=?',(fecha,payload,ident,lote)); return ident
        return c.execute(f'INSERT INTO {t}(lote_id,fecha,datos) VALUES(?,?,?)',(lote,fecha,payload)).lastrowid
def delete_lote(ident,path=None):
    with connect(path) as c: c.execute('DELETE FROM lotes WHERE id=?',(ident,))
def timeline(lote,path=None):
    return sorted([dict(r,tipo=t) for t in TABLES for r in rows(t,lote,path)],key=lambda r:r['fecha'],reverse=True)
def register_model(meta,path=None):
    with connect(path) as c: c.execute('INSERT OR REPLACE INTO modelo VALUES(?,?,?)',(meta['version'],meta['fecha'],json.dumps(meta,ensure_ascii=False)))
