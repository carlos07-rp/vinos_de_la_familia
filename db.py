import sqlite3, json
from pathlib import Path
from datetime import datetime, timedelta, timezone
ROOT=Path(__file__).parent
TABLES=('analisis','cata','almacenamiento','proceso','seguimiento','prediccion')
def connect(path=None):
    c=sqlite3.connect(path or ROOT/'data/finca.sqlite'); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c
def init(path=None):
    with connect(path) as c:
        c.execute('CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TEXT NOT NULL, activo INTEGER NOT NULL DEFAULT 1)')
        c.execute('CREATE TABLE IF NOT EXISTS sesiones (token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE, created_at TEXT NOT NULL, expires_at TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS lotes (id INTEGER PRIMARY KEY, codigo TEXT UNIQUE NOT NULL, nombre TEXT NOT NULL, variedad TEXT, anada TEXT, etapa TEXT, fecha TEXT, datos TEXT NOT NULL)')
        for t in TABLES:
            c.execute(f'CREATE TABLE IF NOT EXISTS {t} (id INTEGER PRIMARY KEY, lote_id INTEGER NOT NULL REFERENCES lotes(id) ON DELETE CASCADE, fecha TEXT NOT NULL, datos TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS modelo (version TEXT PRIMARY KEY, fecha TEXT, datos TEXT)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_lotes_etapa ON lotes(etapa)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_lotes_codigo ON lotes(codigo)')
        for t in TABLES:
            c.execute(f'CREATE INDEX IF NOT EXISTS idx_{t}_lote_fecha ON {t}(lote_id, fecha)')
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

def password_hash(password):
    import hashlib, secrets
    salt=secrets.token_hex(16)
    digest=hashlib.pbkdf2_hmac('sha256',password.encode('utf-8'),salt.encode('ascii'),200_000).hex()
    return f'{salt}${digest}'

def has_users(path=None):
    with connect(path) as c:
        return c.execute('SELECT 1 FROM usuarios WHERE activo=1 LIMIT 1').fetchone() is not None

def create_user(username,password,path=None):
    username=username.strip()
    if len(username)<3 or len(username)>80: raise ValueError('El usuario debe tener entre 3 y 80 caracteres.')
    if len(password)<12: raise ValueError('La contraseña debe tener al menos 12 caracteres.')
    with connect(path) as c:
        c.execute('INSERT INTO usuarios(username,password_hash,created_at,activo) VALUES(?,?,?,1)',
                  (username,password_hash(password),datetime.now(timezone.utc).isoformat()))

def verify_user(username,password,path=None):
    import hashlib, hmac
    with connect(path) as c:
        row=c.execute('SELECT password_hash,activo FROM usuarios WHERE username=?',(username,)).fetchone()
    if not row or not row['activo']: return False
    try:
        salt,digest=row['password_hash'].split('$',1)
        candidate=hashlib.pbkdf2_hmac('sha256',password.encode('utf-8'),salt.encode('ascii'),200_000).hex()
        return hmac.compare_digest(candidate,digest)
    except (ValueError,AttributeError): return False

def create_session(username,token,path=None):
    import hashlib
    with connect(path) as c:
        row=c.execute('SELECT id FROM usuarios WHERE username=? AND activo=1',(username,)).fetchone()
        if not row: return False
        now=datetime.now(timezone.utc)
        c.execute('DELETE FROM sesiones WHERE expires_at<=?',(now.isoformat(),))
        c.execute('INSERT INTO sesiones(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)',
                  (hashlib.sha256(token.encode('utf-8')).hexdigest(),row['id'],now.isoformat(),(now+timedelta(hours=12)).isoformat()))
        return True

def session_user(token,path=None):
    import hashlib
    if not token: return None
    now=datetime.now(timezone.utc).isoformat()
    with connect(path) as c:
        row=c.execute('SELECT u.username FROM sesiones s JOIN usuarios u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>? AND u.activo=1',
                      (hashlib.sha256(token.encode('utf-8')).hexdigest(),now)).fetchone()
        return row['username'] if row else None

def revoke_session(token,path=None):
    import hashlib
    if not token: return
    with connect(path) as c:
        c.execute('DELETE FROM sesiones WHERE token_hash=?',(hashlib.sha256(token.encode('utf-8')).hexdigest(),))
