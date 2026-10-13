"""Biblioteca personal. Ejecutar: python -m streamlit run app.py"""
from pathlib import Path
import json
import re
import unicodedata
from html import escape
from urllib.parse import urlencode
from urllib.request import urlopen
import duckdb as dd
import streamlit as st

RAIZ = Path(__file__).parent
BASE = RAIZ / 'data' / 'biblioteca.duckdb'
ESTADOS = ['pendiente', 'en lectura', 'leído', 'abandonado']
st.set_page_config(page_title='Mi biblioteca', page_icon='📚', layout='wide')

st.markdown("""
<style>
:root {color-scheme: light;}
.stApp, [data-testid="stAppViewContainer"] {background:#F7F2E9;color:#283E35;}
[data-testid="stHeader"] {background:rgba(247,242,233,.92);}
section[data-testid="stSidebar"] {background:#E9E2D5;border-right:1px solid #D9CFBF;}
.block-container {padding-top:2.5rem;padding-bottom:4rem;max-width:1440px;}
h1,h2,h3 {font-family:Georgia,'Times New Roman',serif!important;color:#283E35!important;}
h1 {font-size:3rem!important;letter-spacing:-.04em;}
h3 {font-size:1.5rem!important;line-height:1.3!important;}
[data-testid="stMarkdownContainer"],label,[data-testid="stCaptionContainer"] {color:#283E35;}
[data-testid="stCaptionContainer"] {color:#71685D;}
[data-testid="stMetric"] {background:#EEE7DA;border:1px solid #DED4C4;border-radius:14px;padding:16px 20px;}
[data-testid="stMetricValue"] {color:#743D49;font-family:Georgia,serif;}
[data-testid="stVerticalBlockBorderWrapper"] > div {border-color:#DED4C4!important;border-radius:16px!important;}
[data-testid="stForm"], [data-testid="stExpander"] {background:#FFFCF6;border-color:#DED4C4;border-radius:12px;}
div[class*="st-key-libro_"] {background:#FFFCF6;border-radius:16px;}
div[class*="st-key-libro_"] [data-testid="stImage"] {margin:0 auto;}
.stButton button,.stDownloadButton button,[data-testid="stFormSubmitButton"] button {background:#743D49!important;color:#FFF!important;border:1px solid #743D49!important;border-radius:9px;padding:.5rem 1rem;}
.stButton button:hover,.stDownloadButton button:hover,[data-testid="stFormSubmitButton"] button:hover {background:#58303A!important;border-color:#58303A!important;}
button p {color:inherit!important;}
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="select"] > div,textarea {background:#FFFCF6!important;color:#283E35!important;border-color:#CDBFAE!important;}
input,textarea {color:#283E35!important;caret-color:#743D49;}
[data-baseweb="popover"] [role="listbox"], [data-baseweb="menu"] {background:#FFFCF6!important;color:#283E35!important;}
[data-baseweb="tag"] {background:#E4EBDD!important;color:#283E35!important;}
.eyebrow {font-size:.74rem;letter-spacing:.2em;text-transform:uppercase;color:#743D49;font-weight:600;margin-bottom:.3rem;}
.book-cover-empty {height:230px;width:150px;margin:0 auto 20px;background:linear-gradient(140deg,#D6DFCD,#EBE2D1);border-left:8px solid #82937C;border-radius:3px 8px 8px 3px;display:flex;align-items:center;justify-content:center;box-shadow:5px 8px 18px #283E3512;}
.book-cover-empty span {font-family:Georgia,serif;font-size:1.05rem;text-align:center;padding:15px;color:#3C5143;}
.reading-badge {display:inline-block;background:#E6EDDF;color:#3A513F;padding:5px 10px;border-radius:30px;font-size:.8rem;margin:4px 0;}
@media(max-width:700px) {h1 {font-size:2.2rem!important;}.block-container {padding-top:1.5rem;}}
/* Texto blanco en los botones bordó */
.stButton button *,
.stDownloadButton button *,
[data-testid="stFormSubmitButton"] button * {
    color: #FFFFFF !important;
}
</style>
""", unsafe_allow_html=True)



def consultar(sql, valores=()):
    con = dd.connect(str(BASE))
    try:
        return con.execute(sql, valores).fetchall()
    finally:
        con.close()


def ejecutar(sql, valores):
    con = dd.connect(str(BASE))
    try:
        con.execute(sql, valores)
    finally:
        con.close()



def guardar_portada(id_edicion, referencia, archivo=None, quitar=False):
    from io import BytesIO
    from uuid import uuid4
    from urllib.parse import urlparse
    from PIL import Image

    nuevo_archivo = None
    referencia = referencia.strip()
    if quitar:
        if archivo is not None:
            raise ValueError('Para quitar la portada, primero retirá la imagen subida.')
        valor = None
    elif archivo is not None:
        contenido = archivo.getvalue()
        if len(contenido) > 10 * 1024 * 1024:
            raise ValueError('La imagen debe pesar menos de 10 MB.')
        with Image.open(BytesIO(contenido)) as imagen:
            formato = imagen.format
            if formato not in ['PNG', 'JPEG', 'WEBP']:
                raise ValueError('Elegí una imagen PNG, JPG o WebP.')
            if imagen.width * imagen.height > 25_000_000:
                raise ValueError('La imagen es demasiado grande. Usá una versión más pequeña.')
            imagen.verify()
        carpeta = RAIZ / 'data' / 'portadas'
        carpeta.mkdir(parents=True, exist_ok=True)
        extension = {'PNG': '.png', 'JPEG': '.jpg', 'WEBP': '.webp'}[formato]
        nuevo_archivo = carpeta / (uuid4().hex + extension)
        nuevo_archivo.write_bytes(contenido)
        valor = nuevo_archivo.relative_to(RAIZ).as_posix()
    elif referencia:
        direccion = urlparse(referencia)
        if direccion.scheme in ['http', 'https'] and direccion.netloc:
            valor = referencia
        elif (RAIZ / referencia).is_file():
            valor = referencia
        else:
            raise ValueError('Pegá una URL completa (https://...) o subí una imagen.')
    else:
        raise ValueError('Ingresá una portada o marcá Quitar portada.')
    try:
        if not consultar('SELECT 1 FROM ediciones WHERE id_edicion=?', [id_edicion]):
            raise ValueError('No se encontró esa edición.')
        ejecutar('UPDATE ediciones SET portada=? WHERE id_edicion=?', [valor, id_edicion])
    except Exception:
        if nuevo_archivo is not None:
            nuevo_archivo.unlink(missing_ok=True)
        raise


def estado_edicion(obras):
    leidas = sum(o[3] == 'leído' for o in obras)
    if leidas == len(obras):
        return 'Leído'
    if leidas:
        return 'Parcialmente leído'
    if any(o[3] == 'en lectura' for o in obras):
        return 'En lectura'
    if any(o[3] == 'abandonado' for o in obras):
        return 'Abandonado'
    return 'Pendiente'



def normalizar_isbn(valor):
    return ''.join(valor.split()).replace('-', '').upper()


def datos_edicion_catalogo(libro, isbn):
    # Esta fecha es de la edición, nunca de la publicación original de la obra.
    fecha = str(libro.get('publish_date') or '')
    coincidencia = re.search(r'(?<!\d)(\d{4})(?!\d)', fecha)
    idiomas = {'spa': 'Español', 'eng': 'Inglés', 'fre': 'Francés',
               'fra': 'Francés', 'ger': 'Alemán', 'deu': 'Alemán',
               'ita': 'Italiano', 'por': 'Portugués'}
    lenguas = libro.get('languages') or []
    nombres = []
    for lengua in lenguas:
        codigo = lengua.get('key', '').rsplit('/', 1)[-1] if isinstance(lengua, dict) else str(lengua)
        nombres.append(idiomas.get(codigo, codigo))
    return {
        'ed_isbn': isbn,
        'ed_titulo': libro.get('title') or '',
        'ed_editorial': ', '.join(p.get('name','') for p in libro.get('publishers',[]) if p.get('name')),
        'ed_portada': (libro.get('cover') or {}).get('large') or (libro.get('cover') or {}).get('medium') or '',
        'ed_anio': coincidencia.group(1) if coincidencia else '',
        'ed_idioma': ', '.join(nombres),
        'ed_notas': ''
    }


def reiniciar_carga():
    st.session_state.sugerencias = {}
    st.session_state.nuevas_obras = []
    st.session_state.isbn_busqueda = ''
    st.session_state.isbn_fuente = ''
    st.session_state.obras_existentes_carga = []
    st.session_state.version_form_obra = st.session_state.get('version_form_obra', 0) + 1
    for campo,valor in datos_edicion_catalogo({}, '').items():
        st.session_state[campo] = valor


def anio(texto):
    return int(texto.strip()) if texto.strip() else None


def canonico(con, tabla, columna, valor):
    # Solo recibe nombres de tabla/columna definidos por este programa.
    for (existente,) in con.execute(f'SELECT DISTINCT {columna} FROM {tabla}').fetchall():
        if existente and existente.casefold() == valor.casefold():
            return existente
    return valor


def guardar_edicion(edicion, ids, nuevas):
    con = dd.connect(str(BASE))
    con.execute('BEGIN TRANSACTION')
    try:
        if not edicion[1].strip() or not (ids or nuevas):
            raise ValueError('Completá el título y agregá al menos una obra.')
        if edicion[0] and con.execute('SELECT 1 FROM ediciones WHERE isbn=?', [edicion[0]]).fetchone():
            raise ValueError('Ese ISBN ya está registrado.')
        eid = con.execute('''INSERT INTO ediciones
            (isbn,titulo,editorial,anio_publicacion,idioma,portada,notas)
            VALUES (?,?,?,?,?,?,?) RETURNING id_edicion''', edicion).fetchone()[0]
        autores_nuevos = {}
        for obra in nuevas:
            genero = canonico(con, 'obras', 'genero', obra['genero'])
            oid = con.execute('''INSERT INTO obras
                (titulo,anio_publicacion_original,idioma_original,genero,estado_lectura,valoracion,comentario_personal)
                VALUES (?,?,?,?,?,?,?) RETURNING id_obra''', [
                obra['titulo'], obra['anio'], obra['idioma'] or None, genero,
                obra['estado'], obra['valoracion'], obra['comentario'] or None
            ]).fetchone()[0]
            ids.append(oid)
            for tema in obra['temas']:
                tema = canonico(con, 'temas', 'nombre', tema)
                fila = con.execute('SELECT id_tema FROM temas WHERE nombre=?', [tema]).fetchone()
                tid = fila[0] if fila else con.execute('INSERT INTO temas(nombre) VALUES (?) RETURNING id_tema', [tema]).fetchone()[0]
                con.execute('INSERT INTO trata_sobre VALUES (?,?) ON CONFLICT DO NOTHING', [oid,tid])
            aids = list(obra['autores'])
            if obra['nuevo_autor']:
                nombre, apellido, nacionalidad = obra['nuevo_autor']
                firma = (nombre.casefold(), apellido.casefold(), nacionalidad.casefold())
                coincidencias = con.execute('''SELECT id_autor FROM autores
                    WHERE lower(nombre)=lower(?) AND lower(coalesce(apellido,''))=lower(?)''', [nombre,apellido]).fetchall()
                if coincidencias and firma not in autores_nuevos:
                    raise ValueError(f'Ya existe un autor llamado {nombre} {apellido}. Seleccionalo en la lista.')
                if firma in autores_nuevos:
                    aid = autores_nuevos[firma]
                else:
                    aid = con.execute('INSERT INTO autores(nombre,apellido,nacionalidad) VALUES (?,?,?) RETURNING id_autor',
                        [nombre,apellido or None,nacionalidad or None]).fetchone()[0]
                    autores_nuevos[firma] = aid
                aids.append(aid)
            for aid in set(aids):
                con.execute('INSERT INTO escribe VALUES (?,?)', [aid,oid])
        for oid in set(ids):
            con.execute('INSERT INTO contiene VALUES (?,?)', [eid,oid])
        con.execute('COMMIT')
    except Exception:
        con.execute('ROLLBACK')
        raise
    finally:
        con.close()




def clave_alfabetica(texto):
    texto = unicodedata.normalize('NFD', texto.casefold())
    return ''.join(c for c in texto if not unicodedata.combining(c))


def obtener_obras_pdf():
    # Una fila por obra, sin pasar por ediciones.
    registros = consultar('SELECT id_obra,titulo FROM obras')
    autoria = consultar("""
        SELECT es.id_obra,a.id_autor,a.nombre,a.apellido
        FROM escribe es JOIN autores a ON a.id_autor=es.id_autor
    """)
    filas = []
    for oid,titulo in registros:
        lista = [a for a in autoria if a[0] == oid]
        lista.sort(key=lambda a:(clave_alfabetica((a[3] or '').strip() or a[2]),clave_alfabetica(a[2]),a[1]))
        nombres = ['{}, {}'.format(a[3].strip(),a[2]) if a[3] and a[3].strip() else a[2] for a in lista]
        if lista:
            primero=lista[0]
            orden=(clave_alfabetica((primero[3] or '').strip() or primero[2]),clave_alfabetica(primero[2]))
        else:
            orden=('anonimo','')
        filas.append((orden,clave_alfabetica(titulo),oid,titulo,'; '.join(nombres) or 'Anónimo'))
    filas.sort(key=lambda f:(f[0],f[1],f[2]))
    return [(f[2],f[3],f[4]) for f in filas]


def generar_pdf_obras(filas):
    from io import BytesIO
    from html import escape
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    fuente = 'Helvetica'
    candidatas = [Path('C:/Windows/Fonts/arial.ttf'), Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
    for ruta in candidatas:
        if ruta.exists():
            if 'BibliotecaPDF' not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont('BibliotecaPDF', str(ruta)))
            fuente = 'BibliotecaPDF'
            break
    buffer = BytesIO()
    documento = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36,
        leftMargin=36, topMargin=36, bottomMargin=36, title='Mi biblioteca - Obras')
    estilos = getSampleStyleSheet()
    celda = ParagraphStyle('Libro', fontName=fuente, fontSize=10, leading=14)
    titulo = ParagraphStyle('TituloBiblioteca', fontName=fuente, fontSize=20, leading=25,
        textColor=colors.HexColor('#243d35'))
    datos = [[Paragraph('Autor', celda), Paragraph('Título de obra', celda)]]
    for _,nombre,autoria in filas:
        datos.append([Paragraph(escape(autoria or 'Anónimo'), celda), Paragraph(escape(nombre), celda)])
    tabla = LongTable(datos, colWidths=[213,310], repeatRows=1, splitInRow=1)
    tabla.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e4eee7')),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),10),
        ('RIGHTPADDING',(0,0),(-1,-1),10),
        ('TOPPADDING',(0,0),(-1,-1),9),
        ('BOTTOMPADDING',(0,0),(-1,-1),9),
        ('LINEBELOW',(0,0),(-1,0),0.7,colors.HexColor('#9bb5a4')),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, colors.HexColor('#f7f8f6')]),
    ]))
    subtitulo = ParagraphStyle('Subtitulo', fontName=fuente, fontSize=9, leading=13, textColor=colors.HexColor('#71685D'))
    documento.build([Paragraph('Mi biblioteca', titulo), Spacer(1,6),
        Paragraph('Obras ordenadas alfabéticamente por autor', subtitulo), Spacer(1,18), tabla])
    return buffer.getvalue()

st.markdown('<div class="eyebrow">Una colección personal</div>', unsafe_allow_html=True)
st.title('Mi biblioteca')
st.caption('Tus libros, tus lecturas y las historias que querés volver a encontrar.')
if st.session_state.pop('aviso_portada', False):
    st.success('Portada actualizada.')
if not BASE.exists():
    st.info('Ejecutá biblioteca.py para crear la base y después recargá esta página.')
    st.stop()

st.sidebar.markdown('### Tu biblioteca')
pagina = st.sidebar.radio('Ir a', ['Biblioteca', 'Lectura y valoración', 'Cargar libro'])
obras = consultar('SELECT id_obra,titulo,genero,estado_lectura,valoracion FROM obras ORDER BY lower(titulo),id_obra')
autores = consultar('SELECT id_autor,nombre,apellido,nacionalidad FROM autores ORDER BY apellido,nombre')
temas = consultar('SELECT id_tema,nombre FROM temas ORDER BY nombre')
obra_etiquetas = {o[0]: f'{o[1]} · #{o[0]}' for o in obras}
autor_etiquetas = {a[0]: f"{a[1]} {a[2] or ''}".strip() + f' · #{a[0]}' for a in autores}

if pagina == 'Biblioteca':
    # El PDF incluye todas las obras, independientemente de los filtros.
    exportacion = obtener_obras_pdf()
    if exportacion:
        try:
            pdf = generar_pdf_obras(exportacion)
            st.download_button('Descargar obras en PDF', data=pdf,
                file_name='mi_biblioteca_obras.pdf', mime='application/pdf')
        except ImportError:
            st.info('Para habilitar el PDF, instalá ReportLab: python -m pip install reportlab')
    m1,m2,m3 = st.columns(3)
    m1.metric('Obras',len(obras))
    m2.metric('Autores',len(autores))
    m3.metric('Obras leídas',sum(o[3]=='leído' for o in obras))
    st.write('')
    busqueda = st.text_input('Buscar por título, autor o ISBN', placeholder='Por ejemplo: Bovary')
    with st.sidebar:
        st.subheader('Filtros de obras')
        generos = st.multiselect('Género', sorted({o[2] for o in obras}))
        tema_ids = st.multiselect('Tema', [t[0] for t in temas], format_func=lambda i: dict(temas)[i])
        autor_ids = st.multiselect('Autor', list(autor_etiquetas), format_func=autor_etiquetas.get)
        paises = st.multiselect('Nacionalidad', sorted({a[3] for a in autores if a[3]}))
        estados = st.multiselect('Lectura de la obra', ESTADOS)
    enlaces = consultar('SELECT id_edicion,id_obra FROM contiene')
    escribe = consultar('SELECT id_autor,id_obra FROM escribe')
    trata = consultar('SELECT id_obra,id_tema FROM trata_sobre')
    amap = {a[0]: a for a in autores}
    coincidencias = set()
    for o in obras:
        aids = {a for a,b in escribe if b == o[0]}
        tids = {t for b,t in trata if b == o[0]}
        if generos and o[2] not in generos: continue
        if estados and o[3] not in estados: continue
        if tema_ids and not tids.intersection(tema_ids): continue
        if (autor_ids or paises) and not any(
            (not autor_ids or a in autor_ids) and (not paises or amap[a][3] in paises) for a in aids
        ): continue
        coincidencias.add(o[0])
    ediciones = consultar('SELECT id_edicion,titulo,isbn,editorial,anio_publicacion,idioma,portada,notas FROM ediciones ORDER BY lower(titulo)')
    resultados = []
    for e in ediciones:
        ids = {oid for eid,oid in enlaces if eid == e[0]}
        contenidas = [o for o in obras if o[0] in ids]
        nombres = sorted({autor_etiquetas[aid].rsplit(' · #',1)[0] for aid,oid in escribe if oid in ids})
        texto = ' '.join([e[1], e[2] or '', *nombres, *[o[1] for o in contenidas]]).casefold()
        if busqueda.casefold() not in texto or not ids.intersection(coincidencias): continue
        resultados.append((e,contenidas,nombres))
    st.caption(f'{len(resultados)} de {len(ediciones)} ediciones')
    if not resultados:
        st.info('No hay libros para esta búsqueda. Podés cambiar los filtros o cargar un libro.')
    columnas = st.columns(3)
    for i,(e,contenidas,nombres) in enumerate(resultados):
        with columnas[i % 3]:
            with st.container(border=True, key=f'libro_{e[0]}'):
                if e[6]:
                    try:
                        portada = e[6] if e[6].startswith(('http://','https://')) else str(RAIZ / e[6])
                        st.image(portada, width=150)
                    except Exception:
                        st.caption('Portada no disponible')
                else:
                    st.markdown('<div class="book-cover-empty"><span>'+escape(e[1])+'</span></div>',unsafe_allow_html=True)
                st.subheader(e[1])
                st.write(', '.join(nombres) or 'Sin autor registrado')
                st.caption(' · '.join(str(x) for x in [e[3],e[4],e[5]] if x))
                if e[2]: st.caption('ISBN: '+e[2])
                st.markdown('<span class="reading-badge">'+estado_edicion(contenidas)+'</span>',unsafe_allow_html=True)
                st.caption(f"{sum(o[3]=='leído' for o in contenidas)} de {len(contenidas)} obras leídas")
                with st.expander('Obras y detalles'):
                    for o in contenidas:
                        st.write(f'{o[1]} — {o[3]}')
                    st.write('ISBN:', e[2] or 'Sin ISBN')
                    if e[7]: st.write(e[7])
                if st.button('Editar portada', key=f'abrir_portada_{e[0]}'):
                    st.session_state.edicion_portada = e[0]
                if st.session_state.get('edicion_portada') == e[0]:
                    with st.form(f'portada_{e[0]}'):
                        referencia = st.text_input('URL o ruta de la portada', value=e[6] or '', key=f'url_portada_{e[0]}')
                        archivo = st.file_uploader('O subí una imagen', type=['png', 'jpg', 'jpeg', 'webp'], key=f'archivo_portada_{e[0]}')
                        st.caption('Si subís una imagen, se usa en lugar de la URL. Se guarda con tu biblioteca.')
                        quitar = st.checkbox('Quitar portada', key=f'quitar_portada_{e[0]}')
                        guardar = st.form_submit_button('Guardar portada')
                        cancelar = st.form_submit_button('Cancelar')
                    if cancelar:
                        st.session_state.edicion_portada = None
                        st.rerun()
                    if guardar:
                        try:
                            guardar_portada(e[0], referencia, archivo, quitar)
                            st.session_state.edicion_portada = None
                            st.session_state.aviso_portada = True
                            # Nuevas aperturas mostrarán la referencia recién guardada.
                            st.session_state.pop(f'url_portada_{e[0]}', None)
                            st.session_state.pop(f'archivo_portada_{e[0]}', None)
                            st.session_state.pop(f'quitar_portada_{e[0]}', None)
                            st.rerun()
                        except Exception as error:
                            st.error(f'No se cambió la portada: {error}')

    st.caption('Los filtros combinados deben cumplirse en la misma obra. La lectura de la edición considera todas sus obras.')

elif pagina == 'Lectura y valoración':
    if not obras:
        st.info('Todavía no hay obras registradas.')
    else:
        oid = st.selectbox('Obra', list(obra_etiquetas), format_func=obra_etiquetas.get)
        o = next(o for o in obras if o[0] == oid)
        comentario = consultar('SELECT comentario_personal FROM obras WHERE id_obra=?',[oid])[0][0]
        with st.form(f'lectura_{oid}'):
            estado = st.selectbox('Estado de lectura', ESTADOS, index=ESTADOS.index(o[3]))
            valoracion = st.selectbox('Valoración', [None,1,2,3,4,5], index=([None,1,2,3,4,5].index(o[4])), format_func=lambda v:'Sin valoración' if v is None else f'{v} / 5')
            texto = st.text_area('Comentario personal', comentario or '')
            if st.form_submit_button('Guardar cambios', type='primary'):
                ejecutar('UPDATE obras SET estado_lectura=?,valoracion=?,comentario_personal=? WHERE id_obra=?',[estado,valoracion,texto or None,oid])
                st.success('Cambios guardados. Las ediciones reflejan esta lectura automáticamente.')

else:
    st.session_state.setdefault('sugerencias', {})
    st.session_state.setdefault('nuevas_obras', [])
    st.session_state.setdefault('cache_isbn', {})
    st.session_state.setdefault('version_form_obra', 0)
    # Las claves permanecen explícitas: no dependemos de borrar widgets viejos.
    for campo,valor in datos_edicion_catalogo(st.session_state.sugerencias, st.session_state.get('isbn_carga','')).items():
        st.session_state.setdefault(campo,valor)
    st.button('Iniciar otra carga', on_click=reiniciar_carga,
              help='Descarta el borrador actual. No borra libros guardados.')
    with st.form('consulta_isbn'):
        isbn = st.text_input('ISBN para buscar', key='isbn_busqueda',
            help='Buscá el ISBN o completá directamente Tu edición más abajo.')
        buscar = st.form_submit_button('Buscar datos')
    if buscar:
        limpio = normalizar_isbn(isbn)
        fuente_anterior = st.session_state.get('isbn_fuente', '')
        if st.session_state.nuevas_obras and limpio != fuente_anterior:
            st.error('Hay obras preparadas para la carga actual. Guardá ese libro o pulsá Iniciar otra carga antes de buscar otro ISBN.')
        elif limpio and consultar('SELECT 1 FROM ediciones WHERE isbn=?',[limpio]):
            st.error('Ese ISBN ya está en tu biblioteca. Los datos de la carga actual se conservaron.')
        else:
            libro = {}
            fallo = False
            if limpio:
                if limpio in st.session_state.cache_isbn:
                    libro = st.session_state.cache_isbn[limpio]
                else:
                    try:
                        url = 'https://openlibrary.org/api/books?' + urlencode({'bibkeys':f'ISBN:{limpio}','format':'json','jscmd':'data'})
                        with urlopen(url,timeout=20) as respuesta:
                            libro = json.load(respuesta).get(f'ISBN:{limpio}',{})
                        st.session_state.cache_isbn[limpio] = libro
                    except Exception:
                        fallo = True
            st.session_state.sugerencias = libro
            st.session_state.isbn_fuente = limpio
            st.session_state.version_form_obra += 1
            for campo,valor in datos_edicion_catalogo(libro, limpio).items():
                st.session_state[campo] = valor
            if fallo:
                st.warning('No se pudo consultar el catálogo. El ISBN se conservó para que completes los demás datos a mano.')
            elif libro:
                st.success('Datos encontrados. Revisá Tu edición y agregá las obras que contiene.')
            else:
                st.info('No hay datos en el catálogo. El ISBN se conservó; completá el resto a mano.')
    sugerencias = st.session_state.sugerencias
    if sugerencias.get('publish_date'):
        st.caption('Fecha de edición sugerida: '+str(sugerencias['publish_date']))
    if sugerencias.get('authors'):
        st.caption('Autores sugeridos: '+', '.join(a.get('name','') for a in sugerencias['authors']))
    st.subheader('Obras que contiene')
    ids = st.multiselect('Seleccionar obras ya registradas', list(obra_etiquetas),format_func=obra_etiquetas.get,key='obras_existentes_carga')
    with st.expander('Agregar una obra nueva'):
        with st.form(f"nueva_obra_{st.session_state.version_form_obra}", clear_on_submit=True):
            titulo = st.text_input('Título de la obra', value=sugerencias.get('title','') if not st.session_state.nuevas_obras else '')
            oa = st.text_input('Año original (opcional)')
            idioma = st.text_input('Idioma original')
            genero = st.selectbox('Género', sorted({o[2] for o in obras}), index=None, accept_new_options=True)
            estado = st.selectbox('Lectura',ESTADOS)
            valor = st.selectbox('Puntuación',[None,1,2,3,4,5],format_func=lambda v:'Sin valoración' if v is None else str(v))
            comentario = st.text_area('Comentario')
            ts = st.multiselect('Temas', [t[1] for t in temas],accept_new_options=True)
            nombres_sugeridos = {a.get('name','').strip().casefold() for a in sugerencias.get('authors',[])}
            autores_sugeridos = [a[0] for a in autores if f"{a[1]} {a[2] or ''}".strip().casefold() in nombres_sugeridos]
            ais = st.multiselect('Autores registrados',list(autor_etiquetas),format_func=autor_etiquetas.get,default=autores_sugeridos)
            st.caption('Si falta un autor, completá estos campos. Para una obra anónima, dejá los autores vacíos.')
            nombre = st.text_input('Nombre del autor nuevo')
            apellido = st.text_input('Apellido del autor nuevo')
            nacionalidad = st.text_input('Nacionalidad del autor nuevo')
            agregar = st.form_submit_button('Agregar a esta edición')
        if agregar:
            try:
                if not titulo.strip() or not genero or not ts:
                    raise ValueError('Completá título, género y al menos un tema.')
                if (apellido.strip() or nacionalidad.strip()) and not nombre.strip():
                    raise ValueError('Completá el nombre del autor nuevo.')
                st.session_state.nuevas_obras.append(dict(titulo=titulo.strip(),anio=anio(oa),idioma=idioma.strip(),genero=genero.strip(),estado=estado,valoracion=valor,comentario=comentario,temas=list(dict.fromkeys(t.strip() for t in ts if t.strip())),autores=ais,nuevo_autor=(nombre.strip(),apellido.strip(),nacionalidad.strip()) if nombre.strip() else None))
                st.success('Obra preparada. Guardá la edición para registrarla.')
            except ValueError as error: st.error(str(error))
    for i,o in enumerate(st.session_state.nuevas_obras):
        c1,c2=st.columns([5,1])
        c1.write(f"{i+1}. {o['titulo']} — {o['estado']}")
        if c2.button('Quitar',key=f'quitar_{i}'):
            st.session_state.nuevas_obras.pop(i);st.rerun()
    with st.form('edicion'):
        st.subheader('Tu edición')
        isbn_edicion = st.text_input('ISBN de esta edición',key='ed_isbn',help='Este es el ISBN que se guardará. Podés corregirlo o dejarlo vacío.')
        titulo = st.text_input('Título de la edición',key='ed_titulo')
        editorial = st.text_input('Editorial',key='ed_editorial')
        ea = st.text_input('Año de esta edición',key='ed_anio')
        idioma = st.text_input('Idioma de esta edición',key='ed_idioma')
        portada = st.text_input('URL o ruta de la portada',key='ed_portada')
        notas = st.text_area('Notas de la edición',key='ed_notas')
        guardar = st.form_submit_button('Guardar libro',type='primary')
    if guardar:
        try:
            guardar_edicion([normalizar_isbn(isbn_edicion) or None,titulo.strip(),editorial.strip() or None,anio(ea),idioma.strip() or None,portada.strip() or None,notas.strip() or None],list(ids),st.session_state.nuevas_obras)
            st.session_state.nuevas_obras=[]
            st.success('¡Libro guardado! Ya podés verlo en Biblioteca.')
        except Exception as error: st.error(f'No se guardó la carga: {error}')
