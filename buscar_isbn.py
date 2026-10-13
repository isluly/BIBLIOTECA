import json
import duckdb as dd
from urllib.request import urlopen
from urllib.parse import urlencode
from pathlib import Path
raiz = Path(__file__).parent
ruta_base = raiz / "data" / "biblioteca.duckdb"
if not ruta_base.exists():
    raise SystemExit("Primero ejecutá biblioteca.py para crear la base y sus tablas.")
conexion = dd.connect(str(ruta_base))
# Permite conservar una sugerencia o ingresar otro valor
def completar(campo, sugerencia=""):
    nuevo = input(f"{campo} [{sugerencia}]: ").strip()
    if nuevo == "":
        return sugerencia
    return nuevo
def elegir_o_agregar(campo, consulta):
    filas = conexion.execute(consulta).fetchall()
    opciones = [fila[0] for fila in filas]
    print(f"\n{campo}")
    for numero, opcion in enumerate(opciones, start=1):
        print(f"{numero}. {opcion}")
    while True:
        entrada = input(
            "Elegí un número o escribí un valor nuevo: "
        ).strip()
        if entrada == "":
            print("Este campo es obligatorio.")
            continue
        if entrada.isdigit():
            numero = int(entrada)
            if 1 <= numero <= len(opciones):
                return opciones[numero - 1]
            print("Ese número no está entre las opciones.")
            continue
        # Reutilizamos la escritura existente si solo cambia
        # el uso de mayúsculas y minúsculas
        for opcion in opciones:
            if entrada.casefold() == opcion.casefold():
                return opcion
        return entrada
# Búsqueda por ISBN
isbn = input("Ingresá el ISBN: ").strip().replace("-", "").replace(" ", "")
libro = None
if isbn:
    parametros = urlencode({
        "bibkeys": f"ISBN:{isbn}",
        "format": "json",
        "jscmd": "data"
    })
    url = f"https://openlibrary.org/api/books?{parametros}"
    with urlopen(url, timeout=20) as respuesta:
        datos = json.load(respuesta)
    libro = datos.get(f"ISBN:{isbn}")
# Valores iniciales para los datos que puedan faltar
titulo = ""
autores = []
editoriales = []
portada = ""
fecha = ""
if libro is None:
    print("Open Library no encontró ese ISBN.")
else:
    titulo = libro.get("title", "")
    autores = [
        autor["name"]
        for autor in libro.get("authors", [])
    ]
    editoriales = [
        editorial["name"]
        for editorial in libro.get("publishers", [])
    ]
    portada = libro.get("cover", {}).get("large", "")
    fecha = libro.get("publish_date", "")
    print("\nDatos encontrados:")
    print("Título:", titulo)
    print("Autores:", ", ".join(autores))
    print("Editorial:", ", ".join(editoriales))
    print("Fecha de edición:", fecha)
    print("Portada:", portada)
# Datos de la edición
print("\nCompletá los datos de tu edición.")
print("Enter conserva el valor entre corchetes.")
print("Los campos opcionales pueden quedar vacíos.\n")
titulo_edicion = completar("Título de la edición", titulo)
while titulo_edicion == "":
    print("El título es obligatorio.")
    titulo_edicion = completar("Título de la edición")
editorial = completar("Editorial", ", ".join(editoriales))
# La fecha encontrada se mostró arriba para que puedas revisarla
anio_edicion = completar("Año de tu edición")
idioma_edicion = completar("Idioma de tu edición")
portada_edicion = completar("URL o ruta de la portada", portada)
notas_edicion = completar("Notas")
print("\nDatos de la edición revisados:")
print("ISBN:", isbn)
print("Título:", titulo_edicion)
print("Editorial:", editorial)
print("Año:", anio_edicion)
print("Idioma:", idioma_edicion)
print("Portada:", portada_edicion)
print("Notas:", notas_edicion)
# Convertimos los años a números; vacío significa dato desconocido
def convertir_anio(valor, campo):
    while valor != "":
        try:
            return int(valor)
        except ValueError:
            print("Ingresá un año entero o dejalo vacío.")
            valor = completar(campo)
    return None

def cargar_obra():
    # Elegir una obra existente o cargar una nueva
    print("\n1. Elegir una obra ya registrada")
    print("2. Cargar una obra nueva")
    opcion_obra = input("Elegí una opción: ").strip()
    while opcion_obra not in ["1", "2"]:
        opcion_obra = input("Ingresá 1 o 2: ").strip()

    id_obra_existente = None
    if opcion_obra == "1":
        obras_existentes = conexion.execute("""
            SELECT o.id_obra, o.titulo, o.estado_lectura,
                (SELECT string_agg(a.nombre || ' ' || coalesce(a.apellido, ''), ', ')
                 FROM escribe es JOIN autores a ON a.id_autor = es.id_autor
                 WHERE es.id_obra = o.id_obra) AS autores
            FROM obras o ORDER BY o.titulo, o.id_obra
        """).fetchall()
        if not obras_existentes:
            print("No hay obras registradas. Cargaremos una nueva.")
        else:
            print("\nObras registradas:")
            for numero, obra in enumerate(obras_existentes, start=1):
                print(f"{numero}. {obra[1]} — {obra[3] or 'Sin autor registrado'} — {obra[2]}")
            seleccion = input("Elegí el número de la obra: ").strip()
            while not seleccion.isdigit() or not 1 <= int(seleccion) <= len(obras_existentes):
                seleccion = input("Ingresá un número de la lista: ").strip()
            obra = obras_existentes[int(seleccion) - 1]
            id_obra_existente = obra[0]
            print("Obra seleccionada:", obra[1])

    if id_obra_existente is None:
        # Datos de la obra
        print("\nDatos de la obra")
        titulo_obra = completar("Título de la obra", titulo_edicion)
        while not titulo_obra:
            titulo_obra = completar("Título de la obra")
        anio_original = convertir_anio(completar("Año de publicación original"), "Año original")
        idioma_original = completar("Idioma original")
        # Un solo género por obra, obligatorio
        genero = elegir_o_agregar(
            "Género",
            """
            SELECT DISTINCT genero
            FROM obras
            WHERE genero IS NOT NULL AND trim(genero) <> ''
            ORDER BY genero
            """
        )
        # Estados de lectura predefinidos
        estados = ["pendiente", "en lectura", "leído", "abandonado"]
        print("\nEstado de lectura:")
        for numero, estado in enumerate(estados, start=1):
            print(f"{numero}. {estado}")
        opcion = input("Elegí un número [1]: ").strip()
        # Enter selecciona pendiente
        if opcion == "":
            opcion = "1"
        while opcion not in ["1", "2", "3", "4"]:
            opcion = input("Ingresá un número del 1 al 4: ").strip()
        estado_lectura = estados[int(opcion) - 1]
        # Valoración opcional, del 1 al 5
        valoracion = completar("Valoración del 1 al 5")
        while valoracion not in ["", "1", "2", "3", "4", "5"]:
            print("Ingresá un número del 1 al 5 o dejalo vacío.")
            valoracion = completar("Valoración del 1 al 5")
        if valoracion == "":
            valoracion = None
        else:
            valoracion = int(valoracion)
        comentario = completar("Comentario personal")
        # Al menos un tema por obra
        temas = []
        while True:
            tema = elegir_o_agregar(
                "Tema de la obra",
                "SELECT nombre FROM temas ORDER BY nombre"
            )
            # Evitamos repetir un tema, aunque cambien las mayúsculas
            if tema.casefold() not in [t.casefold() for t in temas]:
                temas.append(tema)
            else:
                print("Ese tema ya está seleccionado.")
            print("Temas seleccionados:", ", ".join(temas))
            otro = input("¿Agregar otro tema? (s/n): ").strip().lower()
            while otro not in ["s", "n"]:
                otro = input("Ingresá s o n: ").strip().lower()
            if otro == "n":
                break
        print("\nObra revisada:")
        print("Título:", titulo_obra)
        print("Año original:", anio_original)
        print("Idioma original:", idioma_original)
        print("Género:", genero)
        print("Estado:", estado_lectura)
        print("Valoración:", valoracion)
        print("Comentario:", comentario)
        print("Temas:", ", ".join(temas))
        # Autores de la obra
        print("\nAutores sugeridos por la API:", ", ".join(autores))
        autores_seleccionados = []
        anonima = input("¿La obra es anónima? (s/n): ").strip().lower()
        while anonima not in ["s", "n"]:
            anonima = input("Ingresá s o n: ").strip().lower()
        if anonima == "n":
            while True:
                existentes = conexion.execute("""
                    SELECT id_autor, nombre, apellido, nacionalidad
                    FROM autores
                    ORDER BY apellido, nombre
                """).fetchall()
                print("\nAutores registrados:")
                for numero, autor in enumerate(existentes, start=1):
                    apellido = autor[2] or ""
                    print(f"{numero}. {autor[1]} {apellido}")
                print("0. Cargar un autor nuevo")
                opcion = input("Elegí un número: ").strip()
                while (
                    not opcion.isdigit()
                    or int(opcion) > len(existentes)
                ):
                    opcion = input("Elegí un número de la lista: ").strip()
                numero = int(opcion)
                if numero == 0:
                    nombre = completar("Nombre")
                    while nombre == "":
                        print("El nombre es obligatorio.")
                        nombre = completar("Nombre")
                    apellido = completar("Apellido")
                    nacionalidad = completar("Nacionalidad")
                    autor_elegido = {
                        "id_autor": None,
                        "nombre": nombre,
                        "apellido": apellido or None,
                        "nacionalidad": nacionalidad or None
                    }
                else:
                    autor = existentes[numero - 1]
                    autor_elegido = {
                        "id_autor": autor[0],
                        "nombre": autor[1],
                        "apellido": autor[2],
                        "nacionalidad": autor[3]
                    }
                if autor_elegido not in autores_seleccionados:
                    autores_seleccionados.append(autor_elegido)
                else:
                    print("Ese autor ya está seleccionado.")
                otro = input("¿Agregar otro autor? (s/n): ").strip().lower()
                while otro not in ["s", "n"]:
                    otro = input("Ingresá s o n: ").strip().lower()
                if otro == "n":
                    break
        print("\nAutores seleccionados:")
        if anonima == "s":
            print("Obra anónima")
        else:
            for autor in autores_seleccionados:
                print(autor["nombre"], autor["apellido"] or "")

    if id_obra_existente is not None:
        return {"id_obra": id_obra_existente, "titulo": obra[1]}
    return {
        "id_obra": None, "titulo": titulo_obra,
        "anio_original": anio_original, "idioma_original": idioma_original,
        "genero": genero, "estado_lectura": estado_lectura,
        "valoracion": valoracion, "comentario": comentario,
        "temas": temas, "autores": autores_seleccionados
    }
# Reunimos todas las obras antes de guardar la edición.
obras_seleccionadas = []
while True:
    nueva = cargar_obra()
    repetida = nueva["id_obra"] is not None and any(
        o["id_obra"] == nueva["id_obra"] for o in obras_seleccionadas
    )
    if repetida:
        print("Esa obra ya está incluida en esta edición.")
    else:
        obras_seleccionadas.append(nueva)
    print("\nObras de esta edición:")
    for o in obras_seleccionadas:
        print("-", o["titulo"])
    otro = input("¿Esta edición contiene otra obra? (s/n): ").strip().lower()
    while otro not in ["s", "n"]:
        otro = input("Ingresá s o n: ").strip().lower()
    if otro == "n":
        break

anio_edicion = convertir_anio(anio_edicion, "Año de tu edición")
# Revisamos si ese ISBN ya está cargado
edicion_existente = conexion.execute(
    "SELECT id_edicion FROM ediciones WHERE isbn = ?",
    [isbn]
).fetchone()
if edicion_existente is not None:
    print("Ese ISBN ya está registrado. No se agregó nuevamente.")
else:
    conexion.execute("BEGIN TRANSACTION")
    try:
        # Guardamos la edición y obtenemos su ID
        id_edicion = conexion.execute("""
            INSERT INTO ediciones (
                isbn, titulo, editorial, anio_publicacion,
                idioma, portada, notas
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            RETURNING id_edicion
        """, [
            isbn or None,
            titulo_edicion,
            editorial or None,
            anio_edicion,
            idioma_edicion or None,
            portada_edicion or None,
            notas_edicion or None
        ]).fetchone()[0]
        autores_creados = {}
        for obra_cargada in obras_seleccionadas:
            id_obra_existente = obra_cargada["id_obra"]
            if id_obra_existente is None:
                titulo_obra = obra_cargada["titulo"]
                anio_original = obra_cargada["anio_original"]
                idioma_original = obra_cargada["idioma_original"]
                genero = obra_cargada["genero"]
                estado_lectura = obra_cargada["estado_lectura"]
                valoracion = obra_cargada["valoracion"]
                comentario = obra_cargada["comentario"]
                temas = obra_cargada["temas"]
                autores_seleccionados = obra_cargada["autores"]
            if id_obra_existente is not None:
                id_obra = id_obra_existente
            else:
                # Guardamos la obra y obtenemos su ID
                id_obra = conexion.execute("""
                    INSERT INTO obras (
                        titulo, anio_publicacion_original, idioma_original,
                        genero, estado_lectura, valoracion, comentario_personal
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    RETURNING id_obra
                """, [
                    titulo_obra,
                    anio_original,
                    idioma_original or None,
                    genero,
                    estado_lectura,
                    valoracion,
                    comentario or None
                ]).fetchone()[0]
                # Guardamos o reutilizamos los temas
                for tema in temas:
                    existente = conexion.execute("""
                        SELECT id_tema
                        FROM temas
                        WHERE lower(nombre) = lower(?)
                    """, [tema]).fetchone()
                    if existente is None:
                        id_tema = conexion.execute("""
                            INSERT INTO temas (nombre)
                            VALUES (?)
                            RETURNING id_tema
                        """, [tema]).fetchone()[0]
                    else:
                        id_tema = existente[0]
                    conexion.execute("""
                        INSERT INTO trata_sobre (id_obra, id_tema)
                        VALUES (?, ?)
                        ON CONFLICT DO NOTHING
                    """, [id_obra, id_tema])
                # Guardamos o reutilizamos los autores
                for autor in autores_seleccionados:
                    firma = (autor["nombre"].casefold(), (autor["apellido"] or "").casefold(), (autor["nacionalidad"] or "").casefold())
                    id_autor = autor["id_autor"]
                    if id_autor is None:
                        id_autor = autores_creados.get(firma)
                    if id_autor is None:
                        # Buscamos coincidencias antes de crear otro autor
                        coincidencias = conexion.execute("""
                            SELECT id_autor
                            FROM autores
                            WHERE lower(nombre) = lower(?)
                              AND lower(coalesce(apellido, '')) = lower(?)
                        """, [
                            autor["nombre"],
                            autor["apellido"] or ""
                        ]).fetchall()
                        if coincidencias:
                            raise ValueError(
                                "Ya hay un autor con ese nombre y apellido. "
                                "Volvé a cargar seleccionándolo de la lista. "
                                "Si es otra persona, tenemos que distinguirlos."
                            )
                        id_autor = conexion.execute("""
                            INSERT INTO autores (nombre, apellido, nacionalidad)
                            VALUES (?, ?, ?)
                            RETURNING id_autor
                        """, [
                            autor["nombre"],
                            autor["apellido"],
                            autor["nacionalidad"]
                        ]).fetchone()[0]
                        autores_creados[firma] = id_autor
                    conexion.execute("""
                        INSERT INTO escribe (id_autor, id_obra)
                        VALUES (?, ?)
                        ON CONFLICT DO NOTHING
                    """, [id_autor, id_obra])
    
            # Vinculamos la edición con la obra
            conexion.execute("""
                INSERT INTO contiene (id_edicion, id_obra)
                VALUES (?, ?)
            """, [id_edicion, id_obra])
        conexion.execute("COMMIT")
        print("\n¡Libro guardado en la biblioteca!")
    except Exception as error:
        conexion.execute("ROLLBACK")
        print("\nNo se guardó la carga:", error)
print("\nLibros registrados:")
print(conexion.execute("""
    SELECT
        e.id_edicion,
        e.titulo AS edicion,
        e.isbn,
        o.titulo AS obra,
        o.estado_lectura
    FROM ediciones e
    JOIN contiene c ON c.id_edicion = e.id_edicion
    JOIN obras o ON o.id_obra = c.id_obra
    ORDER BY e.id_edicion
""").df())
conexion.close()
