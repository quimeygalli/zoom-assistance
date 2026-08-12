from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
import shutil
import os
from core import procesar_asistencia

# Inicializamos la aplicación FastAPI
app = FastAPI(title="Zoom Attendance API", description="API para automatizar la asistencia de Zoom")

# Mantenemos nuestro diccionario simulado por ahora
mock_zoom_data = {
    "Ana Perez": {"camera_on": True},
    "Maria Lopez": {"camera_on": False}
}

@app.post("/api/procesar-asistencia/")
async def upload_csv(file: UploadFile = File(...)):
    """
    Recibe un archivo CSV, lo procesa y devuelve el CSV actualizado
    con la asistencia y el estado de la cámara.
    """
    input_path = f"temp_in_{file.filename}"
    output_path = f"temp_out_{file.filename}"
    
    try:
        # 1. Guardar el archivo que sube el usuario temporalmente
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 2. Procesar el archivo usando nuestra lógica central
        procesar_asistencia(input_path, output_path, mock_zoom_data)
        
        # 3. Devolver el archivo procesado para que el usuario lo descargue
        return FileResponse(
            path=output_path, 
            filename=f"resultado_{file.filename}",
            media_type='text/csv'
        )
        
    finally:
        # El archivo de salida lo mantendremos un instante para que FastAPI lo envíe
        if os.path.exists(input_path):
            os.remove(input_path)