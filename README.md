# Zoom Attendance Tracker

### Toma de asistencia automática para Zoom

Una extensión de Google Chrome para tomar asistencia automáticamente en reuniones de Zoom web. Compara a los participantes conectados con tu lista de alumnos en formato CSV, y genera un reporte d[...]

---

## ¿Qué necesito?

- **Google Chrome** (o un navegador basado en Chromium).
- **Reuniones de Zoom en el navegador web** (accediendo a través de [zoom.us](https://zoom.us)).
- La carpeta `extension` incluida en este proyecto.

> [!NOTE]
> ¡No necesitas instalar Python, servidores ni ninguna otra herramienta extra para usar la extensión! Todo corre localmente en tu navegador.

---

## Instalación (Solo la primera vez — 2 minutos)

## Instalación (Solo la primera vez — 2 minutos)

1. **Abre Google Chrome** e ingresa a la siguiente dirección:
   ```text
   chrome://extensions/
   ```
2. **Activa el "Modo de desarrollador"** con el interruptor ubicado en la esquina **superior derecha** (debe quedar activo en azul).
3. Haz clic en el botón **"Cargar extensión sin comprimir"** (ubicado arriba a la izquierda).
4. **Selecciona la carpeta correcta**: En la ventana emergente, navega hasta los archivos del proyecto y selecciona la carpeta llamada `extension`.
   > [!IMPORTANT]
   > Selecciona la carpeta **`extension`**, NO la carpeta contenedora principal.
5. **Fija la extensión**: Haz clic en el ícono de rompecabezas (arriba a la derecha en Chrome), busca **Zoom Attendance Tracker** y haz clic en el ícono de pin para tenerlo siempre a mano[...]

> [!TIP]
> **Aviso normal de Chrome:** Al abrir el navegador, es posible que aparezca un aviso indicando que _"Las extensiones en modo de desarrollador están habilitadas"_. Esto es normal; simplemente haz cli[...]

---

## Uso en cada clase (30 segundos)

## Uso en cada clase (30 segundos)

### Paso Previo: Preparar el listado de alumnos

Necesitas un archivo CSV con la lista de tus alumnos. Puedes editar el archivo de ejemplo `lista_alumnos.csv` con Excel o cualquier editor de texto.

**Formato del CSV:**
| Nombre |
| :--- |
| Ana Perez |
| Juan Gomez |
| Maria Lopez |

> [!TIP]
> La extensión compara nombres de forma inteligente. Los nombres con o sin tildes/acentos funcionan igual (ej. _"María López"_ coincidirá con _"Maria Lopez"_ en Zoom).

### Durante la reunión:

1. Únete a tu reunión de Zoom desde **Google Chrome** (en [zoom.us](https://zoom.us)).
2. Abre el panel de **"Participantes"** de Zoom (haciendo clic en el botón _Participantes_ en la barra inferior de Zoom).
3. Haz clic en el ícono de la extensión en la barra de Chrome.
4. En el menú de la extensión:
   - Haz clic en **"Elegir archivo"** y selecciona tu archivo CSV con la lista de alumnos.
   - Haz clic en **"Escanear y procesar asistencia"**.
5. En unos segundos verás una tabla con los resultados (Presente / Ausente) junto con el estado de su cámara.
6. Haz clic en **"Descargar reporte CSV"** para guardar el archivo con la asistencia del día.

---

## Desarrollo y Servidor API (Opcional)

Si eres desarrollador y deseas correr la API local en FastAPI o compilar la aplicación para Windows:

### Requisitos del entorno

1. Instala las dependencias necesarias:
   ```bash
   pip install -r requirements.txt
   ```
2. Para iniciar el servidor de desarrollo FastAPI:
   ```bash
   python main.py --server
   ```
3. Para ejecutar pruebas:
   ```bash
   pytest
   ```
4. Para compilar el ejecutable para Windows:
   - Ejecuta `build.bat` para compilar el ejecutable en `dist/ZoomAttendanceServer.exe`.
   - Ejecuta `empaquetar.bat` para crear un archivo comprimido de distribución.

---

## Solución de Problemas

## Solución de Problemas

- **Problema: "No se detectó la lista de participantes"**
  - _Solución:_ Asegúrate de estar en la reunión de Zoom dentro de Chrome (no en la aplicación de escritorio) y de tener el panel "Participantes" abierto. Si acabas de instalar la extensión, [...]
- **Problema: Todos los alumnos figuran como "Ausente"**
  - _Solución:_ Verifica que el panel de Participantes esté abierto. Compara si los nombres en Zoom coinciden visualmente con los nombres que escribiste en el archivo CSV.
- **Problema: No puedo abrir el CSV con Excel / aparece todo en una sola línea**
  - _Solución:_ Haz doble clic en el archivo CSV y elige _"Abrir con Excel"_. O en Excel ve a `Datos` ➔ `Desde texto/CSV` y selecciona el archivo para importarlo correctamente.
- **Problema: Chrome advierte sobre las extensiones de desarrollador**
  - _Solución:_ Es una advertencia estándar de seguridad de Chrome. Simplemente haz clic en "Mantener" o descártala.
