import os
import csv
import json
import pytest
from fastapi.testclient import TestClient

from core import normalizar_nombre, extraer_participantes_zoom, procesar_asistencia
from main import app


def test_normalizar_nombre():
    assert normalizar_nombre("María López") == "maria lopez"
    assert normalizar_nombre("  Carlos Díaz  ") == "carlos diaz"
    assert normalizar_nombre("Alejo Rossi (Anfitrión, yo)") == "alejo rossi"
    assert normalizar_nombre("Profesor (Host)") == "profesor"
    assert normalizar_nombre("Juan Perez (Co-host)") == "juan perez"
    assert normalizar_nombre("Ana (Guest)") == "ana"


def test_extraer_participantes_ejemplo():
    with open("formato-ejemplo.html", "r", encoding="utf-8") as f:
        html = f.read()

    participantes = extraer_participantes_zoom(html)
    
    assert "alejo rossi" in participantes
    assert participantes["alejo rossi"]["nombre_original"] == "Alejo Rossi"
    assert participantes["alejo rossi"]["camera_on"] is False  # Apagada
    
    assert "quimey galli" in participantes
    assert participantes["quimey galli"]["nombre_original"] == "Quimey Galli"
    assert participantes["quimey galli"]["camera_on"] is False  # Apagada


def test_extraer_participante_camara_encendida():
    html_on = """
    <div id="participants-ul">
        <div class="participants-li" aria-label="Laura Gomez,computer audio unmuted,video on">
            <span class="participants-item__display-name">Laura Gomez</span>
            <div class="participants-item__right-section">
                <svg class="lazy-icon-icons/participants-list/video-on"></svg>
            </div>
        </div>
    </div>
    """
    participantes = extraer_participantes_zoom(html_on)
    assert "laura gomez" in participantes
    assert participantes["laura gomez"]["camera_on"] is True


def test_procesar_asistencia_con_html_y_tildes(tmp_path):
    csv_in = tmp_path / "alumnos.csv"
    csv_out = tmp_path / "reporte.csv"

    # CSV con tildes y sin tildes
    with open(csv_in, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Nombre"])
        writer.writerow(["María López"])
        writer.writerow(["Carlos Diaz"])
        writer.writerow(["Alejo Rossi"])

    # HTML donde Maria no tiene tilde y tiene cámara encendida
    html_data = """
    <div id="participants-ul">
        <div class="participants-li" aria-label="Maria Lopez,video on">
            <span class="participants-item__display-name">Maria Lopez</span>
        </div>
        <div class="participants-li" aria-label="Alejo Rossi (Anfitrión),video off">
            <span class="participants-item__display-name">Alejo Rossi</span>
            <svg class="lazy-icon-icons/participants-list/video-off"></svg>
        </div>
    </div>
    """

    resultados = procesar_asistencia(str(csv_in), str(csv_out), html_data)
    
    # Header + 3 alumnos
    assert len(resultados) == 4
    assert resultados[1] == ["María López", "Presente", "Encendida"]
    assert resultados[2] == ["Carlos Diaz", "Ausente", "Apagada"]
    assert resultados[3] == ["Alejo Rossi", "Presente", "Apagada"]

    # Verificar lectura del archivo generado
    with open(csv_out, "r", encoding="utf-8-sig") as f:
        reader = list(csv.reader(f))
        assert reader[1] == ["María López", "Presente", "Encendida"]


def test_fastapi_endpoint_con_html(tmp_path):
    client = TestClient(app)

    csv_content = "Nombre\nAlejo Rossi\nCarlos Diaz\n"
    with open("formato-ejemplo.html", "r", encoding="utf-8") as f:
        html_content = f.read()

    response = client.post(
        "/api/procesar-asistencia/",
        files={"file": ("alumnos.csv", csv_content.encode("utf-8"), "text/csv")},
        data={"zoom_data": html_content}
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    
    csv_text = response.content.decode("utf-8-sig")
    assert "Alejo Rossi,Presente,Apagada" in csv_text
    assert "Carlos Diaz,Ausente,Apagada" in csv_text


def test_fastapi_endpoint_con_json():
    client = TestClient(app)

    csv_content = "Nombre\nJuan Perez\n"
    json_data = json.dumps({"Juan Perez": {"camera_on": True}})

    response = client.post(
        "/api/procesar-asistencia/",
        files={"file": ("alumnos.csv", csv_content.encode("utf-8"), "text/csv")},
        data={"zoom_data": json_data}
    )

    assert response.status_code == 200
    csv_text = response.content.decode("utf-8-sig")
    assert "Juan Perez,Presente,Encendida" in csv_text
