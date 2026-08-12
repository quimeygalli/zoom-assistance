import csv

def procesar_asistencia(input_csv, output_csv, zoom_data):
    """
    Lee un CSV con una lista de alumnos, compara con los datos de Zoom
    y genera un nuevo CSV con las columnas de Asistencia y Cámara.
    """
    try:
        with open(input_csv, mode='r', encoding='utf-8') as infile:
            reader = csv.reader(infile)
            header = next(reader, None) # Leer el header (ej: "Nombre")
            
            resultados = []
            # Crear el nuevo header
            if header:
                resultados.append([header[0], "Asistencia", "Cámara"])
            else:
                resultados.append(["Alumno", "Asistencia", "Cámara"])
            
            # Procesar cada alumno
            for row in reader:
                if not row:
                    continue # Saltar filas vacías
                    
                nombre_alumno = row[0].strip()
                
                # Buscar al alumno en los datos de Zoom
                info_alumno = zoom_data.get(nombre_alumno)
                
                if info_alumno:
                    asistencia = "Presente"
                    camara = "Encendida" if info_alumno.get("camera_on") else "Apagada"
                else:
                    asistencia = "Ausente"
                    camara = "Apagada" # Por defecto, si no está, la cámara está apagada
                    
                resultados.append([nombre_alumno, asistencia, camara])
                
        # Escribir el resultado en un nuevo CSV
        with open(output_csv, mode='w', encoding='utf-8', newline='') as outfile:
            writer = csv.writer(outfile)
            writer.writerows(resultados)
            
        print(f"Éxito: Archivo generado correctamente en '{output_csv}'")
        
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{input_csv}'")
    except Exception as e:
        print(f"Error inesperado: {e}")

# ==========================================
# MOCK
# ==========================================
if __name__ == "__main__":
    # 1. Crear un CSV de prueba automáticamente para probar el script
    csv_prueba = "lista_alumnos.csv"
    with open(csv_prueba, "w", encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Nombre"])
        writer.writerow(["Ana Perez"])
        writer.writerow(["Juan Gomez"])
        writer.writerow(["Maria Lopez"])
        writer.writerow(["Carlos Diaz"])

    # 2. Simular la información que nos entregará la API de Zoom en el futuro
    mock_zoom_data = {
        "Ana Perez": {"camera_on": True},
        "Maria Lopez": {"camera_on": False}
        # Juan y Carlos no se conectaron
    }

    # 3. Ejecutar la función
    procesar_asistencia(csv_prueba, "asistencia_final.csv", mock_zoom_data)