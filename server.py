"""
server.py — Punto de entrada para el ejecutable .exe
Inicia el servidor FastAPI de asistencia Zoom con un ícono en la bandeja del sistema.
"""
import sys
import os
import socket
import threading
import webbrowser

import pystray
from PIL import Image
import uvicorn

from main import app

# ────────────────────────────────────────────────
# Configuración
# ────────────────────────────────────────────────
HOST = "127.0.0.1"
PORT = 8000
APP_NAME = "Zoom Attendance Server"


def get_icon_image() -> Image.Image:
    """Carga el ícono embebido o genera uno genérico si no existe."""
    # PyInstaller empaqueta los datos en sys._MEIPASS cuando se genera el .exe
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    icon_path = os.path.join(base_path, "icon.png")
    if os.path.exists(icon_path):
        return Image.open(icon_path).convert("RGBA").resize((64, 64))
    # Ícono de respaldo: cuadrado sólido azul con texto
    from PIL import ImageDraw
    img = Image.new("RGBA", (64, 64), color=(30, 58, 138, 255))
    draw = ImageDraw.Draw(img)
    draw.text((14, 20), "ZA", fill=(255, 255, 255, 255))
    return img


def puerto_libre(host: str, port: int) -> bool:
    """Verifica si el puerto está disponible."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) != 0


def iniciar_servidor():
    """Corre el servidor en un hilo daemon."""
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


def on_abrir_browser(icon, item):
    webbrowser.open(f"http://{HOST}:{PORT}/docs")


def on_salir(icon, item):
    icon.stop()
    # Terminar el proceso completo (incluye el hilo de uvicorn)
    os._exit(0)


def main():
    # Verificar si ya hay una instancia corriendo
    if not puerto_libre(HOST, PORT):
        pystray.Icon(
            APP_NAME,
            get_icon_image(),
            APP_NAME,
            menu=pystray.Menu(
                pystray.MenuItem("Ya hay una instancia activa en :8000", None, enabled=False),
                pystray.MenuItem("Salir", on_salir),
            ),
        ).run()
        return

    # Iniciar el servidor en un hilo secundario
    hilo = threading.Thread(target=iniciar_servidor, daemon=True)
    hilo.start()

    # Menú del tray
    menu = pystray.Menu(
        pystray.MenuItem(f"Servidor activo en {HOST}:{PORT}", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Abrir documentacion API", on_abrir_browser),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Iniciar con Windows", on_toggle_autostart, checked=lambda item: esta_en_autostart()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Salir", on_salir),
    )

    icon = pystray.Icon(APP_NAME, get_icon_image(), APP_NAME, menu)
    icon.run()


# ────────────────────────────────────────────────
# Inicio automático con Windows (registro)
# ────────────────────────────────────────────────
def _exe_path() -> str:
    """Ruta del ejecutable actual (funciona tanto en .py como en .exe)."""
    return sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__)


def esta_en_autostart() -> bool:
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ,
        )
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except (FileNotFoundError, OSError):
        return False


def on_toggle_autostart(icon, item):
    import winreg
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0, winreg.KEY_SET_VALUE,
    )
    if esta_en_autostart():
        winreg.DeleteValue(key, APP_NAME)
    else:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{_exe_path()}"')
    winreg.CloseKey(key)


if __name__ == "__main__":
    main()
