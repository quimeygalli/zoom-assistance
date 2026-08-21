"""
main.py — FastAPI application and CLI entry point.

Usage
-----
  # Start the HTTP API server (default port 8000):
  python main.py --server [--port 8000]

  # Run the attendance processor via command line:
  python main.py --csv lista_alumnos.csv --html formato-ejemplo.html --out reporte.csv

The FastAPI app object (`app`) is also imported by server.py for the Windows
executable distribution. Do not rename it.
"""
import argparse
import json
import os
import shutil
import sys
from typing import Optional

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from core import extraer_participantes_zoom, procesar_asistencia, marcar_asistencia_excel

app = FastAPI(
    title="Zoom Attendance API",
    description="API para procesar asistencia y estado de cámara de alumnos en Zoom a partir de listas CSV y datos/HTML de la reunión.",
    version="1.1.0"
)

# Configuración de CORS para permitir la comunicación con la extensión de Chrome
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"status": "ok", "message": "Zoom Attendance API activa."}


@app.post("/api/procesar-asistencia/")
async def procesar_asistencia_endpoint(
    file: UploadFile = File(..., description="Archivo CSV con la lista de alumnos"),
    zoom_data: Optional[str] = Form(None, description="Datos de Zoom en formato HTML o JSON string"),
    zoom_file: Optional[UploadFile] = File(None, description="Archivo HTML o JSON de Zoom")
):
    """
    Recibe un archivo CSV de alumnos y la fuente de datos de Zoom (HTML o JSON).
    Procesa la asistencia y devuelve el archivo CSV actualizado con Asistencia y Cámara.
    """
    if not zoom_data and not zoom_file:
        raise HTTPException(
            status_code=400,
            detail="Debes proporcionar 'zoom_data' (HTML/JSON en texto) o 'zoom_file' (archivo HTML/JSON)."
        )

    input_path = f"temp_in_{file.filename}"
    output_path = f"temp_out_{file.filename}"
    temp_zoom_path = None

    try:
        # 1. Guardar el archivo CSV temporalmente
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 2. Obtener la fuente de datos de Zoom
        fuente_zoom = ""
        if zoom_data:
            fuente_zoom = zoom_data
        elif zoom_file:
            temp_zoom_path = f"temp_zoom_{zoom_file.filename}"
            with open(temp_zoom_path, "wb") as buffer:
                shutil.copyfileobj(zoom_file.file, buffer)
            with open(temp_zoom_path, "r", encoding="utf-8", errors="ignore") as f:
                fuente_zoom = f.read()

        # 3. Procesar asistencia
        procesar_asistencia(input_path, output_path, fuente_zoom)

        # 4. Devolver archivo procesado
        return FileResponse(
            path=output_path,
            filename=f"resultado_{file.filename}",
            media_type="text/csv"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar asistencia: {str(e)}")

    finally:
        # Limpieza de archivos temporales de entrada
        if os.path.exists(input_path):
            try:
                os.remove(input_path)
            except OSError:
                pass
        if temp_zoom_path and os.path.exists(temp_zoom_path):
            try:
                os.remove(temp_zoom_path)
            except OSError:
                pass


@app.post("/api/marcar-asistencia-excel/")
async def marcar_asistencia_excel_endpoint(
    file: UploadFile = File(..., description="Archivo Excel (.xlsx) con la lista de alumnos"),
    zoom_data: Optional[str] = Form(None, description="Datos de Zoom en formato HTML o JSON string"),
    zoom_file: Optional[UploadFile] = File(None, description="Archivo HTML o JSON de Zoom"),
    col_offset: int = Form(1, description="Columnas a la derecha del nombre donde se escribe la asistencia")
):
    """
    Recibe un archivo Excel con la lista de alumnos y la fuente de datos de Zoom.
    Escribe \"Sí\" o \"No\" en la columna inmediatamente a la derecha de cada nombre.
    Devuelve el archivo Excel modificado.
    Si un alumno de Zoom no está en el Excel, se ignora.
    """
    if not zoom_data and not zoom_file:
        raise HTTPException(
            status_code=400,
            detail="Debes proporcionar 'zoom_data' (HTML/JSON en texto) o 'zoom_file' (archivo HTML/JSON)."
        )

    # Guardar el xlsx recibido con un nombre temporal
    input_xlsx = f"temp_in_{file.filename}"
    output_xlsx = f"temp_out_{file.filename}"
    temp_zoom_path = None

    try:
        # 1. Guardar el Excel temporalmente
        with open(input_xlsx, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Copiar a archivo de salida (se modifica in-place en marcar_asistencia_excel)
        shutil.copy2(input_xlsx, output_xlsx)

        # 2. Obtener la fuente de datos de Zoom
        fuente_zoom = ""
        if zoom_data:
            fuente_zoom = zoom_data
        elif zoom_file:
            temp_zoom_path = f"temp_zoom_{zoom_file.filename}"
            with open(temp_zoom_path, "wb") as buffer:
                shutil.copyfileobj(zoom_file.file, buffer)
            with open(temp_zoom_path, "r", encoding="utf-8", errors="ignore") as f:
                fuente_zoom = f.read()

        # 3. Marcar asistencia en el Excel
        marcar_asistencia_excel(output_xlsx, fuente_zoom, col_offset=col_offset)

        # 4. Devolver el archivo Excel modificado
        return FileResponse(
            path=output_xlsx,
            filename=f"asistencia_{file.filename}",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar Excel: {str(e)}")

    finally:
        if os.path.exists(input_xlsx):
            try:
                os.remove(input_xlsx)
            except OSError:
                pass
        if temp_zoom_path and os.path.exists(temp_zoom_path):
            try:
                os.remove(temp_zoom_path)
            except OSError:
                pass


def ejecutar_cli(csv_path: str, html_path: str, output_path: str):
    """
    Ejecuta el procesamiento de asistencia por línea de comandos e imprime un reporte.

    Parameters
    ----------
    csv_path : str
        Ruta al archivo CSV con la lista de alumnos.
    html_path : str
        Ruta al archivo HTML exportado del panel de Participantes de Zoom.
    output_path : str
        Ruta donde se escribirá el CSV de resultado.

    Side effects
    ------------
    Escribe el CSV de salida en ``output_path`` y muestra el reporte en stdout.
    """
    print("=" * 60)
    print("PROCESADOR DE ASISTENCIA ZOOM")
    print("=" * 60)
    print(f"Lista de alumnos : {csv_path}")
    print(f"HTML de Zoom     : {html_path}")
    print(f"Reporte salida   : {output_path}")
    print("-" * 60)

    if not os.path.exists(csv_path):
        print(f"[!] Error: No se encontro el archivo CSV '{csv_path}'.")
        return

    if not os.path.exists(html_path):
        print(f"[!] Error: No se encontro el archivo HTML '{html_path}'.")
        return

    with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
        html_content = f.read()

    participantes = extraer_participantes_zoom(html_content)
    print(f"Participantes detectados en Zoom ({len(participantes)}):")
    for norm_k, info in participantes.items():
        cam_txt = "Encendida" if info["camera_on"] else "Apagada"
        print(f"   - {info['nombre_original']} -> Camara: {cam_txt}")

    print("-" * 60)
    resultados = procesar_asistencia(csv_path, output_path, html_content)

    print("REPORTE DE ASISTENCIA GENERADO:")
    print(f"{'#':<4} {'Alumno':<25} {'Asistencia':<14} {'Camara':<10}")
    print("-" * 60)
    for idx, row in enumerate(resultados[1:], 1):
        nombre, asistencia, camara = row[0], row[1], row[2]
        print(f"{idx:<4} {nombre:<25} {asistencia:<14} {camara}")

    print("=" * 60)
    print(f"Reporte guardado con exito en: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Procesador de Asistencia Zoom")
    parser.add_argument("--server", action="store_true", help="Iniciar el servidor API FastAPI")
    parser.add_argument("--csv", default="lista_alumnos.csv", help="Ruta al archivo CSV de alumnos")
    parser.add_argument("--html", default="formato-ejemplo.html", help="Ruta al archivo HTML de Zoom")
    parser.add_argument("--out", default="reporte_asistencia.csv", help="Ruta para el archivo CSV de salida")
    parser.add_argument("--port", type=int, default=8000, help="Puerto para el servidor FastAPI")
    parser.add_argument("--xlsx", default=None, help="Ruta al archivo Excel (.xlsx) para marcar asistencia directamente")
    parser.add_argument("--xlsx-out", default=None, help="Ruta de salida del Excel modificado (por defecto sobreescribe el original)")

    args = parser.parse_args()

    if args.server:
        print(f"Iniciando servidor FastAPI en http://127.0.0.1:{args.port}...")
        uvicorn.run(app, host="127.0.0.1", port=args.port)
    elif args.xlsx:
        # Modo Excel: marcar asistencia directamente en el xlsx
        xlsx_path = args.xlsx
        xlsx_out = args.xlsx_out or xlsx_path

        if not os.path.exists(xlsx_path):
            print(f"[!] Error: No se encontró el archivo Excel '{xlsx_path}'.")
            sys.exit(1)
        if not os.path.exists(args.html):
            print(f"[!] Error: No se encontró el archivo HTML de Zoom '{args.html}'.")
            sys.exit(1)

        # Si la salida es distinta al original, copiar primero
        if xlsx_out != xlsx_path:
            shutil.copy2(xlsx_path, xlsx_out)

        with open(args.html, "r", encoding="utf-8", errors="ignore") as f:
            html_content = f.read()

        print("=" * 60)
        print("MARCADO DE ASISTENCIA EN EXCEL")
        print("=" * 60)
        resumen = marcar_asistencia_excel(xlsx_out, html_content)
        print(f"Archivo Excel   : {xlsx_out}")
        print(f"Presentes       : {resumen['presentes']}")
        print(f"Ausentes        : {resumen['ausentes']}")
        print(f"Total procesados: {resumen['total']}")
        print("-" * 60)
        for nombre, estado in resumen["filas"]:
            icono = "✓" if estado == "Sí" else "✗"
            print(f"  {icono} {nombre:<30} {estado}")
        print("=" * 60)
        print(f"Excel guardado en: {xlsx_out}")
    else:
        ejecutar_cli(args.csv, args.html, args.out)