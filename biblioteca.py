from pathlib import Path
import duckdb as dd

#%% CREACIÓN DE LA BASE DE DATOS


# Ubicación del proyecto
raiz = Path(__file__).parent

# Crea la carpeta data si todavía no existe
carpeta_datos = raiz / "data"
carpeta_datos.mkdir(exist_ok=True)

# Abre la base; si no existe, la crea
conexion = dd.connect(str(carpeta_datos / "biblioteca.duckdb"))

# Leemos el archivo con las instrucciones SQL
esquema = (raiz / "schema.sql").read_text(encoding="utf-8")

print("Archivo SQL:", raiz / "schema.sql")
print("Contenido:", repr(esquema))

# Ejecutamos esas instrucciones para crear las tablas
conexion.execute(esquema)

# Mostramos qué tablas existen
print(conexion.execute("SHOW TABLES").df())

conexion.close()
