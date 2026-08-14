import csv
import json
import os
import re
import unicodedata
from bs4 import BeautifulSoup


def normalizar_nombre(nombre: str) -> str:
    """
    Normaliza un nombre para facilitar la comparación:
    - Remueve tildes/acentos (ej. María -> Maria, Pérez -> Perez)
    - Pasa a minúsculas
    - Remueve espacios redundantes
    - Remueve sufijos típicos de Zoom como (yo), (anfitrión), (host), (guest), etc.
    """
    if not nombre:
        return ""
    
    # 1. Normalizar caracteres unicode (quitar diacríticos/tildes)
    nfkd = unicodedata.normalize('NFKD', str(nombre))
    sin_tildes = "".join([c for c in nfkd if not unicodedata.combining(c)])
    
    # 2. Convertir a minúsculas y limpiar espacios
    limpio = re.sub(r'\s+', ' ', sin_tildes).strip().lower()
    
    # 3. Remover sufijos de Zoom si estuvieran dentro del texto
    limpio = re.sub(
        r'\s*\((yo|anfitri[oó]n|coanfitri[oó]n|host|co-host|me|guest|invitado)[^)]*\)',
        '',
        limpio,
        flags=re.IGNORECASE
    )
    
    return limpio.strip()


def extraer_participantes_zoom(html_content: str) -> dict:
    """
    Extrae los participantes y el estado de sus cámaras a partir del HTML de Zoom.
    Soporta la estructura virtualizada de Zoom Web (formato-ejemplo.html).
    
    Retorna un diccionario con la estructura:
    {
        "nombre_normalizado": {
            "nombre_original": str,
            "camera_on": bool,
            "aria_label": str
        }
    }
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    participantes = {}
    
    # 1. Buscar elementos de participante:
    # Zoom web utiliza elementos con clase 'participants-li' o IDs con 'participants-list-'
    items = soup.find_all(
        lambda tag: tag.has_attr('class') and 'participants-li' in tag.get('class', [])
    )
    
    if not items:
        # Fallback: buscar por ID
        items = soup.find_all(
            lambda tag: tag.has_attr('id') and str(tag.get('id', '')).startswith('participants-list-')
        )
        
    if not items:
        # Fallback general: buscar contenedores con layout de participante
        items = soup.find_all(
            class_=lambda c: c and any(cls in ['participants-item__item-layout', 'participants-item-position'] for cls in (c if isinstance(c, list) else c.split()))
        )

    for item in items:
        # 2. Extraer nombre desde el span con clase 'participants-item__display-name'
        name_el = item.find(
            class_=lambda c: c and 'participants-item__display-name' in (c if isinstance(c, list) else c.split())
        )
        
        nombre_original = ""
        if name_el:
            nombre_original = name_el.get_text(strip=True)
            
        aria_label = item.get('aria-label', '')
        
        # Si no encontramos el span de nombre, intentar extraerlo del aria-label
        if not nombre_original and aria_label:
            nombre_part = aria_label.split(',')[0].strip()
            nombre_original = re.sub(r'\s*\([^)]*\)', '', nombre_part).strip()
            
        if not nombre_original:
            continue
            
        # 3. Detectar estado de la cámara
        # A. Revisar íconos SVG con clase 'video-off'
        has_video_off_svg = bool(
            item.find('svg', class_=lambda c: c and any('video-off' in cls for cls in (c if isinstance(c, list) else c.split())))
        )
        
        # B. Revisar si en aria-label indica video off o video on
        aria_lower = aria_label.lower()
        has_video_off_aria = any(
            phrase in aria_lower for phrase in ["video off", "video apagado", "camara apagada", "cámara apagada", "video-off"]
        )
        has_video_on_aria = any(
            phrase in aria_lower for phrase in ["video on", "video encendido", "camara encendida", "cámara encendida", "video-on"]
        )
        has_video_on_svg = bool(
            item.find('svg', class_=lambda c: c and any('video-on' in cls for cls in (c if isinstance(c, list) else c.split())))
        )
        
        if has_video_off_svg or has_video_off_aria:
            camera_on = False
        elif has_video_on_svg or has_video_on_aria:
            camera_on = True
        else:
            # En Zoom, cuando la cámara está activa usualmente no muestra el ícono tachado de video-off
            camera_on = True
            
        clave_normalizada = normalizar_nombre(nombre_original)
        participantes[clave_normalizada] = {
            "nombre_original": nombre_original,
            "camera_on": camera_on,
            "aria_label": aria_label
        }
        
    return participantes


def procesar_asistencia(input_csv: str, output_csv: str, zoom_source) -> list:
    """
    Lee un CSV con una lista de alumnos, compara con los datos de Zoom
    (HTML crudo, ruta de archivo HTML, string JSON o diccionario)
    y genera un nuevo CSV con las columnas: [Nombre, Asistencia, Cámara].
    
    Retorna la lista de filas procesadas.
    """
    # 1. Resolver y normalizar zoom_data
    zoom_dict_normalizado = {}
    
    if isinstance(zoom_source, dict):
        for k, v in zoom_source.items():
            norm_k = normalizar_nombre(k)
            if isinstance(v, dict):
                zoom_dict_normalizado[norm_k] = v
            else:
                zoom_dict_normalizado[norm_k] = {"camera_on": bool(v)}
                
    elif isinstance(zoom_source, str):
        fuente = zoom_source.strip()
        # Verificar si es una ruta a un archivo existente
        if os.path.isfile(fuente):
            with open(fuente, 'r', encoding='utf-8', errors='ignore') as f:
                contenido = f.read()
            if "<" in contenido and ("participants" in contenido or "html" in contenido or "div" in contenido):
                zoom_dict_normalizado = extraer_participantes_zoom(contenido)
            else:
                try:
                    data = json.loads(contenido)
                    zoom_dict_normalizado = {normalizar_nombre(k): v if isinstance(v, dict) else {"camera_on": bool(v)} for k, v in data.items()}
                except json.JSONDecodeError:
                    zoom_dict_normalizado = extraer_participantes_zoom(contenido)
        # Verificar si es HTML directo
        elif "<" in fuente and ("participants" in fuente or "div" in fuente or "svg" in fuente):
            zoom_dict_normalizado = extraer_participantes_zoom(fuente)
        # Verificar si es JSON
        else:
            try:
                data = json.loads(fuente)
                if isinstance(data, dict):
                    zoom_dict_normalizado = {normalizar_nombre(k): v if isinstance(v, dict) else {"camera_on": bool(v)} for k, v in data.items()}
            except json.JSONDecodeError:
                # Si no es JSON válido, intentar extraer como HTML
                zoom_dict_normalizado = extraer_participantes_zoom(fuente)

    # 2. Lectura inteligente del archivo CSV con soporte para múltiples encodings
    encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']
    infile = None
    reader = None
    header = None
    
    for enc in encodings:
        try:
            f = open(input_csv, mode='r', encoding=enc)
            test_reader = csv.reader(f)
            header = next(test_reader, None)
            infile = f
            reader = test_reader
            break
        except (UnicodeDecodeError, Exception):
            if f:
                f.close()
            continue
            
    if infile is None:
        raise ValueError(f"No se pudo leer el archivo CSV {input_csv} con codificaciones estándar.")

    # 3. Procesar asistencia de cada alumno
    resultados = []
    col_nombre = header[0].strip() if (header and len(header) > 0 and header[0].strip()) else "Nombre"
    resultados.append([col_nombre, "Asistencia", "Cámara"])
    
    for row in reader:
        if not row or not any(row):
            continue
            
        nombre_alumno_original = row[0].strip()
        if not nombre_alumno_original:
            continue
            
        clave_busqueda = normalizar_nombre(nombre_alumno_original)
        info_zoom = zoom_dict_normalizado.get(clave_busqueda)
        
        if info_zoom:
            asistencia = "Presente"
            camara = "Encendida" if info_zoom.get("camera_on") else "Apagada"
        else:
            asistencia = "Ausente"
            camara = "Apagada"
            
        resultados.append([nombre_alumno_original, asistencia, camara])
        
    infile.close()

    # 4. Generar el archivo CSV de salida con utf-8-sig (compatible con Excel)
    with open(output_csv, mode='w', encoding='utf-8-sig', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerows(resultados)
        
    return resultados