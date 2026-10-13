from pathlib import Path
import duckdb as dd

#%% CREACIÓN DE LA BASE DE DATOS

raiz = Path(__file__).parent

# Crea la carpeta data si todavía no existe
carpeta_datos = raiz / "data"
carpeta_datos.mkdir(exist_ok=True)

# Abre la base; si no existe, la crea
conexion = dd.connect(str(carpeta_datos / "biblioteca.duckdb"))

esquema = (raiz / "schema.sql").read_text(encoding="utf-8")
conexion.execute(esquema)

conexion.close()
