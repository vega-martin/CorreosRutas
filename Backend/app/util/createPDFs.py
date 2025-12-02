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
    subsubtitle = styles["Heading3"]


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

    intro = """
    Entrada:<br/>
    - Fichero A: identifica la ruta de reparto de una PDA de correspondencia no registrada (código de unidad, PDA, fecha, latitud y longitud).<br/>
    - Fichero B: identifica los instantes de entrega de correspondencia registrada (código de unidad, PDA, fecha y tiempo transcurrido).<br/>
    - Fichero C: identifica las coordenadas de entrega de correspondencia registrada (código de unidad, PDA, fecha, latitud y lontiud).<br/>
    <br/>
    Salida:<br/>
    - Fichero D: resultado de la unión de B y C.<br/>
    - Fichero E: resultado de la unión de A y D.<br/>
    """

    story.append(Paragraph(intro, normal))

    story.append(Paragraph("Preproceso de B y C", subtitle))
    story.append(Spacer(1, 4))

    story.append(Paragraph("Proceso de carga de datos de los ficheros B y C.", normal))
    # Estadisticas
    story.append(Paragraph("Información de lectura de los datos", subsubtitle))
    info_D_intro, info_D_union = getInfo(info_path, 'D')
    story.append(Paragraph(info_D_intro, normal))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Unión de datos de B y C >> Fichero D", subsubtitle))
    story.append(Paragraph(info_D_union, normal))


    story.append(Spacer(1, 6))
    story.append(Paragraph("Preproceso de A y D", subtitle))
    story.append(Spacer(1, 4))

    # Introduccion para contexto
    intro_text_AD = """
    El segundo paso del preprocesado consiste en realizar la unión de los datos del fichero A con los datos del fichero D. 
    En el fichero A se cuenta con los siguientes campos importantes para el proceso: código de unidad, PDA, fecha, latitud y longitud. 
    Por otro lado, en el fichero D se cuenta con los siguientes campos importantes para el proceso: código de unidad, PDA, fecha, latitud, lontiud y tiempo transcurrido.<br/>
    Como resultado de esta unión surge un fichero de datos que a partir de ahora se denominará fichero final. 
    """
    story.append(Paragraph(intro_text_AD, normal))
    # Estadisticas
    info_E_intro, info_E_union = getInfo(info_path, 'E')
    story.append(Paragraph("Información de lectura de los datos y preprocesado del fichero A", subsubtitle))
    story.append(Paragraph(info_E_intro, normal))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Unión de datos de A y D >> Fichero E", subsubtitle))
    story.append(Paragraph(info_E_union, normal))


    doc.build(story)




def getInfo(path, type):
    full_path = os.path.join(path, f'{type}_statistics.json')
    with open(full_path, "r", encoding="utf-8") as f:
        my_dict = json.load(f)

    intro="""Información no generada correctamente"""
    union="""Información no generada correctamente"""

    if type == 'D':
        intro = f"""
        Registros totales: {my_dict["Informacion inicial"]["Conteo de registros"]["Registros totales"]}.<br/>
            - Pertenecientes al fichero B: {my_dict["Informacion inicial"]["Conteo de registros"]["Registros B"]}.<br/>
            - Pertenecientes al fichero C: {my_dict["Informacion inicial"]["Conteo de registros"]["Registros C"]}.<br/>
        <br/>
        Códigos de unidad:<br/>
            - Códigos de unidad de B: {my_dict["Informacion inicial"]["Conteo codireds"]["Codireds en fichero B"]}.<br/>
            - Códigos de unidad de C: {my_dict["Informacion inicial"]["Conteo codireds"]["Codireds en fichero C"]}.<br/>
            - Códigos compartidos: {my_dict["Informacion inicial"]["Conteo codireds"]["Codireds compartidos"]}.<br/>
        <br/>
        PDAs:<br/>
           - Pertenecientes al fichero B ({my_dict["Informacion inicial"]["Conteo PDAs"]["Num PDAs encontradas en el fichero B"]}):
        {my_dict["Informacion inicial"]["Conteo PDAs"]["PDAs en fichero B"]}.<br/>
           - Pertenecientes al fichero C ({my_dict["Informacion inicial"]["Conteo PDAs"]["Num PDAs encontradas en el fichero C"]}):
        {my_dict["Informacion inicial"]["Conteo PDAs"]["PDAs en fichero C"]}.<br/>
           - Compartidos ({my_dict["Informacion inicial"]["Conteo PDAs"]["Num PDAs compartida"]}):
        {my_dict["Informacion inicial"]["Conteo PDAs"]["PDAs compartidas"]}.<br/>
        <br/>
        Fechas:<br/>
           - Pertenecientes al fichero B ({my_dict["Informacion inicial"]["Conteo fechas"]["Num fechas en fichero B"]}):
        {my_dict["Informacion inicial"]["Conteo fechas"]["Lista fecha en fichero B"]}.<br/>
           - Pertenecientes al fichero C ({my_dict["Informacion inicial"]["Conteo fechas"]["Num fechas en fichero C"]}):
        {my_dict["Informacion inicial"]["Conteo fechas"]["Lista fecha en fichero C"]}.<br/>
           - Compartidas ({my_dict["Informacion inicial"]["Conteo fechas"]["Num fechas compartidas"]}):
        {my_dict["Informacion inicial"]["Conteo fechas"]["Lista fecha compartida"]}.<br/>
        <br/>
        """
        union = f"""
        Eliminación de duplicados:<br/><br/>
           + Duplicados totales: {my_dict["Duplicados"]["Duplicados totales"]}.<br/>
           - Pertenecientes al fichero B: {my_dict["Duplicados"]["Duplicados B"]}.<br/>
           - Pertenecientes al fichero C: {my_dict["Duplicados"]["Duplicados C"]}.<br/><br/>
           + Datos totales no duplicados: {my_dict["Duplicados"]["Registros totales no duplicados"]}.<br/>
           - Pertenecientes al fichero B: {my_dict["Duplicados"]["Registros B no duplicados"]}.<br/>
           - Pertenecientes al fichero C: {my_dict["Duplicados"]["Registros C no duplicados"]}.<br/>
        <br/>
        Información de sincronización (eliminar PDAs y fechas no compartidas):<br/><br/>
           + Registros totales: {my_dict["Información de sincronizacion"]["Conteo de registros"]["Registros totales"]}.<br/>
           - Pertenecientes al fichero B: {my_dict["Información de sincronizacion"]["Conteo de registros"]["Registros B"]}.<br/>
           - Pertenecientes al fichero C: {my_dict["Información de sincronizacion"]["Conteo de registros"]["Registros C"]}.<br/><br/>
           + Códigos de unidad:<br/>
           - Pertenecientes al fichero B ({my_dict["Información de sincronizacion"]["Conteo codireds"]["Num codireds encontrados en fichero B"]}):
        {my_dict["Información de sincronizacion"]["Conteo codireds"]["Codireds en fichero B"]}.<br/>
           - Pertenecientes al fichero C ({my_dict["Información de sincronizacion"]["Conteo codireds"]["Num codireds encontrados en fichero C"]}):
        {my_dict["Información de sincronizacion"]["Conteo codireds"]["Codireds en fichero C"]}.<br/>
           - Compartidos ({my_dict["Información de sincronizacion"]["Conteo codireds"]["Num codireds compartidos"]}):
        {my_dict["Información de sincronizacion"]["Conteo codireds"]["Codireds compartidos"]}.<br/><br/>
           + PDAs:<br/>
           - Pertenecientes al fichero B ({my_dict["Información de sincronizacion"]["Conteo PDAs"]["Num PDAs encontradas en el fichero B"]}):
        {my_dict["Información de sincronizacion"]["Conteo PDAs"]["PDAs en fichero B"]}.<br/>
           - Pertenecientes al fichero C ({my_dict["Información de sincronizacion"]["Conteo PDAs"]["Num PDAs encontradas en el fichero C"]}):
        {my_dict["Información de sincronizacion"]["Conteo PDAs"]["PDAs en fichero C"]}.<br/>
           - Compartidos ({my_dict["Información de sincronizacion"]["Conteo PDAs"]["Num PDAs compartida"]}):
        {my_dict["Información de sincronizacion"]["Conteo PDAs"]["PDAs compartidas"]}.<br/><br/>
           + Fechas:<br/>
           - Pertenecientes al fichero B ({my_dict["Información de sincronizacion"]["Conteo fechas"]["Num fechas en fichero B"]}):
        {my_dict["Información de sincronizacion"]["Conteo fechas"]["Lista fecha en fichero B"]}.<br/>
           - Pertenecientes al fichero C ({my_dict["Información de sincronizacion"]["Conteo fechas"]["Num fechas en fichero C"]}):
        {my_dict["Información de sincronizacion"]["Conteo fechas"]["Lista fecha en fichero C"]}.<br/>
           - Compartidas ({my_dict["Información de sincronizacion"]["Conteo fechas"]["Num fechas compartidas"]}):
        {my_dict["Información de sincronizacion"]["Conteo fechas"]["Lista fecha compartida"]}.<br/>
        <br/>
        Registros sin correspondencia (descartados):<br/>
           - Registros totales: {my_dict["Registros_no_usados"]["Totales no usados en la union"]}.<br/>
           - Registros del fichero B: {my_dict["Registros_no_usados"]["B_no_usados en la union"]}.<br/>
           - Registros del fichero C: {my_dict["Registros_no_usados"]["C_no_usados en la union"]}.<br/>
        <br/>
        <br/>
        Resultado de la unión: {my_dict["Registros_finales"]} registros.<br/>
        """
    elif type == 'E':
        intro = f"""
        Registros totales: {my_dict["Informacion inicial"]["Conteo de registros"]["Registros totales"]}.<br/>
            - Pertenecientes al fichero A: {my_dict["Informacion inicial"]["Conteo de registros"]["Registros B"]}.<br/>
            - Pertenecientes al fichero D: {my_dict["Informacion inicial"]["Conteo de registros"]["Registros C"]}.<br/>
        <br/>
        Códigos de unidad:<br/>
            - Códigos de unidad de A: {my_dict["Informacion inicial"]["Conteo codireds"]["Codireds en fichero B"]}.<br/>
            - Códigos de unidad de D: {my_dict["Informacion inicial"]["Conteo codireds"]["Codireds en fichero C"]}.<br/>
            - Códigos compartidos: {my_dict["Informacion inicial"]["Conteo codireds"]["Codireds compartidos"]}.<br/>
        <br/>
        PDAs:<br/>
           - Pertenecientes al fichero A ({my_dict["Informacion inicial"]["Conteo PDAs"]["Num PDAs encontradas en el fichero B"]}):
        {my_dict["Informacion inicial"]["Conteo PDAs"]["PDAs en fichero B"]}.<br/>
           - Pertenecientes al fichero D ({my_dict["Informacion inicial"]["Conteo PDAs"]["Num PDAs encontradas en el fichero C"]}):
        {my_dict["Informacion inicial"]["Conteo PDAs"]["PDAs en fichero C"]}.<br/>
           - Compartidos ({my_dict["Informacion inicial"]["Conteo PDAs"]["Num PDAs compartida"]}):
        {my_dict["Informacion inicial"]["Conteo PDAs"]["PDAs compartidas"]}.<br/>
        <br/>
        Fechas:<br/>
           - Pertenecientes al fichero A ({my_dict["Informacion inicial"]["Conteo fechas"]["Num fechas en fichero B"]}):
        {my_dict["Informacion inicial"]["Conteo fechas"]["Lista fecha en fichero B"]}.<br/>
           - Pertenecientes al fichero D ({my_dict["Informacion inicial"]["Conteo fechas"]["Num fechas en fichero C"]}):
        {my_dict["Informacion inicial"]["Conteo fechas"]["Lista fecha en fichero C"]}.<br/>
           - Compartidas ({my_dict["Informacion inicial"]["Conteo fechas"]["Num fechas compartidas"]}):
        {my_dict["Informacion inicial"]["Conteo fechas"]["Lista fecha compartida"]}.<br/>
        <br/>
        <br/>
        Eliminación de registros defectuosos:<br/>
           (Se eliminan PDAs como #N/D, sin formato PDA01, PDA13, PDA25, etc)<br/>
           - PDAs fichero A: {my_dict["Defectuoso"]["PDAs A"]} registros.<br/>
           - PDAs fichero D: {my_dict["Defectuoso"]["PDAs D"]} registros.<br/><br/>
           (Se eliminan fechas que no se han podido usar, como nan)<br/>
           - Fechas fichero A: {my_dict["Defectuoso"]["Fechas A"]} registros.<br/>
           - Fechas fichero D: {my_dict["Defectuoso"]["Fechas D"]} registros.<br/><br/>
           (Se eliminan horas fueras del rango laboral fijado entre 7:30 y 22:00)<br/>
           - Horas fichero A: {my_dict["Defectuoso"]["Horas A"]} registros.<br/>
           - Horas fichero D: {my_dict["Defectuoso"]["Horas D"]} registros.<br/><br/>
        Eliminación de duplicados:<br/>
           + Duplicados totales: {my_dict["Duplicados"]["Duplicados totales"]}.<br/>
           - Pertenecientes al fichero A: {my_dict["Duplicados"]["Duplicados A"]}.<br/>
           - Pertenecientes al fichero D: {my_dict["Duplicados"]["Duplicados D"]}.<br/><br/>
           + Datos totales no duplicados: {my_dict["Duplicados"]["Registros totales no duplicados"]}.<br/>
           - Pertenecientes al fichero A: {my_dict["Duplicados"]["Registros A no duplicados"]}.<br/>
           - Pertenecientes al fichero D: {my_dict["Duplicados"]["Registros D no duplicados"]}.<br/>
        <br/>
        """
        union = f"""
        Información de sincronización (eliminar PDAs y fechas no compartidas):<br/><br/>
           + Registros totales: {my_dict["Información de sincronizacion"]["Conteo de registros"]["Registros totales"]}.<br/>
           - Pertenecientes al fichero A: {my_dict["Información de sincronizacion"]["Conteo de registros"]["Registros B"]}.<br/>
           - Pertenecientes al fichero D: {my_dict["Información de sincronizacion"]["Conteo de registros"]["Registros C"]}.<br/><br/>
           + Códigos de unidad:<br/>
           - Pertenecientes al fichero A ({my_dict["Información de sincronizacion"]["Conteo codireds"]["Num codireds encontrados en fichero B"]}):
        {my_dict["Información de sincronizacion"]["Conteo codireds"]["Codireds en fichero B"]}.<br/>
           - Pertenecientes al fichero D ({my_dict["Información de sincronizacion"]["Conteo codireds"]["Num codireds encontrados en fichero C"]}):
        {my_dict["Información de sincronizacion"]["Conteo codireds"]["Codireds en fichero C"]}.<br/>
           - Compartidos ({my_dict["Información de sincronizacion"]["Conteo codireds"]["Num codireds compartidos"]}):
        {my_dict["Información de sincronizacion"]["Conteo codireds"]["Codireds compartidos"]}.<br/><br/>
           + PDAs:<br/>
           - Pertenecientes al fichero A ({my_dict["Información de sincronizacion"]["Conteo PDAs"]["Num PDAs encontradas en el fichero B"]}):
        {my_dict["Información de sincronizacion"]["Conteo PDAs"]["PDAs en fichero B"]}.<br/>
           - Pertenecientes al fichero D ({my_dict["Información de sincronizacion"]["Conteo PDAs"]["Num PDAs encontradas en el fichero C"]}):
        {my_dict["Información de sincronizacion"]["Conteo PDAs"]["PDAs en fichero C"]}.<br/>
           - Compartidos ({my_dict["Información de sincronizacion"]["Conteo PDAs"]["Num PDAs compartida"]}):
        {my_dict["Información de sincronizacion"]["Conteo PDAs"]["PDAs compartidas"]}.<br/><br/>
           + Fechas:<br/>
           - Pertenecientes al fichero A ({my_dict["Información de sincronizacion"]["Conteo fechas"]["Num fechas en fichero B"]}):
        {my_dict["Información de sincronizacion"]["Conteo fechas"]["Lista fecha en fichero B"]}.<br/>
           - Pertenecientes al fichero D ({my_dict["Información de sincronizacion"]["Conteo fechas"]["Num fechas en fichero C"]}):
        {my_dict["Información de sincronizacion"]["Conteo fechas"]["Lista fecha en fichero C"]}.<br/>
           - Compartidas ({my_dict["Información de sincronizacion"]["Conteo fechas"]["Num fechas compartidas"]}):
        {my_dict["Información de sincronizacion"]["Conteo fechas"]["Lista fecha compartida"]}.<br/>
        <br/>
        <br/>
        Resultado de la unión: {my_dict["Registros_finales"]} registros.<br/>
        """
    
    return intro, union