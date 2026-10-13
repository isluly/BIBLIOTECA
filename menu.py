"""Menú de la biblioteca personal. Ejecutar: python menu.py."""
from pathlib import Path
import subprocess
import sys
import duckdb as dd

RAIZ = Path(__file__).parent
RUTA_BASE = RAIZ / "data" / "biblioteca.duckdb"


def ver_biblioteca():
    if not RUTA_BASE.exists():
        print("Primero ejecutá biblioteca.py para crear la base.")
        return

    conexion = dd.connect(str(RUTA_BASE), read_only=True)
    try:
        libros = conexion.execute("""
            WITH progreso AS (
                SELECT c.id_edicion,
                    count(*) AS total,
                    count(*) FILTER (WHERE o.estado_lectura = 'leído') AS leidas,
                    count(*) FILTER (WHERE o.estado_lectura = 'en lectura') AS en_curso,
                    count(*) FILTER (WHERE o.estado_lectura = 'abandonado') AS abandonadas
                FROM contiene c
                JOIN obras o ON o.id_obra = c.id_obra
                GROUP BY c.id_edicion
            ), nombres AS (
                SELECT DISTINCT c.id_edicion,
                    trim(a.nombre || ' ' || coalesce(a.apellido, '')) AS autor
                FROM contiene c
                JOIN escribe es ON es.id_obra = c.id_obra
                JOIN autores a ON a.id_autor = es.id_autor
            ), autoria AS (
                SELECT id_edicion, string_agg(autor, ', ' ORDER BY autor) AS autores
                FROM nombres GROUP BY id_edicion
            )
            SELECT e.id_edicion, e.titulo,
                coalesce(a.autores, 'Sin autor registrado') AS autores,
                CASE
                    WHEN p.leidas = p.total THEN 'Leído'
                    WHEN p.leidas > 0 THEN 'Parcialmente leído'
                    WHEN p.en_curso > 0 THEN 'En lectura'
                    WHEN p.abandonadas > 0 THEN 'Abandonado'
                    ELSE 'Pendiente'
                END AS estado,
                p.leidas, p.total
            FROM ediciones e
            JOIN progreso p ON p.id_edicion = e.id_edicion
            LEFT JOIN autoria a ON a.id_edicion = e.id_edicion
            ORDER BY lower(e.titulo), e.id_edicion
        """).fetchall()
    finally:
        conexion.close()

    if not libros:
        print("\nTu biblioteca todavía está vacía.")
        return

    print(f"\nMI BIBLIOTECA — {len(libros)} ediciones")
    for identificador, titulo, autores, estado, leidas, total in libros:
        print(f"\n[{identificador}] {titulo}")
        print(f"  Autores: {autores}")
        print(f"  Lectura: {estado} — {leidas} de {total} obras leídas")


def cargar_libro():
    archivo = RAIZ / "buscar_isbn.py"
    if not archivo.exists():
        print("Poné buscar_isbn.py en la misma carpeta que menu.py.")
        return
    # Usamos el mismo Python y entorno virtual con que abriste este menú.
    subprocess.run([sys.executable, str(archivo)], cwd=str(RAIZ))

def actualizar_lectura():
    if not RUTA_BASE.exists():
        print("Primero ejecutá biblioteca.py para crear la base.")
        return

    conexion = dd.connect(str(RUTA_BASE))

    try:
        obras = conexion.execute("""
            SELECT
                o.id_obra,
                o.titulo,
                o.estado_lectura,
                o.valoracion,
                (
                    SELECT string_agg(
                        trim(a.nombre || ' ' || coalesce(a.apellido, '')),
                        ', '
                    )
                    FROM escribe es
                    JOIN autores a ON a.id_autor = es.id_autor
                    WHERE es.id_obra = o.id_obra
                ) AS autores
            FROM obras o
            ORDER BY lower(o.titulo), o.id_obra
        """).fetchall()

        if not obras:
            print("Todavía no hay obras registradas.")
            return

        print("\nElegí una obra:")
        for numero, obra in enumerate(obras, start=1):
            print(
                f"{numero}. {obra[1]} — "
                f"{obra[4] or 'Sin autor registrado'} — {obra[2]}"
            )
        print("0. Volver")

        opcion = input("Número de la obra: ").strip()
        while (
            not opcion.isdigit()
            or not 0 <= int(opcion) <= len(obras)
        ):
            opcion = input("Ingresá un número de la lista: ").strip()

        if opcion == "0":
            return

        obra = obras[int(opcion) - 1]
        id_obra = obra[0]

        # Estado de lectura
        estados = ["pendiente", "en lectura", "leído", "abandonado"]

        print(f"\nEstado actual: {obra[2]}")
        for numero, estado in enumerate(estados, start=1):
            print(f"{numero}. {estado}")

        opcion_estado = input(
            "Nuevo estado (Enter conserva el actual): "
        ).strip()

        while opcion_estado not in ["", "1", "2", "3", "4"]:
            opcion_estado = input(
                "Ingresá 1 a 4 o Enter para conservar: "
            ).strip()

        estado = obra[2]
        if opcion_estado != "":
            estado = estados[int(opcion_estado) - 1]

        # Valoración
        print(
            "\nValoración actual:",
            obra[3] if obra[3] is not None else "Sin valoración"
        )

        entrada = input(
            "Nueva valoración: 1 a 5, 0 para quitar, "
            "Enter para conservar: "
        ).strip()

        while entrada not in ["", "0", "1", "2", "3", "4", "5"]:
            entrada = input("Ingresá 0 a 5 o Enter: ").strip()

        valoracion = obra[3]
        if entrada == "0":
            valoracion = None
        elif entrada != "":
            valoracion = int(entrada)

        conexion.execute("""
            UPDATE obras
            SET estado_lectura = ?, valoracion = ?
            WHERE id_obra = ?
        """, [estado, valoracion, id_obra])

        print(f"\nActualizaste «{obra[1]}».")
        print("Estado:", estado)
        print(
            "Valoración:",
            valoracion if valoracion is not None else "Sin valoración"
        )

    finally:
        conexion.close()

def main():
    while True:
        print("\nBIBLIOTECA PERSONAL")
        print("1. Cargar un libro por ISBN")
        print("2. Ver mi biblioteca")
        print("3. Actualizar lectura y valoración")
        print("0. Salir")
        opcion = input("Elegí una opción: ").strip()
        if opcion == "1":
            cargar_libro()
        elif opcion == "2":
            ver_biblioteca()
        elif opcion == "3":
            actualizar_lectura()
        elif opcion == "0":
            print("¡Hasta luego!")
            break
        else:
            print("Ingresá 1, 2, 3 o 0.")


if __name__ == "__main__":
    main()
