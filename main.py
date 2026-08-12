from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import json
from core import procesar_asistencia

app = FastAPI(title="Zoom Attendance API")

# Configuración obligatoria para permitir que la extensión se comunique con esta API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/procesar-asistencia/")
async def upload_csv(
    file: UploadFile = File(...),
    zoom_data: str = Form(...) # Recibimos los datos de la extensión como un string de texto
):
    """
    Recibe un archivo CSV y un string JSON con los datos capturados de Zoom.
    Procesa y devuelve el CSV actualizado.
    """
    input_path = f"temp_in_{file.filename}"
    output_path = f"temp_out_{file.filename}"
    
    try:
        # 1. Guardar el archivo que sube el usuario temporalmente
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 2. Convertir el texto JSON que nos manda la extensión a un diccionario de Python
        zoom_dict = json.loads(zoom_data)
        
        # 3. Procesar el archivo usando nuestra lógica central
        procesar_asistencia(input_path, output_path, zoom_dict)
        
        # 4. Devolver el archivo procesado
        return FileResponse(
            path=output_path, 
            filename=f"resultado_{file.filename}",
            media_type='text/csv'
        )
        
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)