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

   data = getData(info_path)

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
   <b>Entrada:</b><br/>
   - Fichero A: identifica la ruta de reparto de una PDA de correspondencia no registrada (código de unidad, PDA, fecha, latitud y longitud).<br/>
   - Fichero B: identifica los instantes de entrega de correspondencia registrada (código de unidad, PDA, fecha, tiempo transcurrido, código de actividad, sección y turno).<br/>
   - Fichero C: identifica las coordenadas de entrega de correspondencia registrada (código de unidad, sección, turno, fecha, latitud y lontiud).<br/>
   <br/>
   <b>Salida:</b><br/>
   - Fichero D: resultado de la unión de B y C.<br/>
   - Fichero E: resultado de la unión de A y D.<br/>
   """

   story.append(Paragraph(intro, normal))

   story.append(Paragraph("Limpieza preliminar de los datos", subtitle))

   story.append(Paragraph("Fichero A", subsubtitle))
   pre_info_A = getInfo(data, "preRead", "A")
   story.append(Paragraph(pre_info_A, normal))

   story.append(Paragraph("Fichero B", subsubtitle))
   pre_info_B = getInfo(data, "preRead", "B")
   story.append(Paragraph(pre_info_B, normal))

   story.append(Paragraph("Fichero C", subsubtitle))
   pre_info_C = getInfo(data, "preRead", "C")
   story.append(Paragraph(pre_info_C, normal))

   story.append(Paragraph("Preproceso de B y C", subtitle))
   story.append(Spacer(1, 4))

   join_info = """
   El proceso de unificación de los ficheros B y C se hace con el propósito 
   de asignar coordenadas (proporcionadas en el fichero C) a los puntos de 
   paradas registradas del fichero B.<br/>
   Para ello se establece una relación entre los ficheros con los campos 
   <i>Sección</i>, <i>Turno</i> y <i>Fecha</i>. Con la restricción inicial 
   de que los registros deben pertenecer a la misma unidad de reparto (el campo 
   <i>Código de unidad</i> debe coincidir).<br/>
   Una vez filtrados los registros se establece una ventana de 59 segundos 
   de margen entre los registros de un fichero y del otro que describren la misma 
   acción del cartero. Esto se hace debido a que los registros que describen la misma 
   acción no tienen por qué tener exactamente la misma hora registrada porque se generan 
   con aplicaciones distintas.<br/>
   El resultado de este proceso será el fichero D.<br/><br/>
   """

   story.append(Paragraph(join_info, normal))
   # Estadisticas
   story.append(Paragraph("Información de lectura de los datos", subsubtitle))
   read_D = getInfo(data, "read", "D")
   story.append(Paragraph(read_D, normal))
   #info_D_intro, info_D_union = getInfo(info_path, 'D')
   #story.append(Paragraph(info_D_intro, normal))
   story.append(Spacer(1, 4))
   story.append(Paragraph("Información de sincronización de los datos", subsubtitle))
   subtitle_sinchro = """
   La sincronización consiste en eliminar los registros con códigos de unidad, 
   fechas, secciones o turnos no compartidos entre ambos ficheros.<br/><br/>
   """
   story.append(Paragraph(subtitle_sinchro, normal))
   sinchro_D = getInfo(data, "sinchro", "D")
   story.append(Paragraph(sinchro_D, normal))
   story.append(Paragraph("Unión de datos de B y C >> Fichero D", subsubtitle))
   join_D = getInfo(data, "join", "D")
   story.append(Paragraph(join_D, normal))


   story.append(Spacer(1, 6))
   story.append(Paragraph("Preproceso de A y D", subtitle))
   story.append(Spacer(1, 4))

   # Introduccion para contexto
   intro_text_AD = """ 
   La unión de los ficheros A y D se realiza con el propósito de resaltar q
   ué puntos de las rutas de los carteros son paradas registradas. De esta forma, 
   más adelante (en un proceso que no se describirá en este documento) se contrarrestarán 
   estas paradas registradas a los puntos primarios.<br/>
   El proceso conserva todos los datos del fichero A y rellena las secuencias temporales 
   presentadas en este con los datos del fichero D.<br/>
   El resultado de este proceso será el fichero E.<br/><br/>
   """
   story.append(Paragraph(intro_text_AD, normal))
   # Estadisticas
   #info_E_intro, info_E_union = getInfo(info_path, 'E')
   story.append(Paragraph("Información de lectura de los datos y preprocesado del fichero A", subsubtitle))
   read_E = getInfo(data, "read", "E")
   story.append(Paragraph(read_E, normal))
   story.append(Paragraph("Información de sincronización de los datos", subsubtitle))
   subtitle_sinchro = """
   La sincronización consiste en eliminar los códigos de unidad, PDAs y fechas del fichero D 
   que no pertenezcan al fichero A.<br/><br/>
   """
   story.append(Paragraph(subtitle_sinchro, normal))
   sinchro_E = getInfo(data, "sinchro", "E")
   story.append(Paragraph(sinchro_E, normal))
   #story.append(Paragraph(info_E_intro, normal))
   #story.append(Spacer(1, 4))
   story.append(Paragraph("Unión de datos de A y D >> Fichero E", subsubtitle))
   join_E = getInfo(data, "join", "E")
   story.append(Paragraph(join_E, normal))


   doc.build(story)


def getData(path):
   full_path = os.path.join(path, 'statistics.json')
   with open(full_path, "r", encoding="utf-8") as f:
      my_dict = json.load(f)
      return my_dict




def getInfo(dict, info_type, type):
   if info_type == "preRead":
      return preInfo(dict, type)
   elif info_type == "read":
      return readInfo(dict, type)
   elif info_type == "sinchro":
      return sinchroInfo(dict, type)
   elif info_type == "join":
      return joinInfo(dict, type)
   else:
      return "No se pudo proveer esta información"





def joinInfo(dict, type):
   if type == "D":
      data = dict["D"]["final"]

      return f"""
      Registros usados:<br/>
         - Pertenecientes al fichero B: {data["b_used"]}.<br/>
         - Pertenecientes al fichero C: {data["c_used"]}.<br/>
      <br/>
      Registros descartados en la unión:<br/>
         - Pertenecientes al fichero B: {data["b_unused"]}.<br/>
         - Pertenecientes al fichero C: {data["c_unused"]}.<br/>
      <br/>
      <br/>
      RESULTADO DE LA UNIÓN<br/>
      <br/>
      Registros totales: {data["final"]["length"]}.<br/>
      <br/>
      Códigos de unidad ({data["final"]["unit_codes_length"]}): {data["final"]["unit_codes"]}.<br/>
      <br/>
      PDAs ({data["final"]["num_inv_length"]}): {data["final"]["num_inv"]}.<br/>
      <br/>
      Fechas ({data["final"]["dates_length"]}): {data["final"]["dates"]}.<br/>
      <br/>
      """
   elif type == "E":
      data = dict["E"]["final"]

      return f"""
      Registros totales: {data["length"]}.<br/>
      <br/>
      Códigos de unidad ({data["unit_codes_length"]}): {data["unit_codes"]}.<br/>
      <br/>
      PDAs ({data["num_inv_length"]}): {data["num_inv"]}.<br/>
      <br/>
      Fechas ({data["dates_length"]}): {data["dates"]}.<br/>
      <br/>
      """
   else:
      return ""





def sinchroInfo(dict, type):
   if type == "D":
      data = dict["D"]["sinchronized"]
      b_after = data["b_after"]
      c_after = data["c_after"]

      return f"""
      Códigos de unidad:<br/>
         - Registros eliminados del fichero B: {data["b_unit_code_reg_erased"]}.<br/>
         - Registros eliminados del fichero C: {data["c_unit_code_reg_erased"]}.<br/>
      <br/>
      Sección:<br/>
         - Registros eliminados del fichero B: {data["b_section_reg_erased"]}.<br/>
         - Registros eliminados del fichero C: {data["c_section_reg_erased"]}.<br/>
      <br/>
      Turno:<br/>
         - Registros eliminados del fichero B: {data["b_shift_reg_erased"]}.<br/>
         - Registros eliminados del fichero C: {data["c_shift_reg_erased"]}.<br/>
      <br/>
      Fechas:<br/>
         - Registros eliminados del fichero B: {data["b_dates_reg_erased"]}.<br/>
         - Registros eliminados del fichero C: {data["c_dates_reg_erased"]}.<br/>
      <br/>
      Combinación de todos los campos:<br/>
         - Registros eliminados del fichero B: {data["b_sinchronized_reg_erased"]}.<br/>
         - Registros eliminados del fichero C: {data["c_sinchronized_reg_erased"]}.<br/>
      <br/>
      Registros eliminados totales: {data["total_reg_erased"]}<br/>
         - Pertenecientes al fichero B: {data["b_total_reg_erased"]}.<br/>
         - Pertenecientes al fichero C: {data["c_total_reg_erased"]}.<br/>
      <br/>
      <br/>
      RESULTADO DE LA SINCRONIZACIÓN<br/>
      <br/>
      Registros totales: {b_after["length"] + c_after["length"]}.<br/>
         - Pertenecientes al fichero B: {b_after["length"]}.<br/>
         - Pertenecientes al fichero C: {c_after["length"]}.<br/>
      <br/>
      Códigos de unidad:<br/>
         - Pertenecientes al fichero B ({b_after["unit_codes_length"]}): {b_after["unit_codes"]}.<br/>
         - Pertenecientes al fichero C ({c_after["unit_codes_length"]}): {c_after["unit_codes"]}<br/>
      <br/>
      PDAs:<br/>
         - Pertenecientes al fichero B ({b_after["num_inv_length"]}): {b_after["num_inv"]}.<br/>
         - Pertenecientes al fichero C (0): El fichero no cuenta con un campo "Num Inv".<br/>
      <br/>
      Fechas:<br/>
         - Pertenecientes al fichero B ({b_after["dates_length"]}): {b_after["dates"]}.<br/>
         - Pertenecientes al fichero C ({c_after["dates_length"]}): {c_after["dates"]}<br/>
      <br/>
      """
   elif type == "E":
      data = dict["E"]["sinchronized"]
      d_after = data["d_after"]

      return f"""
      Códigos de unidad:<br/>
         - Registros eliminados del fichero D: {data["d_unit_code_reg_erased"]}.<br/>
      <br/>
      PDAs:<br/>
         - Registros eliminados del fichero D: {data["d_pda_reg_erased"]}.<br/>
      <br/>
      Fechas:<br/>
         - Registros eliminados del fichero D: {data["d_dates_reg_erased"]}.<br/>
      <br/>
      Combinación de todos los campos:<br/>
         - Registros eliminados del fichero D: {data["d_sinchronized_reg_erased"]}.<br/>
      <br/>
      Registros eliminados totales: {data["d_total_reg_erased"]}<br/>
      <br/>
      <br/>
      RESULTADO DE LA SINCRONIZACIÓN<br/>
      <br/>
      Registros totales:<br/>
         - Pertenecientes al fichero B: {d_after["length"]}.<br/>
      <br/>
      Códigos de unidad:<br/>
         - Pertenecientes al fichero B ({d_after["unit_codes_length"]}): {d_after["unit_codes"]}.<br/>
      <br/>
      PDAs:<br/>
         - Pertenecientes al fichero B ({d_after["num_inv_length"]}): {d_after["num_inv"]}.<br/>
      <br/>
      Fechas:<br/>
         - Pertenecientes al fichero B ({d_after["dates_length"]}): {d_after["dates"]}.<br/>
      <br/>
      """
   else:
      return ""





def readInfo(dict, type):
   if type == "D":
      data = dict["D"]
      b_data = data["B_initial"]
      c_data = data["C_initial"]

      return f"""
      Registros totales: {b_data["length"] + c_data["length"]}.<br/>
         - Pertenecientes al fichero B: {b_data["length"]}.<br/>
         - Pertenecientes al fichero C: {c_data["length"]}.<br/>
      <br/>
      Códigos de unidad:<br/>
         - Pertenecientes al fichero B ({b_data["unit_codes_length"]}): {b_data["unit_codes"]}.<br/>
         - Pertenecientes al fichero C ({c_data["unit_codes_length"]}): {c_data["unit_codes"]}<br/>
      <br/>
      PDAs:<br/>
         - Pertenecientes al fichero B ({b_data["num_inv_length"]}): {b_data["num_inv"]}.<br/>
         - Pertenecientes al fichero C (0): El fichero no cuenta con un campo "PDA".<br/>
      <br/>
      Fechas:<br/>
         - Pertenecientes al fichero B ({b_data["dates_length"]}): {b_data["dates"]}.<br/>
         - Pertenecientes al fichero C ({c_data["dates_length"]}): {c_data["dates"]}<br/>
      <br/>
      Intentos de entrega:<br/>
         - Pertenecientes al fichero B: {data["B_delivery"]["data_info"]["length"]}.<br/>
            · Registros eliminados: {data["B_delivery"]["erased_info"]}.<br/>
         - Pertenecientes al fichero C: 0 (El fichero no cuenta con un campo "Codigo Actividad").<br/>
            · Registros eliminados: 0.<br/>
      <br/>
      """

   elif type == "E":
      data = dict["E"]
      a_data = data["A_initial"]
      d_data = data["D_initial"]

      return f"""
      Registros totales: {a_data["length"] + d_data["length"]}.<br/>
         - Pertenecientes al fichero A: {a_data["length"]}.<br/>
         - Pertenecientes al fichero D: {d_data["length"]}.<br/>
      <br/>
      Códigos de unidad:<br/>
         - Pertenecientes al fichero A ({a_data["unit_codes_length"]}): {a_data["unit_codes"]}.<br/>
         - Pertenecientes al fichero D ({d_data["unit_codes_length"]}): {d_data["unit_codes"]}<br/>
      <br/>
      PDAs:<br/>
         - Pertenecientes al fichero A ({a_data["num_inv_length"]}): {a_data["num_inv"]}.<br/>
         - Pertenecientes al fichero D (0): El fichero no cuenta con el campo "PDA".<br/>
      <br/>
      Fechas:<br/>
         - Pertenecientes al fichero A ({a_data["dates_length"]}): {a_data["dates"]}.<br/>
         - Pertenecientes al fichero D ({d_data["dates_length"]}): {d_data["dates"]}<br/>
      <br/>
      """
   else:
      return ""




def preInfo(info_dict, type):
   if type == "A":
      data = info_dict["A_preprocess"]
   elif type == "B":
      data = info_dict["B_preprocess"]
   elif type == "C":
      data = info_dict["C_preprocess"]
   else:
      data = []

   return f"""
   · Número de registros iniciales: {data["initial"]}.<br/>
   · Número de registros duplicados: {data["duplicates"]}.<br/>
   · Número de registros inválidos (registros con valores nulos): {data["invalid"]}.<br/>
   · Número de registros finales: {data["final"]}.<br/>
   """
