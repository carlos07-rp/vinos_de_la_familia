# VINTALYTICS — Wine Intelligence & Winery Data System

MVP 2.0. Interfaz HTML5, CSS3 y JavaScript; backend Python/FastAPI; SQLite; Pandas, Scikit-learn y Plotly. El archivo académico incluido es el CSV original proporcionado. La base de la finca comienza vacía.

## Windows
1. Descomprimir la carpeta completa. Se necesita Python instalado (3.12 recomendado).
2. Doble clic en `INSTALAR.bat` (requiere Internet la primera vez).
3. Doble clic en `INICIAR.bat`. Si el navegador se abre antes de que arranque el servidor, recargar http://localhost:8000.
4. En Datos y modelos > Modelos, seleccionar Entrenar y comparar. No se distribuyen binarios Joblib para evitar incompatibilidades.

Alternativa PowerShell desde la carpeta del proyecto:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

No se requiere Node.js ni Streamlit. Plotly se sirve localmente y no necesita CDN.

## Estructura
- `frontend/index.html`: estructura de la interfaz de los nueve módulos (una sola página con navegación dinámica).
- `frontend/styles.css`: estilo responsive, paleta burgundy, marfil y oro.
- `frontend/app.js`: formularios, llamadas API, navegación y gráficas.
- `main.py`: API y servidor de archivos.
- `db.py`: persistencia relacional de lotes y registros.
- `ml.py`: limpieza, entrenamiento, evaluación, predicción, PCA y K-means.
- `reports.py`: PDF y Excel.
- `data/academico.csv`: dataset académico separado de los datos propios.

## Publicar y compartir
Subir el contenido de esta carpeta a un repositorio de GitHub, sin la base de datos privada. En un servicio que soporte Python/ASGI, usar `pip install -r requirements.txt` como comando de compilación y `uvicorn main:app --host 0.0.0.0 --port $PORT` como inicio. El archivo `render.yaml` es una configuración inicial para Render con disco persistente (puede tener costo; verificar plan y configuración antes del despliegue). Configurar `VINTALYTICS_DATA` hacia una carpeta persistente, y `VINTALYTICS_PASSWORD` con una contraseña fuerte, `VINTALYTICS_USER` con el usuario deseado. La autenticación HTTP Basic compartida protege el prototipo cuando la contraseña está configurada; usar HTTPS en el alojamiento. No publicar sin configurar autenticación. El servicio generará una URL para compartir; los visitantes no instalan nada. GitHub Pages por sí solo no ejecuta Python.

En local, sin esas variables, no hay autenticación y el servidor escucha solo en la computadora. Respaldar periódicamente la carpeta persistente (SQLite, CSV y modelos). No usar múltiples réplicas con SQLite. No se ha realizado un despliegue real.

## Metodología y limitaciones
- Se usan once variables originales y objetivo `quality`; se eliminan perfiles duplicados y contradictorios antes de dividir. Evaluación estratificada 75/25; selección exploratoria por F1 macro, no validación externa. Los resultados se calculan al entrenar.
- Unidades del CSV deben confirmarse con la fuente original. Acidez fija y acidez total medida son campos distintos. Las predicciones no son diagnósticos ni evaluaciones definitivas; no hay confianza calibrada.
- Implementados los nueve módulos con navegación, formularios y persistencia. La comparación utiliza el último análisis y la evolución de pH. Los filtros de variedad y añada funcionan mediante búsqueda textual, no selectores independientes. El traductor sensorial utiliza reglas de palabras clave.
- Pendientes: variables personalizables, unidades y métodos por variable, gráficas dentro de PDF, conservación de binarios de todas las versiones, roles/usuarios individuales, migración a PostgreSQL, validación externa y pruebas visuales integrales en navegador. El modelo actual se reemplaza al entrenar; metadatos históricos permanecen.
- API verificada mediante TestClient con base temporal: inicio vacío, registro de lote, análisis, historial, dataset, entrenamiento, predicción, PCA/K-means, exportación PDF/XLSX/CSV y eliminación. Sintaxis Python y JS verificada. Los datos de prueba no se incluyen.
