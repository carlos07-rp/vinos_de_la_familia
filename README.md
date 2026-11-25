# VINTALYTICS — Wine Intelligence & Winery Data System

MVP 2.0. Interfaz HTML5, CSS3 y JavaScript; backend Python/FastAPI; SQLite; Pandas, Scikit-learn y Plotly. El archivo académico incluido es el CSV original proporcionado. La base de la finca comienza vacía.

## Windows
1. Descomprimir la carpeta completa. Se necesita Python instalado (3.12 recomendado).
2. Doble clic en `INSTALAR.bat` (requiere Internet la primera vez).
3. Doble clic en `INICIAR.bat`. En el primer inicio, la terminal pedirá el usuario y una contraseña nueva (mínimo 12 caracteres); no se muestra ni se guarda en texto plano. Después abrirá el navegador.
4. En Datos y modelos > Modelos, seleccionar Entrenar y comparar. No se distribuyen binarios Joblib para evitar incompatibilidades.

Alternativa PowerShell desde la carpeta del proyecto:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py ensure-admin
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

También se puede crear manualmente el primer administrador con `.\.venv\Scripts\python.exe main.py create-admin`. Los usuarios, hashes PBKDF2 y sesiones revocables se guardan en SQLite; las sesiones del navegador expiran a las 12 horas. El dashboard y todos los endpoints de datos requieren sesión autenticada. Sin usuarios, la página muestra el procedimiento de configuración y no abre el dashboard.

No se requiere Node.js ni Streamlit. Plotly se sirve localmente y no necesita CDN.

## Seguridad y persistencia
- No existen credenciales por defecto ni variables de entorno que omitan el inicio de sesión.
- `VINTALYTICS_DATA` determina la carpeta persistente para la base de datos, dataset y modelos.
- En producción, usar HTTPS; el navegador recibe una cookie `HttpOnly` y `SameSite=Strict`, marcada `Secure` bajo HTTPS.
- Configure `VINTALYTICS_DATA` en un disco persistente para conservar base de datos, dataset y modelos.
- Consulte `/api/health` para verificar el estado del servicio.

## Estructura
- `frontend/index.html`: estructura de la interfaz de los nueve módulos (una sola página con navegación dinámica).
- `frontend/styles.css`: estilo responsive, paleta burgundy, marfil y oro.
- `frontend/app.js`: formularios, llamadas API, navegación y gráficas.
- `main.py`: API y servidor de archivos.
- `db.py`: persistencia relacional de lotes y registros.
- `ml.py`: limpieza, entrenamiento, evaluación, predicción, PCA y K-means.
- `reports.py`: PDF y Excel.
- `data/academico.csv`: dataset académico separado de los datos propios.
- `frontend/assets/images/`: fotografías WebP locales; consultar `CREDITS.txt` para fuentes y licencias.

## Publicar y compartir
Subir el contenido de esta carpeta a un repositorio de GitHub, sin la base de datos privada. En un servicio que soporte Python/ASGI, usar `pip install -r requirements.txt` como comando de compilación y `uvicorn main:app --host 0.0.0.0 --port $PORT` como inicio. El archivo `render.yaml` es una configuración inicial para Render con disco persistente (puede tener costo; verificar plan y configuración antes del despliegue). Configurar `VINTALYTICS_DATA` en una carpeta persistente y HTTPS. Antes de compartir el servicio, ejecutar `python main.py create-admin` en una consola del servicio para crear la primera cuenta. No existe una cuenta pública ni una contraseña de instalación. El servicio generará una URL para compartir; los visitantes no instalan nada. GitHub Pages por sí solo no ejecuta Python.

En local, la autenticación siempre está activa y el servidor escucha solo en la computadora. Respaldar periódicamente la carpeta persistente (SQLite, CSV y modelos). No usar múltiples réplicas con SQLite. No se ha realizado un despliegue real.

## Metodología y limitaciones
- Se usan once variables originales y objetivo `quality`; se eliminan perfiles duplicados y contradictorios antes de dividir. Evaluación estratificada 75/25; selección exploratoria por F1 macro, no validación externa. Los resultados se calculan al entrenar.
- Unidades del CSV deben confirmarse con la fuente original. Acidez fija y acidez total medida son campos distintos. Las predicciones no son diagnósticos ni evaluaciones definitivas; no hay confianza calibrada.
- Implementados los nueve módulos con navegación, formularios y persistencia. La comparación utiliza el último análisis y la evolución de pH. Los filtros de variedad y añada funcionan mediante búsqueda textual, no selectores independientes. El traductor sensorial utiliza reglas de palabras clave.
- Pendientes: variables personalizables, unidades y métodos por variable, gráficas dentro de PDF, conservación de binarios de todas las versiones, roles/usuarios individuales, migración a PostgreSQL, validación externa y pruebas visuales integrales en navegador. El modelo actual se reemplaza al entrenar; metadatos históricos permanecen.
- API verificada mediante TestClient con base temporal: inicio vacío, registro de lote, análisis, historial, dataset, entrenamiento, predicción, PCA/K-means, exportación PDF/XLSX/CSV y eliminación. Sintaxis Python y JS verificada. Los datos de prueba no se incluyen.
