from flask import current_app
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg
from datetime import datetime
import json
import os


def crear_pdf(ruta_pdf, info_path):
    styles = getSampleStyleSheet()

    styles["Heading1"].textColor = colors.HexColor("#071E51")
    styles["Heading2"].textColor = colors.HexColor("#FECE00")

    styles["Normal"].alignment = 4
    styles["Normal"].fontSize = 10

    normal = styles["Normal"]
    title = styles["Heading1"]
    subtitle = styles["Heading2"]

    # Configurar el documento
    doc = BaseDocTemplate(
        ruta_pdf,
        pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=35*mm, bottomMargin=20*mm
    )

    # Marco principal del contenido
    frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        doc.width, doc.height - 15*mm,   # Dejamos espacio para el encabezado
        id='normal'
    )
    current_app.logger.info("creando encabezado")
    # === ENCABEZADO ===
    def header(canvas, doc):
        canvas.saveState()

        # Título a la izquierda
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawString(doc.leftMargin, A4[1] - 25*mm, "Cártedra de Correos y Telégrafos de la UAH")

        # Cargar y dibujar imágenes SVG
        base_static = current_app.config.get("STATIC_FOLDER")
        img1_path = os.path.join(base_static, 'img', 'logo_correos.png')
        img2_path = os.path.join(base_static, 'img', 'logo_uah.svg')
        #img1 = svg2rlg(img1_path)
        img2 = svg2rlg(img2_path)

        # Escalar ambas imágenes
        scale = 0.025
        img2.width *= scale
        img2.height *= scale
        img2.scale(scale, scale)

        #current_app.logger.info(img1)
        current_app.logger.info(img2)


        canvas.drawImage(str(img1_path),
                     A4[0] - doc.rightMargin - 28*mm,
                     A4[1] - 30*mm,
                     width=12*mm,
                     height=12*mm,
                     preserveAspectRatio=True,
                     mask='auto')
        renderPDF.draw(img2, canvas, A4[0] - doc.rightMargin - 12*mm, A4[1] - 30*mm)

        # Línea separadora amarilla (#FECE00)
        canvas.setStrokeColor("#FECE00")
        canvas.setLineWidth(2)
        canvas.line(doc.leftMargin, A4[1] - 35*mm, A4[0] - doc.rightMargin, A4[1] - 35*mm)

        canvas.restoreState()
    current_app.logger.info("creando pie de pagina")
    # === PIE DE PÁGINA ===
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 10)
        page_num = canvas.getPageNumber()
        canvas.drawString(doc.leftMargin, 15*mm, f"Página {page_num}")
        canvas.restoreState()

    template = PageTemplate(id='template', frames=[frame], onPage=header, onPageEnd=footer)
    doc.addPageTemplates([template])

    # === CONTENIDO PRINCIPAL ===
    current_app.logger.info("creando contenido principal")
    story = []

    ahora = datetime.now()
    fecha_str = ahora.strftime("%d/%m/%Y")
    hora_str = ahora.strftime("%H:%M:%S")

    story.append(Paragraph(f"Fecha: {fecha_str}", normal))
    story.append(Paragraph(f"Hora: {hora_str}", normal))
    story.append(Spacer(1, 6))

    story.append(Paragraph("Estadísticas del preprocesado de los ficheros", title))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Unión datos de B y C", subtitle))
    story.append(Spacer(1, 4))

    # Introduccion para contexto
    intro_text_BC = """
    El primer paso del preprocesado consiste en realizar la unión de los ficheros B y C. 
    En el fichero B se cuenta con los siguientes campos importantes para el proceso: código de unidad, PDA, fecha y tiempo transcurrido. 
    Por otro lado, en el fichero C se cuenta con los siguientes campos importantes para el proceso: código de unidad, PDA, fecha, latitud y lontiud.<br/>
    Como resultado de esta unión surge un conjunto de datos que a partir de ahora se denominará conjunto D. 
    """
    story.append(Paragraph(intro_text_BC, normal))
    # Estadisticas
    info_D = getInfo(info_path, 'D')
    story.append(Paragraph(info_D, normal))

    story.append(Spacer(1, 6))
    story.append(Paragraph("Unión datos de A y D", subtitle))
    story.append(Spacer(1, 4))

    # Introduccion para contexto
    intro_text_AD = """
    El segundo paso del preprocesado consiste en realizar la unión de los datos del fichero A con los datos del conjunto D. 
    En el fichero A se cuenta con los siguientes campos importantes para el proceso: código de unidad, PDA, fecha, latitud y longitud. 
    Por otro lado, en el fichero D se cuenta con los siguientes campos importantes para el proceso: código de unidad, PDA, fecha, latitud, lontiud y tiempo transcurrido.<br/>
    Como resultado de esta unión surge un conjunto de datos que a partir de ahora se denominará conjunto final. 
    """
    story.append(Paragraph(intro_text_AD, normal))
    # Estadisticas
    info_E = getInfo(info_path, 'E')
    story.append(Paragraph(info_E, normal))
    current_app.logger.info("escribiendo")
    doc.build(story)




def getInfo(path, type):
    full_path = os.path.join(path, f'{type}_statistics.json')
    with open(full_path, "r", encoding="utf-8") as f:
        my_dict = json.load(f)

    info=""""""

    if type == 'D':
        info = f"""
        <br/>
        Información de lectura de los datos:<br/>
        - Registros totales: {my_dict["Informacion inicial"]["Conteo de registros"]["Registros totales"]}.<br/>
        \t - Pertenecientes al fichero B: {my_dict["Informacion inicial"]["Conteo de registros"]["Registros B"]}.<br/>
        \t - Pertenecientes al fichero C: {my_dict["Informacion inicial"]["Conteo de registros"]["Registros C"]}.<br/>
        - Códigos de unidad:<br/>
        \t - Pertenecientes al fichero B: {my_dict["Informacion inicial"]["Conteo codireds"]["Num codireds encontrados en fichero B"]}.<br/>
        \t - Lista: {my_dict["Informacion inicial"]["Conteo codireds"]["Codireds en fichero B"]}.<br/>
        \t - Pertenecientes al fichero C: {my_dict["Informacion inicial"]["Conteo codireds"]["Num codireds encontrados en fichero C"]}.<br/>
        \t - Lista: {my_dict["Informacion inicial"]["Conteo codireds"]["Codireds en fichero C"]}.<br/>
        \t - Compartidos: {my_dict["Informacion inicial"]["Conteo codireds"]["Num codireds compartidos"]}.<br/>
        \t - Lista: {my_dict["Informacion inicial"]["Conteo codireds"]["Codireds compartidos"]}.<br/>
        - PDAs:<br/>
        \t - Pertenecientes al fichero B: {my_dict["Informacion inicial"]["Conteo PDAs"]["Num PDAs encontradas en el fichero B"]}.<br/>
        \t - Lista: {my_dict["Informacion inicial"]["Conteo PDAs"]["PDAs en fichero B"]}.<br/>
        \t - Pertenecientes al fichero C: {my_dict["Informacion inicial"]["Conteo PDAs"]["Num PDAs encontradas en el fichero C"]}.<br/>
        \t - Lista: {my_dict["Informacion inicial"]["Conteo PDAs"]["PDAs en fichero C"]}.<br/>
        \t - Compartidos: {my_dict["Informacion inicial"]["Conteo PDAs"]["Num PDAs compartida"]}.<br/>
        \t - Lista: {my_dict["Informacion inicial"]["Conteo PDAs"]["PDAs compartidas"]}.<br/>
        - Fechas:<br/>
        \t - Pertenecientes al fichero B: {my_dict["Informacion inicial"]["Conteo fechas"]["Num fechas en fichero B"]}.<br/>
        \t - Primera fecha: {my_dict["Informacion inicial"]["Conteo fechas"]["Primera fecha en fichero B"]}.<br/>
        \t - Última fecha: {my_dict["Informacion inicial"]["Conteo fechas"]["Ultima fecha en fichero B"]}.<br/>
        \t - Pertenecientes al fichero C: {my_dict["Informacion inicial"]["Conteo fechas"]["Num fechas en fichero C"]}.<br/>
        \t - Primera fecha: {my_dict["Informacion inicial"]["Conteo fechas"]["Primera fecha en fichero C"]}.<br/>
        \t - Última fecha: {my_dict["Informacion inicial"]["Conteo fechas"]["Ultima fecha en fichero C"]}.<br/>
        \t - Compartidas: {my_dict["Informacion inicial"]["Conteo fechas"]["Num fechas compartidas"]}.<br/>
        \t - Primera fecha: {my_dict["Informacion inicial"]["Conteo fechas"]["Primera fecha compartida"]}.<br/>
        \t - Última fecha: {my_dict["Informacion inicial"]["Conteo fechas"]["Ultima fecha compartida"]}.<br/>
        <br/>
        <br/>
        Información de la unión de los datos:<br/>
        - Información duplicada:<br/>
        \t - Duplicados totales: {my_dict["Duplicados"]["Duplicados totales"]}.<br/>
        \t\t - Pertenecientes al conjunto B: {my_dict["Duplicados"]["Duplicados B"]}.<br/>
        \t\t - Pertenecientes al conjunto C: {my_dict["Duplicados"]["Duplicados C"]}.<br/>
        \t\t - Datos totales no duplicados: {my_dict["Duplicados"]["Registros totales no duplicados"]}.<br/>
        \t\t - Datos no duplicados del conjunto B: {my_dict["Duplicados"]["Registros B no duplicados"]}.<br/>
        \t\t - Datos no duplicados del conjunto C: {my_dict["Duplicados"]["Registros C no duplicados"]}.<br/>
        \t - Informacion de sincronización (eliminar PDAs y fechas no compartidas):<br/>
        \t\t - Registros totales: {my_dict["Información de sincronizacion"]["Conteo de registros"]["Registros totales"]}.<br/>
        \t\t\t - Pertenecientes al fichero B: {my_dict["Información de sincronizacion"]["Conteo de registros"]["Registros B"]}.<br/>
        \t\t\t - Pertenecientes al fichero C: {my_dict["Información de sincronizacion"]["Conteo de registros"]["Registros C"]}.<br/>
        \t\t - Códigos de unidad:<br/>
        \t\t\t - Pertenecientes al fichero B: {my_dict["Información de sincronizacion"]["Conteo codireds"]["Num codireds encontrados en fichero B"]}.<br/>
        \t\t\t - Lista: {my_dict["Información de sincronizacion"]["Conteo codireds"]["Codireds en fichero B"]}.<br/>
        \t\t\t - Pertenecientes al fichero C: {my_dict["Información de sincronizacion"]["Conteo codireds"]["Num codireds encontrados en fichero C"]}.<br/>
        \t\t\t - Lista: {my_dict["Información de sincronizacion"]["Conteo codireds"]["Codireds en fichero C"]}.<br/>
        \t\t\t - Compartidos: {my_dict["Información de sincronizacion"]["Conteo codireds"]["Num codireds compartidos"]}.<br/>
        \t\t\t - Lista: {my_dict["Información de sincronizacion"]["Conteo codireds"]["Codireds compartidos"]}.<br/>
        \t\t- PDAs:<br/>
        \t\t\t - Pertenecientes al fichero B: {my_dict["Información de sincronizacion"]["Conteo PDAs"]["Num PDAs encontradas en el fichero B"]}.<br/>
        \t\t\t - Lista: {my_dict["Información de sincronizacion"]["Conteo PDAs"]["PDAs en fichero B"]}.<br/>
        \t\t\t - Pertenecientes al fichero C: {my_dict["Información de sincronizacion"]["Conteo PDAs"]["Num PDAs encontradas en el fichero C"]}.<br/>
        \t\t\t - Lista: {my_dict["Información de sincronizacion"]["Conteo PDAs"]["PDAs en fichero C"]}.<br/>
        \t\t\t - Compartidos: {my_dict["Información de sincronizacion"]["Conteo PDAs"]["Num PDAs compartida"]}.<br/>
        \t\t\t - Lista: {my_dict["Información de sincronizacion"]["Conteo PDAs"]["PDAs compartidas"]}.<br/>
        \t\t - Fechas:<br/>
        \t\t\t - Pertenecientes al fichero B: {my_dict["Información de sincronizacion"]["Conteo fechas"]["Num fechas en fichero B"]}.<br/>
        \t\t\t - Primera fecha: {my_dict["Información de sincronizacion"]["Conteo fechas"]["Primera fecha en fichero B"]}.<br/>
        \t\t\t - Última fecha: {my_dict["Información de sincronizacion"]["Conteo fechas"]["Ultima fecha en fichero B"]}.<br/>
        \t\t\t - Pertenecientes al fichero C: {my_dict["Información de sincronizacion"]["Conteo fechas"]["Num fechas en fichero C"]}.<br/>
        \t\t\t - Primera fecha: {my_dict["Información de sincronizacion"]["Conteo fechas"]["Primera fecha en fichero C"]}.<br/>
        \t\t\t - Última fecha: {my_dict["Información de sincronizacion"]["Conteo fechas"]["Ultima fecha en fichero C"]}.<br/>
        \t\t\t - Compartidas: {my_dict["Información de sincronizacion"]["Conteo fechas"]["Num fechas compartidas"]}.<br/>
        \t\t\t - Primera fecha: {my_dict["Información de sincronizacion"]["Conteo fechas"]["Primera fecha compartida"]}.<br/>
        \t\t\t - Última fecha: {my_dict["Información de sincronizacion"]["Conteo fechas"]["Ultima fecha compartida"]}.<br/>
        \t - Informacion de correspondencia de registros en la unión:<br/>
        \t\t - Registros totales no usados en la union: {my_dict["Registros_no_usados"]["Totales no usados en la union"]}.<br/>
        \t\t - Registros del conjunto B no usados en la union: {my_dict["Registros_no_usados"]["B_no_usados en la union"]}.<br/>
        \t\t - Registros del conjunto C no usados en la union: {my_dict["Registros_no_usados"]["C_no_usados en la union"]}.<br/>
        <br/>
        <br/>
        - Registros finales: {my_dict["Registros_finales"]}.<br/>
        """
    elif type == 'E':
        info= f"""
        <br/>
        Información de lectura de los datos:<br/>
        - Registros totales: {my_dict["Informacion inicial"]["Conteo de registros"]["Registros totales"]}.<br/>
        \t - Pertenecientes al fichero A: {my_dict["Informacion inicial"]["Conteo de registros"]["Registros B"]}.<br/>
        \t - Pertenecientes al conjunto D: {my_dict["Informacion inicial"]["Conteo de registros"]["Registros C"]}.<br/>
        - Códigos de unidad:<br/>
        \t - Pertenecientes al fichero A: {my_dict["Informacion inicial"]["Conteo codireds"]["Num codireds encontrados en fichero B"]}.<br/>
        \t - Lista: {my_dict["Informacion inicial"]["Conteo codireds"]["Codireds en fichero B"]}.<br/>
        \t - Pertenecientes al fichero D: {my_dict["Informacion inicial"]["Conteo codireds"]["Num codireds encontrados en fichero C"]}.<br/>
        \t - Lista: {my_dict["Informacion inicial"]["Conteo codireds"]["Codireds en fichero C"]}.<br/>
        \t - Compartidos: {my_dict["Informacion inicial"]["Conteo codireds"]["Num codireds compartidos"]}.<br/>
        \t - Lista: {my_dict["Informacion inicial"]["Conteo codireds"]["Codireds compartidos"]}.<br/>
        - PDAs:<br/>
        \t - Pertenecientes al fichero A: {my_dict["Informacion inicial"]["Conteo PDAs"]["Num PDAs encontradas en el fichero B"]}.<br/>
        \t - Lista: {my_dict["Informacion inicial"]["Conteo PDAs"]["PDAs en fichero B"]}.<br/>
        \t - Pertenecientes al fichero D: {my_dict["Informacion inicial"]["Conteo PDAs"]["Num PDAs encontradas en el fichero C"]}.<br/>
        \t - Lista: {my_dict["Informacion inicial"]["Conteo PDAs"]["PDAs en fichero C"]}.<br/>
        \t - Compartidos: {my_dict["Informacion inicial"]["Conteo PDAs"]["Num PDAs compartida"]}.<br/>
        \t - Lista: {my_dict["Informacion inicial"]["Conteo PDAs"]["PDAs compartidas"]}.<br/>
        - Fechas:<br/>
        \t - Pertenecientes al fichero A: {my_dict["Informacion inicial"]["Conteo fechas"]["Num fechas en fichero B"]}.<br/>
        \t - Primera fecha: {my_dict["Informacion inicial"]["Conteo fechas"]["Primera fecha en fichero B"]}.<br/>
        \t - Última fecha: {my_dict["Informacion inicial"]["Conteo fechas"]["Ultima fecha en fichero B"]}.<br/>
        \t - Pertenecientes al fichero D: {my_dict["Informacion inicial"]["Conteo fechas"]["Num fechas en fichero C"]}.<br/>
        \t - Primera fecha: {my_dict["Informacion inicial"]["Conteo fechas"]["Primera fecha en fichero C"]}.<br/>
        \t - Última fecha: {my_dict["Informacion inicial"]["Conteo fechas"]["Ultima fecha en fichero C"]}.<br/>
        \t - Compartidas: {my_dict["Informacion inicial"]["Conteo fechas"]["Num fechas compartidas"]}.<br/>
        \t - Primera fecha: {my_dict["Informacion inicial"]["Conteo fechas"]["Primera fecha compartida"]}.<br/>
        \t - Última fecha: {my_dict["Informacion inicial"]["Conteo fechas"]["Ultima fecha compartida"]}.<br/>
        <br/>
        <br/>
        Información de la unión de los datos:<br/>
        - Información duplicada:<br/>
        \t - Duplicados totales: {my_dict["Duplicados"]["Duplicados totales"]}.<br/>
        \t\t - Pertenecientes al conjunto A: {my_dict["Duplicados"]["Duplicados A"]}.<br/>
        \t\t - Pertenecientes al conjunto D: {my_dict["Duplicados"]["Duplicados D"]}.<br/>
        \t\t - Datos totales no duplicados: {my_dict["Duplicados"]["Registros totales no duplicados"]}.<br/>
        \t\t - Datos no duplicados del conjunto A: {my_dict["Duplicados"]["Registros A no duplicados"]}.<br/>
        \t\t - Datos no duplicados del conjunto D: {my_dict["Duplicados"]["Registros D no duplicados"]}.<br/>
        \t - Informacion de sincronización (eliminar PDAs y fechas no compartidas):<br/>
        \t\t - Registros totales: {my_dict["Información de sincronizacion"]["Conteo de registros"]["Registros totales"]}.<br/>
        \t\t\t - Pertenecientes al fichero A: {my_dict["Información de sincronizacion"]["Conteo de registros"]["Registros B"]}.<br/>
        \t\t\t - Pertenecientes al fichero D: {my_dict["Información de sincronizacion"]["Conteo de registros"]["Registros C"]}.<br/>
        \t\t - Códigos de unidad:<br/>
        \t\t\t - Pertenecientes al fichero A: {my_dict["Información de sincronizacion"]["Conteo codireds"]["Num codireds encontrados en fichero B"]}.<br/>
        \t\t\t - Lista: {my_dict["Información de sincronizacion"]["Conteo codireds"]["Codireds en fichero B"]}.<br/>
        \t\t\t - Pertenecientes al fichero D: {my_dict["Información de sincronizacion"]["Conteo codireds"]["Num codireds encontrados en fichero C"]}.<br/>
        \t\t\t - Lista: {my_dict["Información de sincronizacion"]["Conteo codireds"]["Codireds en fichero C"]}.<br/>
        \t\t\t - Compartidos: {my_dict["Información de sincronizacion"]["Conteo codireds"]["Num codireds compartidos"]}.<br/>
        \t\t\t - Lista: {my_dict["Información de sincronizacion"]["Conteo codireds"]["Codireds compartidos"]}.<br/>
        \t\t- PDAs:<br/>
        \t\t\t - Pertenecientes al fichero A: {my_dict["Información de sincronizacion"]["Conteo PDAs"]["Num PDAs encontradas en el fichero B"]}.<br/>
        \t\t\t - Lista: {my_dict["Información de sincronizacion"]["Conteo PDAs"]["PDAs en fichero B"]}.<br/>
        \t\t\t - Pertenecientes al fichero D: {my_dict["Información de sincronizacion"]["Conteo PDAs"]["Num PDAs encontradas en el fichero C"]}.<br/>
        \t\t\t - Lista: {my_dict["Información de sincronizacion"]["Conteo PDAs"]["PDAs en fichero C"]}.<br/>
        \t\t\t - Compartidos: {my_dict["Información de sincronizacion"]["Conteo PDAs"]["Num PDAs compartida"]}.<br/>
        \t\t\t - Lista: {my_dict["Información de sincronizacion"]["Conteo PDAs"]["PDAs compartidas"]}.<br/>
        \t\t - Fechas:<br/>
        \t\t\t - Pertenecientes al fichero A: {my_dict["Información de sincronizacion"]["Conteo fechas"]["Num fechas en fichero B"]}.<br/>
        \t\t\t - Primera fecha: {my_dict["Información de sincronizacion"]["Conteo fechas"]["Primera fecha en fichero B"]}.<br/>
        \t\t\t - Última fecha: {my_dict["Información de sincronizacion"]["Conteo fechas"]["Ultima fecha en fichero B"]}.<br/>
        \t\t\t - Pertenecientes al fichero D: {my_dict["Información de sincronizacion"]["Conteo fechas"]["Num fechas en fichero C"]}.<br/>
        \t\t\t - Primera fecha: {my_dict["Información de sincronizacion"]["Conteo fechas"]["Primera fecha en fichero C"]}.<br/>
        \t\t\t - Última fecha: {my_dict["Información de sincronizacion"]["Conteo fechas"]["Ultima fecha en fichero C"]}.<br/>
        \t\t\t - Compartidas: {my_dict["Información de sincronizacion"]["Conteo fechas"]["Num fechas compartidas"]}.<br/>
        \t\t\t - Primera fecha: {my_dict["Información de sincronizacion"]["Conteo fechas"]["Primera fecha compartida"]}.<br/>
        \t\t\t - Última fecha: {my_dict["Información de sincronizacion"]["Conteo fechas"]["Ultima fecha compartida"]}.<br/>
        <br/>
        <br/>
        - Registros finales: {my_dict["Registros_finales"]}.<br/>
        """
    
    return info