# VINTALYTICS

VINTALYTICS es un MVP de gestión e inteligencia de datos vitivinícolas construido con Streamlit, SQLite y scikit-learn.

## Ejecutar

### Versión web HTML

```bash
python -m http.server 8000
```

Abra `http://localhost:8000/index.html`. Esta versión utiliza `localStorage` para conservar los lotes creados en el navegador.

### Aplicación Streamlit

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

La base de datos SQLite se crea automáticamente en `data/vintalytics.db`. Los datos académicos y los datos propios se mantienen separados.

## Alcance inicial

- Gestión de lotes, análisis, catas, almacenamiento y seguimiento.
- Dashboard con indicadores calculados desde SQLite.
- Comparación y evolución de variables.
- Carga de datasets académicos CSV.
- Análisis descriptivo, correlaciones, PCA y clustering.
- Entrenamiento y comparación de modelos cuando el dataset contiene una variable objetivo válida.
- Exportación CSV y Excel.
