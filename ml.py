from pathlib import Path
from datetime import datetime,timezone
import hashlib, joblib, pandas as pd, numpy as np, sklearn
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score,precision_score,recall_score,f1_score,confusion_matrix
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
ROOT=Path(__file__).parent
FEATURES=['fixed_acidity','volatile_acidity','citric_acid','residual_sugar','chlorides','free_sulfur_dioxide','total_sulfur_dioxide','density','pH','sulphates','alcohol']
TARGET='quality'
def load_data(): return pd.read_csv(ROOT/'data/academico.csv')
def clean(df):
    missing=set(FEATURES+[TARGET])-set(df.columns)
    if missing: raise ValueError('Columnas faltantes: '+', '.join(sorted(missing)))
    d=df[FEATURES+[TARGET]].apply(pd.to_numeric,errors="coerce").replace([np.inf,-np.inf],np.nan).dropna()
    # Evita que perfiles idénticos aparezcan en ambos conjuntos; descarta etiquetas contradictorias.
    d=d.loc[d.groupby(FEATURES)[TARGET].transform('nunique').eq(1)].drop_duplicates(FEATURES)
    if not d[TARGET].mod(1).eq(0).all(): raise ValueError('quality debe contener puntuaciones enteras.')
    return d
def train(df, output=None):
    d=clean(df); X=d[FEATURES]; y=d[TARGET].astype(int)
    if y.nunique()<2 or y.value_counts().min()<5: raise ValueError('Se requieren al menos dos clases y cinco perfiles por clase.')
    Xtr,Xte,ytr,yte=train_test_split(X,y,test_size=.25,stratify=y,random_state=42)
    models={'Regresión logística':make_pipeline(StandardScaler(),LogisticRegression(max_iter=2000,class_weight='balanced',random_state=42)), 'Árbol de decisión':DecisionTreeClassifier(max_depth=8,class_weight='balanced',random_state=42),'Random Forest':RandomForestClassifier(n_estimators=150,min_samples_leaf=2,class_weight='balanced_subsample',random_state=42,n_jobs=2)}
    scores=[]; matrices={}; labels=sorted(y.unique().tolist())
    for name,m in models.items():
        m.fit(Xtr,ytr); p=m.predict(Xte); scores.append({'modelo':name,'accuracy':accuracy_score(yte,p),'precision_macro':precision_score(yte,p,average='macro',zero_division=0),'recall_macro':recall_score(yte,p,average='macro',zero_division=0),'f1_macro':f1_score(yte,p,average='macro',zero_division=0)}); matrices[name]=confusion_matrix(yte,p,labels=labels).tolist()
    best=max(scores,key=lambda x:x['f1_macro'])['modelo']; fingerprint=hashlib.sha256(df.to_csv(index=False).encode()).hexdigest(); version=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'-'+fingerprint[:8]
    meta={'version':version,'fecha':datetime.now(timezone.utc).isoformat(),'dataset_sha256':fingerprint,'registros_originales':len(df),'registros_limpios':len(d),'entrenamiento':len(Xtr),'prueba':len(Xte),'scores':scores,'matrices':matrices,'labels':labels,'seleccion':best,'sklearn':sklearn.__version__,'features':FEATURES,'rangos':{k:[float(Xtr[k].min()),float(Xtr[k].max())] for k in FEATURES}}
    bundle={'meta':meta,'models':models}; output=Path(output or ROOT/'data/modelos.joblib'); joblib.dump(bundle,output); return bundle
def predict(bundle,values,name):
    x=pd.DataFrame([{k:float(values[k]) for k in FEATURES}]);
    if not np.isfinite(x.to_numpy()).all(): raise ValueError('Todas las variables deben ser finitas.')
    m=bundle['models'][name]; result=int(m.predict(x)[0]); outside=[k for k in FEATURES if not bundle['meta']['rangos'][k][0]<=x.iloc[0][k]<=bundle['meta']['rangos'][k][1]]
    # Sensibilidad local: cambiar una variable al valor central del rango de entrenamiento.
    base=m.predict_proba(x)[0]; idx=list(m.classes_).index(result); effects=[]
    for k in FEATURES:
        z=x.copy(); z[k]=sum(bundle['meta']['rangos'][k])/2; effects.append({'variable':k,'cambio_probabilidad_modelo':float(base[idx]-m.predict_proba(z)[0][idx])})
    return result,outside,sorted(effects,key=lambda a:abs(a['cambio_probabilidad_modelo']),reverse=True)
def patterns(df,cols,k=3):
    d=df[cols].apply(pd.to_numeric,errors='coerce').dropna();
    if len(d)<max(k,3) or len(cols)<2: raise ValueError('Datos completos insuficientes.')
    z=StandardScaler().fit_transform(d); p=PCA(n_components=2).fit_transform(z); groups=KMeans(n_clusters=k,random_state=42,n_init=10).fit_predict(z); return pd.DataFrame({'PC1':p[:,0],'PC2':p[:,1],'Grupo':groups.astype(str)})
