CREATE SEQUENCE IF NOT EXISTS seq_autor START 1;
CREATE SEQUENCE IF NOT EXISTS seq_obra START 1;
CREATE SEQUENCE IF NOT EXISTS seq_tema START 1;
CREATE SEQUENCE IF NOT EXISTS seq_edicion START 1;

CREATE TABLE IF NOT EXISTS autores (
    id_autor INTEGER PRIMARY KEY DEFAULT nextval('seq_autor'),
    nombre VARCHAR NOT NULL,
    apellido VARCHAR,
    nacionalidad VARCHAR
);

CREATE TABLE IF NOT EXISTS obras (
    id_obra INTEGER PRIMARY KEY DEFAULT nextval('seq_obra'),
    titulo VARCHAR NOT NULL,
    anio_publicacion_original INTEGER,
    idioma_original VARCHAR,
    genero VARCHAR NOT NULL,
    estado_lectura VARCHAR NOT NULL DEFAULT 'pendiente'
        CHECK (estado_lectura IN (
            'pendiente', 'en lectura', 'leído', 'abandonado'
        )),
    valoracion INTEGER CHECK (valoracion BETWEEN 1 AND 5),
    comentario_personal VARCHAR
);

CREATE TABLE IF NOT EXISTS temas (
    id_tema INTEGER PRIMARY KEY DEFAULT nextval('seq_tema'),
    nombre VARCHAR NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS ediciones (
    id_edicion INTEGER PRIMARY KEY DEFAULT nextval('seq_edicion'),
    isbn VARCHAR UNIQUE,
    titulo VARCHAR NOT NULL,
    editorial VARCHAR,
    anio_publicacion INTEGER,
    idioma VARCHAR,
    portada VARCHAR,
    notas VARCHAR
);

CREATE TABLE IF NOT EXISTS escribe (
    id_autor INTEGER REFERENCES autores(id_autor),
    id_obra INTEGER REFERENCES obras(id_obra),
    PRIMARY KEY (id_autor, id_obra)
);

CREATE TABLE IF NOT EXISTS contiene (
    id_edicion INTEGER REFERENCES ediciones(id_edicion),
    id_obra INTEGER REFERENCES obras(id_obra),
    PRIMARY KEY (id_edicion, id_obra)
);

CREATE TABLE IF NOT EXISTS trata_sobre (
    id_obra INTEGER REFERENCES obras(id_obra),
    id_tema INTEGER REFERENCES temas(id_tema),
    PRIMARY KEY (id_obra, id_tema)
);