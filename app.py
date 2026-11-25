from datetime import date
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

import db

st.set_page_config(page_title="VINTALYTICS", page_icon="V", layout="wide")
db.init_db()

COLORS = {"burgundy": "#722F37", "accent": "#9E243D", "gold": "#C6A56B", "dark": "#292929"}

st.markdown("""
<style>
.stApp { background:#F7F5F0; }
[data-testid="stSidebar"] { background:#FFFFFF; border-right:1px solid #E8E6E1; }
h1,h2,h3 { color:#292929; }
[data-testid="stMetric"] { background:#FFFFFF; border:1px solid #E8E6E1; border-radius:10px; padding:16px; }
.vino-card { background:#fff; border:1px solid #E8E6E1; border-left:4px solid #722F37; border-radius:8px; padding:14px; }
.stButton>button { border-radius:7px; }
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown("## VINTALYTICS")
st.sidebar.caption("Wine Intelligence & Winery Data System")
section = st.sidebar.radio(
    "Navegación",
    ["Dashboard", "Lotes", "Laboratorio", "Inteligencia", "Catas y observaciones",
     "Almacenamiento", "Seguimiento", "Datos y modelos", "Reportes"],
    label_visibility="collapsed",
)

def lots_df():
    return db.fetch_df("SELECT * FROM lotes ORDER BY creado_en DESC")

def lot_options():
    df = lots_df()
    if df.empty:
        return {}
    return {f"{row.codigo or 'SIN-CODIGO'} · {row.nombre}": int(row.id) for row in df.itertuples()}

def add_timeline(lote_id, tipo, titulo, descripcion, fecha=None):
    db.execute(
        "INSERT INTO seguimiento (lote_id, fecha, tipo, titulo, descripcion) VALUES (?, ?, ?, ?, ?)",
        (lote_id, fecha or str(date.today()), tipo, titulo, descripcion),
    )

def page_header(title, caption=None):
    st.title(title)
    if caption:
        st.caption(caption)
    st.divider()

if section == "Dashboard":
    page_header("Dashboard ejecutivo", "Visión general de la actividad de la finca")
    lotes = lots_df()
    analisis = db.fetch_df("SELECT * FROM analisis")
    catas = db.fetch_df("SELECT * FROM catas")

    total = len(lotes)
    en_proceso = int(lotes[lotes["etapa"].isin(["Elaboración", "Fermentación"])].shape[0]) if total else 0
    almacenados = int(lotes[lotes["etapa"].isin(["Crianza", "Almacenamiento"])].shape[0]) if total else 0
    finalizados = int(lotes[lotes["etapa"] == "Finalizado"].shape[0]) if total else 0
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Lotes registrados", total)
    m2.metric("En proceso", en_proceso)
    m3.metric("Crianza / almacenamiento", almacenados)
    m4.metric("Finalizados", finalizados)
    m5.metric("Análisis registrados", len(analisis))
    m6.metric("Último análisis", analisis["fecha"].max() if not analisis.empty else "Sin registros")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Distribución por etapa")
        if total:
            counts = lotes["etapa"].value_counts().reset_index()
            counts.columns = ["Etapa", "Cantidad"]
            fig = px.bar(counts, x="Etapa", y="Cantidad", color_discrete_sequence=[COLORS["burgundy"]])
            fig.update_layout(plot_bgcolor="white", paper_bgcolor="#F7F5F0")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aún no hay lotes registrados.")
    with c2:
        st.subheader("Distribución por variedad")
        if total:
            counts = lotes["variedad"].fillna("Sin especificar").value_counts().reset_index()
            counts.columns = ["Variedad", "Cantidad"]
            fig = px.pie(counts, names="Variedad", values="Cantidad", hole=.55,
                         color_discrete_sequence=[COLORS["burgundy"], COLORS["gold"], COLORS["accent"], "#8C8C8C"])
            fig.update_layout(paper_bgcolor="#F7F5F0")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aún no hay variedades registradas.")

    st.subheader("Actividad reciente")
    events = db.fetch_df("""
        SELECT s.fecha, s.tipo, s.titulo, s.descripcion, l.codigo, l.nombre
        FROM seguimiento s JOIN lotes l ON l.id=s.lote_id
        ORDER BY s.fecha DESC, s.id DESC LIMIT 10
    """)
    if events.empty:
        st.caption("No hay actividad registrada.")
    else:
        st.dataframe(events, use_container_width=True, hide_index=True)

elif section == "Lotes":
    page_header("Lotes", "Expedientes y estado de elaboración")
    tabs = st.tabs(["Listado", "Nuevo lote"])
    with tabs[0]:
        lotes = lots_df()
        if lotes.empty:
            st.info("No existen lotes. Cree el primer lote desde la pestaña **Nuevo lote**.")
        else:
            f1, f2, f3 = st.columns(3)
            search = f1.text_input("Buscar")
            variedad = f2.selectbox("Variedad", ["Todas"] + sorted(lotes["variedad"].dropna().unique().tolist()))
            etapa = f3.selectbox("Etapa", ["Todas"] + sorted(lotes["etapa"].dropna().unique().tolist()))
            view = lotes.copy()
            if search:
                view = view[view.astype(str).apply(lambda r: r.str.contains(search, case=False).any(), axis=1)]
            if variedad != "Todas":
                view = view[view["variedad"] == variedad]
            if etapa != "Todas":
                view = view[view["etapa"] == etapa]
            st.dataframe(view[["codigo","nombre","variedad","anada","tipo_vino","etapa","responsable","fecha_inicio"]],
                         use_container_width=True, hide_index=True)

            st.divider()
            selected = st.selectbox("Abrir detalle", options=["Seleccione un lote"] + [
                f"{r.codigo or 'SIN-CODIGO'} · {r.nombre}" for r in lotes.itertuples()
            ])
            if selected != "Seleccione un lote":
                lote_id = int(lotes[lotes.apply(lambda r:
                    f"{r['codigo'] or 'SIN-CODIGO'} · {r['nombre']}" == selected, axis=1)].iloc[0]["id"])
                lote = lotes[lotes["id"] == lote_id].iloc[0]
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.subheader(lote["nombre"])
                    st.caption(f"Lote {lote['codigo']} · {lote['variedad']} · Añada {lote['anada']}")
                    st.write(lote["descripcion"] or "Sin descripción.")
                    st.write(f"**Etapa:** {lote['etapa']}  \n**Responsable:** {lote['responsable'] or 'No registrado'}")
                with c2:
                    new_etapa = st.selectbox("Cambiar etapa", ["Elaboración","Fermentación","Crianza","Almacenamiento","Finalizado"],
                                             index=["Elaboración","Fermentación","Crianza","Almacenamiento","Finalizado"].index(lote["etapa"]))
                    if st.button("Actualizar etapa", use_container_width=True):
                        db.execute("UPDATE lotes SET etapa=? WHERE id=?", (new_etapa, lote_id))
                        add_timeline(lote_id, "Etapa", f"Cambio de etapa a {new_etapa}", "Actualización del estado del lote")
                        st.success("Etapa actualizada.")
                        st.rerun()
                    if st.button("Eliminar lote", type="secondary", use_container_width=True):
                        st.session_state[f"confirm_delete_{lote_id}"] = True
                    if st.session_state.get(f"confirm_delete_{lote_id}"):
                        st.warning("¿Eliminar permanentemente este lote y su historial?")
                        if st.button("Sí, eliminar"):
                            db.execute("DELETE FROM lotes WHERE id=?", (lote_id,))
                            st.rerun()
    with tabs[1]:
        with st.form("new_lote", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            codigo = c1.text_input("Código del lote*", placeholder="LT-2026-001")
            nombre = c2.text_input("Nombre del lote*", placeholder="Reserva Parcela Norte")
            variedad = c3.text_input("Variedad de uva")
            c1, c2, c3 = st.columns(3)
            anada = c1.text_input("Añada")
            region = c2.text_input("Región o procedencia")
            parcela = c3.text_input("Parcela o viñedo")
            c1, c2, c3 = st.columns(3)
            tipo = c1.selectbox("Tipo de vino", ["Tinto","Blanco","Rosado","Espumoso","Dulce","Otro"])
            fecha_inicio = c2.date_input("Fecha de inicio")
            responsable = c3.text_input("Responsable")
            etapa = st.selectbox("Etapa actual", ["Elaboración","Fermentación","Crianza","Almacenamiento","Finalizado"])
            descripcion = st.text_area("Descripción")
            observaciones = st.text_area("Observaciones")
            if st.form_submit_button("Guardar lote", type="primary"):
                if not codigo.strip() or not nombre.strip():
                    st.error("El código y el nombre son obligatorios.")
                else:
                    try:
                        lote_id = db.execute("""
                            INSERT INTO lotes (codigo,nombre,variedad,anada,region,parcela,tipo_vino,fecha_inicio,responsable,etapa,descripcion,observaciones)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (codigo.strip(), nombre.strip(), variedad, anada, region, parcela, tipo, str(fecha_inicio),
                              responsable, etapa, descripcion, observaciones))
                        add_timeline(lote_id, "Lote", "Lote creado", f"Registro inicial en etapa {etapa}")
                        st.success("Lote guardado correctamente.")
                    except Exception as exc:
                        st.error(f"No se pudo guardar el lote: {exc}")

elif section == "Laboratorio":
    page_header("Laboratorio", "Registro histórico de análisis fisicoquímicos")
    options = lot_options()
    if not options:
        st.info("Primero registre al menos un lote.")
    else:
        tabs = st.tabs(["Nuevo análisis", "Historial y evolución"])
        with tabs[0]:
            with st.form("analisis"):
                lote_label = st.selectbox("Lote*", list(options))
                c1, c2 = st.columns(2)
                fecha = c1.datetime_input("Fecha y hora")
                responsable = c2.text_input("Responsable")
                metodo = st.text_input("Método de medición")
                observaciones = st.text_area("Observaciones")
                variables = {
                    "ph": "pH", "acidez_total": "Acidez total", "acidez_volatil": "Acidez volátil",
                    "alcohol": "Alcohol (%)", "azucares_residuales": "Azúcares residuales",
                    "glucosa": "Glucosa", "fructosa": "Fructosa", "so2_libre": "SO2 libre",
                    "so2_total": "SO2 total", "acido_malico": "Ácido málico", "acido_lactico": "Ácido láctico",
                }
                values = {}
                cols = st.columns(3)
                for i, (key, label) in enumerate(variables.items()):
                    values[key] = cols[i % 3].number_input(label, value=None, format="%.4f")
                if st.form_submit_button("Guardar análisis", type="primary"):
                    cols_sql = ", ".join(["lote_id","fecha","responsable","metodo","observaciones"] + list(values.keys()))
                    placeholders = ", ".join(["?"] * (5 + len(values)))
                    params = [options[lote_label], str(fecha), responsable, metodo, observaciones] + list(values.values())
                    analisis_id = db.execute(f"INSERT INTO analisis ({cols_sql}) VALUES ({placeholders})", params)
                    add_timeline(options[lote_label], "Análisis", "Nuevo análisis fisicoquímico",
                                 f"Análisis registrado por {responsable or 'responsable no indicado'}", str(fecha))
                    st.success("Análisis agregado al historial.")
        with tabs[1]:
            df = db.fetch_df("""
                SELECT a.*, l.codigo, l.nombre FROM analisis a
                JOIN lotes l ON l.id=a.lote_id ORDER BY a.fecha
            """)
            if df.empty:
                st.info("No hay análisis registrados.")
            else:
                selected_lote = st.selectbox("Filtrar lote", ["Todos"] + [
                    f"{r.codigo or 'SIN-CODIGO'} · {r.nombre}" for r in df.itertuples()
                ])
                if selected_lote != "Todos":
                    df = df[df.apply(lambda r: f"{r['codigo'] or 'SIN-CODIGO'} · {r['nombre']}" == selected_lote, axis=1)]
                variable = st.selectbox("Variable", [c for c in df.columns if c not in [
                    "id","lote_id","fecha","responsable","metodo","observaciones","codigo","nombre"
                ] and pd.api.types.is_numeric_dtype(df[c])])
                chart = df.dropna(subset=[variable])
                if not chart.empty:
                    fig = px.line(chart, x="fecha", y=variable, color="nombre", markers=True)
                    fig.update_layout(paper_bgcolor="#F7F5F0", plot_bgcolor="white")
                    st.plotly_chart(fig, use_container_width=True)
                st.dataframe(df, use_container_width=True, hide_index=True)

elif section == "Inteligencia":
    page_header("Inteligencia", "Predicción, perfiles y exploración de patrones")
    tab1, tab2, tab3, tab4 = st.tabs(["Predicción", "Perfil fisicoquímico", "Comparación", "Patrones"])
    with tab1:
        st.warning("Referencia analítica: las predicciones no representan una evaluación definitiva del vino.")
        models = db.fetch_df("SELECT * FROM modelos ORDER BY entrenado_en DESC")
        lotes = lots_df()
        if models.empty:
            st.info("No existe un modelo entrenado. Cargue un dataset académico y entrene modelos en **Datos y modelos**.")
        else:
            model_options = (models["nombre"] + " · " + models["version"]).tolist()
            model_index = st.selectbox("Modelo", range(len(model_options)), format_func=lambda i: model_options[i])
            row = models.iloc[model_index]
            st.caption(f"Dataset: {row['dataset']}")
            if not row["ruta_archivo"] or not Path(row["ruta_archivo"]).exists():
                st.error("El archivo del modelo no está disponible.")
            else:
                features = json.loads(row["features"])
                cols = st.columns(2)
                values = {}
                for i, feature in enumerate(features):
                    values[feature] = cols[i % 2].number_input(feature, value=0.0)
                if st.button("Generar predicción", type="primary"):
                    model = joblib.load(row["ruta_archivo"])
                    pred = model.predict(pd.DataFrame([values]))
                    lote_label = st.selectbox("Asociar a lote (opcional)", ["Ninguno"] + list(lot_options()))
                    pred_label = str(pred[0])
                    confidence = None
                    if hasattr(model, "predict_proba"):
                        confidence = float(model.predict_proba(pd.DataFrame([values])).max())
                    lote_id = None if lote_label == "Ninguno" else lot_options()[lote_label]
                    db.execute("""
                        INSERT INTO predicciones (lote_id,modelo_nombre,modelo_version,variables_json,prediccion,confianza)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (lote_id, row["nombre"], row["version"], json.dumps(values), pred_label, confidence))
                    st.metric("Resultado", pred_label)
                    if confidence is not None:
                        st.metric("Probabilidad máxima", f"{confidence:.1%}")
    with tab2:
        df = db.fetch_df("""
            SELECT a.*, l.nombre FROM analisis a JOIN lotes l ON l.id=a.lote_id
        """)
        if df.empty:
            st.info("No hay análisis propios para construir perfiles.")
        else:
            numeric = [c for c in df.columns if c not in ["id","lote_id","fecha","responsable","metodo","observaciones","nombre"]
                       and pd.api.types.is_numeric_dtype(df[c])]
            selected_vars = st.multiselect("Variables", numeric, default=numeric[:6])
            lot_names = st.multiselect("Lotes", df["nombre"].unique().tolist(),
                                       default=df["nombre"].unique().tolist()[:3])
            if selected_vars and lot_names:
                profile_rows = []
                for name in lot_names:
                    row = df[df["nombre"] == name].dropna(subset=selected_vars).iloc[-1] if not df[df["nombre"] == name].dropna(subset=selected_vars).empty else None
                    if row is not None:
                        profile_rows.append({"Lote": name, **{v: row[v] for v in selected_vars}})
                if profile_rows:
                    profile = pd.DataFrame(profile_rows).set_index("Lote")
                    normalized = (profile - profile.min()) / (profile.max() - profile.min()).replace(0, 1)
                    melted = normalized.reset_index().melt(id_vars="Lote", var_name="Variable", value_name="Valor")
                    fig = px.line_polar(melted, r="Valor", theta="Variable", color="Lote", line_close=True)
                    fig.update_layout(paper_bgcolor="#F7F5F0")
                    st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(profile, use_container_width=True)
    with tab3:
        df = db.fetch_df("SELECT a.*, l.nombre FROM analisis a JOIN lotes l ON l.id=a.lote_id")
        if df.empty:
            st.info("No hay análisis suficientes para comparar lotes.")
        else:
            names = st.multiselect("Lotes", df["nombre"].unique().tolist(),
                                   default=df["nombre"].unique().tolist()[:2])
            numeric = [c for c in df.columns if c not in ["id","lote_id","fecha","responsable","metodo","observaciones","nombre"]
                       and pd.api.types.is_numeric_dtype(df[c])]
            variable = st.selectbox("Variable", numeric)
            chart = df[df["nombre"].isin(names)].dropna(subset=[variable])
            if not chart.empty:
                fig = px.line(chart, x="fecha", y=variable, color="nombre", markers=True)
                st.plotly_chart(fig, use_container_width=True)
    with tab4:
        st.caption("Los análisis disponibles pueden provenir del dataset académico cargado.")
        st.info("Cargue un dataset académico en **Datos y modelos** para ejecutar PCA y clustering.")

elif section == "Catas y observaciones":
    page_header("Catas y observaciones", "Registro sensorial vinculado al lote")
    options = lot_options()
    if not options:
        st.info("Primero registre al menos un lote.")
    else:
        tabs = st.tabs(["Nueva cata", "Historial", "Traductor de lenguaje"])
        with tabs[0]:
            with st.form("cata"):
                lote_label = st.selectbox("Lote*", list(options))
                c1,c2,c3 = st.columns(3)
                fecha = c1.date_input("Fecha")
                responsable = c2.text_input("Responsable")
                color = c3.text_input("Color")
                c1,c2,c3 = st.columns(3)
                claridad = c1.text_input("Claridad")
                intensidad = c2.text_input("Intensidad aromática")
                descriptores = c3.text_input("Descriptores aromáticos")
                c1,c2,c3 = st.columns(3)
                acidez = c1.text_input("Percepción de acidez")
                dulzor = c2.text_input("Percepción de dulzor")
                taninos = c3.text_input("Taninos")
                c1,c2,c3 = st.columns(3)
                cuerpo = c1.text_input("Cuerpo")
                persistencia = c2.text_input("Persistencia")
                defectos = c3.text_input("Posibles defectos percibidos")
                observaciones = st.text_area("Observaciones generales")
                if st.form_submit_button("Guardar cata", type="primary"):
                    db.execute("""
                        INSERT INTO catas (lote_id,fecha,responsable,color,claridad,intensidad_aromatica,descriptores,
                        acidez_percibida,dulzor,taninos,cuerpo,persistencia,observaciones,defectos)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (options[lote_label],str(fecha),responsable,color,claridad,intensidad,descriptores,
                          acidez,dulzor,taninos,cuerpo,persistencia,observaciones,defectos))
                    add_timeline(options[lote_label], "Cata", "Registro sensorial", observaciones or "Cata registrada", str(fecha))
                    st.success("Cata registrada.")
        with tabs[1]:
            df = db.fetch_df("SELECT c.*, l.codigo, l.nombre FROM catas c JOIN lotes l ON l.id=c.lote_id ORDER BY c.fecha")
            st.dataframe(df if not df.empty else df, use_container_width=True, hide_index=True)
            if df.empty:
                st.info("No hay catas registradas.")
        with tabs[2]:
            description = st.text_area("Descripción sensorial")
            if st.button("Analizar descripción"):
                text = description.lower()
                suggestions = []
                if any(x in text for x in ["vinagre","ácido","acida","picante"]):
                    suggestions.append(("Acidez volátil", "Puede revisarse junto con el historial analítico del lote."))
                if "fresco" in text:
                    suggestions.append(("pH y acidez total", "Variables útiles para explorar el contexto analítico."))
                if any(x in text for x in ["astring","seco","tanino"]):
                    suggestions.append(("Taninos y variables fenólicas", "Puede explorarse si existen mediciones disponibles."))
                if any(x in text for x in ["alcohol","caliente","ardiente"]):
                    suggestions.append(("Alcohol", "Variable relevante para revisar el perfil del lote."))
                if suggestions:
                    for title, note in suggestions:
                        st.markdown(f"<div class='vino-card'><b>{title}</b><br>{note}</div>", unsafe_allow_html=True)
                    st.caption("Estas relaciones son referencias de exploración, no diagnósticos ni relaciones causales.")
                else:
                    st.info("No se encontraron referencias preconfiguradas. Puede describir aromas como vinagre, frescura, astringencia o sensación alcohólica.")

elif section == "Almacenamiento":
    page_header("Almacenamiento", "Condiciones y historia de recipientes")
    options = lot_options()
    if not options:
        st.info("Primero registre al menos un lote.")
    else:
        tabs = st.tabs(["Nuevo registro", "Historial"])
        with tabs[0]:
            with st.form("storage"):
                lote_label = st.selectbox("Lote*", list(options))
                c1,c2,c3 = st.columns(3)
                tipo = c1.selectbox("Tipo de recipiente", ["Barrica","Tanque","Botella","Anfora","Otro"])
                identificador = c2.text_input("Identificador")
                material = c3.text_input("Material")
                c1,c2,c3 = st.columns(3)
                fecha_inicio = c1.date_input("Fecha de inicio")
                temperatura = c2.number_input("Temperatura (°C)", value=None)
                cierre = c3.text_input("Tipo de cierre")
                condiciones = st.text_input("Condiciones")
                observaciones = st.text_area("Observaciones")
                if st.form_submit_button("Guardar registro", type="primary"):
                    db.execute("""
                        INSERT INTO almacenamiento (lote_id,tipo_recipiente,identificador,material,fecha_inicio,
                        temperatura,condiciones,cierre,observaciones) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (options[lote_label],tipo,identificador,material,str(fecha_inicio),temperatura,condiciones,cierre,observaciones))
                    add_timeline(options[lote_label], "Almacenamiento", f"{tipo} · {identificador or 'sin identificador'}",
                                 observaciones or "Registro de almacenamiento", str(fecha_inicio))
                    st.success("Condiciones registradas sin reemplazar el historial.")
        with tabs[1]:
            df = db.fetch_df("""
                SELECT a.*, l.codigo,l.nombre FROM almacenamiento a
                JOIN lotes l ON l.id=a.lote_id ORDER BY a.fecha_inicio DESC
            """)
            st.dataframe(df if not df.empty else df, use_container_width=True, hide_index=True)
            if df.empty:
                st.info("No hay registros de almacenamiento.")

elif section == "Seguimiento":
    page_header("Seguimiento", "Línea de tiempo del expediente")
    options = lot_options()
    if not options:
        st.info("Primero registre al menos un lote.")
    else:
        lote_label = st.selectbox("Lote", list(options))
        lote_id = options[lote_label]
        c1,c2 = st.columns([3,1])
        with c2:
            with st.popover("Agregar evento"):
                tipo = st.selectbox("Tipo", ["Proceso","Nota","Observación","Evento"])
                titulo = st.text_input("Título")
                descripcion = st.text_area("Descripción")
                fecha_evento = st.date_input("Fecha", value=date.today())
                if st.button("Guardar evento"):
                    if titulo:
                        add_timeline(lote_id,tipo,titulo,descripcion,str(fecha_evento))
                        st.success("Evento agregado.")
                        st.rerun()
        with c1:
            timeline = db.fetch_df(
                "SELECT * FROM seguimiento WHERE lote_id=? ORDER BY fecha DESC, id DESC",
                (lote_id,),
            )
            if timeline.empty:
                st.info("El expediente no tiene eventos.")
            for row in timeline.itertuples():
                st.markdown(f"""
                <div class='vino-card'>
                    <small>{row.fecha} · {row.tipo}</small><br>
                    <b>{row.titulo}</b><br>{row.descripcion or ''}
                </div>
                """, unsafe_allow_html=True)

elif section == "Datos y modelos":
    page_header("Datos y modelos", "Datasets académicos separados de los datos propios")
    tabs = st.tabs(["Dataset académico", "Datos propios", "Modelos"])
    with tabs[0]:
        uploaded = st.file_uploader("Cargar CSV académico", type=["csv"])
        if uploaded:
            try:
                df = pd.read_csv(uploaded)
                st.session_state["academic_df"] = df
                st.success(f"Dataset cargado: {len(df)} filas y {len(df.columns)} columnas.")
            except Exception as exc:
                st.error(f"No se pudo leer el CSV: {exc}")
        df = st.session_state.get("academic_df")
        if df is not None:
            st.subheader("Vista y limpieza")
            st.dataframe(df, use_container_width=True)
            c1,c2,c3 = st.columns(3)
            c1.metric("Filas", len(df))
            c2.metric("Columnas", len(df.columns))
            c3.metric("Valores nulos", int(df.isna().sum().sum()))
            numeric = df.select_dtypes(include="number")
            if len(numeric.columns) >= 2:
                st.subheader("Correlaciones")
                st.plotly_chart(px.imshow(numeric.corr(), text_auto=".2f", color_continuous_scale="RdBu_r"),
                                use_container_width=True)
            if len(numeric.columns) >= 3:
                st.subheader("PCA")
                clean = numeric.dropna()
                if len(clean) >= 2:
                    scaler = StandardScaler()
                    transformed = PCA(n_components=2).fit_transform(scaler.fit_transform(clean))
                    pca_df = pd.DataFrame(transformed, columns=["Componente 1","Componente 2"])
                    st.plotly_chart(px.scatter(pca_df,x="Componente 1",y="Componente 2"),
                                    use_container_width=True)
            if len(numeric.columns) >= 2:
                st.subheader("Clustering")
                clusters = st.slider("Número de agrupamientos", 2, min(8, max(2, len(numeric.dropna()))))
                clean = numeric.dropna()
                if len(clean) >= clusters:
                    labels = KMeans(n_clusters=clusters, random_state=42, n_init=10).fit_predict(StandardScaler().fit_transform(clean))
                    cluster_df = pd.DataFrame(StandardScaler().fit_transform(clean),
                                              columns=numeric.columns).iloc[:, :2]
                    cluster_df.columns = ["Variable 1","Variable 2"]
                    cluster_df["Grupo"] = labels
                    st.plotly_chart(px.scatter(cluster_df,x="Variable 1",y="Variable 2",color="Grupo"),
                                    use_container_width=True)
            st.subheader("Entrenamiento")
            target = st.selectbox("Variable objetivo", [""] + numeric.columns.tolist())
            model_names = st.multiselect("Modelos", ["Regresión logística","Árbol de decisión","Random Forest"],
                                         default=["Regresión logística"])
            if st.button("Entrenar modelos", type="primary"):
                if not target or not model_names:
                    st.error("Seleccione una variable objetivo y al menos un modelo.")
                else:
                    data = numeric.dropna()
                    X = data.drop(columns=[target])
                    y = data[target]
                    if y.nunique() < 2:
                        st.error("La variable objetivo necesita al menos dos clases o niveles.")
                    elif len(data) < 10:
                        st.error("Se requieren al menos 10 filas válidas.")
                    else:
                        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=.25, random_state=42,
                                                                            stratify=y if y.nunique() < 20 else None)
                        constructors = {
                            "Regresión logística": LogisticRegression(max_iter=1000),
                            "Árbol de decisión": DecisionTreeClassifier(random_state=42),
                            "Random Forest": RandomForestClassifier(n_estimators=100, random_state=42),
                        }
                        for name in model_names:
                            model = constructors[name]
                            model.fit(X_train, y_train)
                            pred = model.predict(X_test)
                            metrics = {
                                "accuracy": float(accuracy_score(y_test,pred)),
                                "precision": float(precision_score(y_test,pred,average="weighted",zero_division=0)),
                                "recall": float(recall_score(y_test,pred,average="weighted",zero_division=0)),
                                "f1": float(f1_score(y_test,pred,average="weighted",zero_division=0)),
                            }
                            models_dir = Path("models")
                            models_dir.mkdir(exist_ok=True)
                            version = "1.0"
                            route = models_dir / f"{name.lower().replace(' ','_')}.joblib"
                            joblib.dump(model, route)
                            db.execute("""
                                INSERT INTO modelos (nombre,version,tipo,dataset,objetivo,features,metricas_json,ruta_archivo)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (name,version,"Clasificación","Dataset académico CSV",target,json.dumps(X.columns.tolist()),
                                  json.dumps(metrics),str(route)))
                            st.success(f"{name}: Accuracy {metrics['accuracy']:.3f}, F1 {metrics['f1']:.3f}")
    with tabs[1]:
        lotes = lots_df()
        analisis = db.fetch_df("SELECT * FROM analisis")
        c1,c2 = st.columns(2)
        c1.metric("Lotes propios", len(lotes))
        c2.metric("Análisis propios", len(analisis))
        st.caption("Estos datos provienen exclusivamente de SQLite y no se mezclan con el dataset académico.")
        st.dataframe(lotes, use_container_width=True, hide_index=True)
        if not analisis.empty:
            st.dataframe(analisis, use_container_width=True, hide_index=True)
    with tabs[2]:
        models = db.fetch_df("SELECT id,nombre,version,tipo,dataset,objetivo,features,metricas_json,entrenado_en FROM modelos ORDER BY entrenado_en DESC")
        if models.empty:
            st.info("No existen modelos entrenados.")
        else:
            for row in models.itertuples():
                metrics = json.loads(row.metricas_json)
                st.markdown(f"<div class='vino-card'><b>{row.nombre} · v{row.version}</b><br>"
                            f"Objetivo: {row.objetivo} · Dataset: {row.dataset}<br>"
                            f"Accuracy: {metrics['accuracy']:.3f} · F1: {metrics['f1']:.3f} · "
                            f"Precision: {metrics['precision']:.3f} · Recall: {metrics['recall']:.3f}</div>",
                            unsafe_allow_html=True)

elif section == "Reportes":
    page_header("Reportes", "Expedientes exportables")
    options = lot_options()
    if not options:
        st.info("Primero registre al menos un lote.")
    else:
        lote_label = st.selectbox("Seleccione el lote", list(options))
        lote_id = options[lote_label]
        lote = db.fetch_df("SELECT * FROM lotes WHERE id=?", (lote_id,))
        analisis = db.fetch_df("SELECT * FROM analisis WHERE lote_id=? ORDER BY fecha", (lote_id,))
        catas = db.fetch_df("SELECT * FROM catas WHERE lote_id=? ORDER BY fecha", (lote_id,))
        almacenamiento = db.fetch_df("SELECT * FROM almacenamiento WHERE lote_id=? ORDER BY fecha_inicio", (lote_id,))
        seguimiento = db.fetch_df("SELECT * FROM seguimiento WHERE lote_id=? ORDER BY fecha", (lote_id,))

        st.subheader("Vista del expediente")
        st.write(lote.to_dict("records")[0])
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Análisis",len(analisis))
        c2.metric("Catas",len(catas))
        c3.metric("Almacenamiento",len(almacenamiento))
        c4.metric("Eventos",len(seguimiento))

        report = {"lote": lote.to_csv(index=False)}
        if not analisis.empty:
            report["analisis"] = analisis.to_csv(index=False)
        if not catas.empty:
            report["catas"] = catas.to_csv(index=False)
        if not almacenamiento.empty:
            report["almacenamiento"] = almacenamiento.to_csv(index=False)
        if not seguimiento.empty:
            report["seguimiento"] = seguimiento.to_csv(index=False)
        combined = "\n\n".join(f"[{key.upper()}]\n{value}" for key,value in report.items())
        st.download_button("Descargar expediente CSV",
                           data=combined,
                           file_name=f"reporte_{lote.iloc[0]['codigo'] or lote_id}.csv",
                           mime="text/csv")
        if st.button("Generar PDF"):
            pdf_buffer = BytesIO()
            pdf = canvas.Canvas(pdf_buffer, pagesize=A4)
            width, height = A4
            y = height - 50
            pdf.setTitle(f"Reporte VINTALYTICS - {lote.iloc[0]['codigo'] or lote_id}")
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawString(50, y, "VINTALYTICS - Expediente del lote")
            y -= 35
            pdf.setFont("Helvetica", 10)
            record = lote.iloc[0].to_dict()
            for key, value in record.items():
                if y < 50:
                    pdf.showPage()
                    y = height - 50
                    pdf.setFont("Helvetica", 10)
                text = f"{key}: {value if value is not None else 'No registrado'}"
                pdf.drawString(50, y, str(text)[:120])
                y -= 16
            pdf.save()
            st.download_button("Descargar PDF", pdf_buffer.getvalue(),
                               file_name=f"reporte_{lote.iloc[0]['codigo'] or lote_id}.pdf",
                               mime="application/pdf")
        if st.button("Exportar datos a Excel"):
            output = Path("data") / f"reporte_{lote_id}.xlsx"
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                lote.to_excel(writer,sheet_name="Lote",index=False)
                if not analisis.empty: analisis.to_excel(writer,sheet_name="Analisis",index=False)
                if not catas.empty: catas.to_excel(writer,sheet_name="Catas",index=False)
                if not almacenamiento.empty: almacenamiento.to_excel(writer,sheet_name="Almacenamiento",index=False)
                if not seguimiento.empty: seguimiento.to_excel(writer,sheet_name="Seguimiento",index=False)
            with open(output,"rb") as file:
                st.download_button("Descargar Excel",file.read(),file_name=output.name,
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
