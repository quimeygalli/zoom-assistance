<<<<<<< HEAD
# Zoom Assistance Tracker

Extensión de Chrome que cruza la lista de participantes activos en una reunión de Zoom con un registro CSV y genera un reporte de asistencia descargable.

Sin servidor externo, sin dependencias — todo corre en el navegador.

---

## Requisitos

- Google Chrome
- Reuniones de Zoom accedidas desde `zoom.us` en el navegador (no la app de escritorio)

---

## Instalación

1. Abrí `chrome://extensions/` en Chrome.
2. Activá el **Modo de desarrollador** (switch en la esquina superior derecha).
3. Hacé clic en **Cargar extensión sin comprimir** y seleccioná la carpeta `extension/`.
4. Fijá la extensión en la barra de Chrome para tenerla siempre a mano.

> Chrome puede mostrar el aviso "Las extensiones en modo de desarrollador están habilitadas" al iniciar. Es normal — cerralo o hacé clic en **Mantener**.

---

## Uso

1. Entrá a una reunión de Zoom en Chrome y abrí el panel de **Participantes**.
2. Hacé clic en el ícono de la extensión.
3. Cargá tu lista de alumnos en formato CSV (un nombre por fila, encabezado `Nombre` opcional).
4. Hacé clic en **Escanear y procesar asistencia**.
5. Revisá la tabla de resultados y hacé clic en **Descargar reporte CSV** para guardar el archivo.

### Formato del CSV

```
Nombre
Ana Perez
Juan Gomez
Maria Lopez
```

Los nombres con y sin tilde se tratan como equivalentes (`María López` coincide con `Maria Lopez`).

---

## Cómo funciona

La extensión inyecta un script en la pestaña activa de Zoom para extraer la lista de participantes del DOM. Luego normaliza los nombres (elimina diacríticos, sufijos de Zoom como `(yo)`, `(anfitrión)`, tokens numéricos) y aplica una coincidencia flexible por subconjunto de tokens — `Juan Gimenez` coincide con `Juan Pablo Gimenez` y viceversa. Los resultados se muestran en el popup y se exportan como CSV UTF-8 con asistencia y estado de cámara por alumno.

---

## Permisos

| Permiso | Propósito |
|---|---|
| `activeTab` | Leer la pestaña activa de Zoom |
| `scripting` | Inyectar el script de extracción de participantes |
| `https://*.zoom.us/*` | Restringir el acceso de host únicamente a Zoom |

---

## Estructura del proyecto

```
zoom-assistance/
    extension/
        manifest.json
        popup.html
        popup.js
        icons/
    INSTRUCCIONES.txt     # guía de instalación para el usuario final
```

---

## Solución de problemas

**No se detectan participantes** — Confirmá que el panel de Participantes esté abierto dentro del cliente web de Zoom, no en la app de escritorio. Si la extensión fue instalada recientemente, recargá la pestaña de Zoom e intentá nuevamente.

**Todos los alumnos figuran como ausentes** — Verificá que los nombres de pantalla en Zoom sean similares a los del CSV.

**El CSV no se abre correctamente en Excel** — Usá **Datos > Desde texto/CSV** en Excel, o hacé doble clic en el archivo y seleccioná el delimitador correcto.
=======
============================================================
  ZOOM ATTENDANCE TRACKER
  Toma de asistencia automática para Zoom
============================================================

¿QUÉ NECESITO?
  - Google Chrome (ya lo tenés instalado)
  - Reuniones de Zoom en el navegador web (zoom.us)
  - La carpeta "extension" que te compartieron

  ¡No necesitás instalar Python, servidores, ni nada extra!


============================================================
  INSTALACIÓN (solo la primera vez — 2 minutos)
============================================================

PASO 1 → Abrí Google Chrome

PASO 2 → En la barra de direcciones de Chrome, escribí exactamente:

            chrome://extensions/

         y presioná Enter.

PASO 3 → Activá el "Modo de desarrollador"
         Buscá el switch que dice "Modo de desarrollador"
         en la esquina SUPERIOR DERECHA de la pantalla
         y hacé clic para activarlo (debe quedar en azul).

PASO 4 → Cargá la extensión
         Hacé clic en el botón "Cargar extensión sin comprimir"
         (aparece arriba a la izquierda).

PASO 5 → Seleccioná la carpeta correcta
         Se abrirá una ventana para elegir carpeta.
         Navegá hasta donde descomprimiste los archivos
         y seleccioná la carpeta que se llama "extension".

         !! IMPORTANTE: seleccioná la carpeta "extension",
            NO la carpeta que la contiene !!

PASO 6 → ¡Listo! La extensión aparecerá en la lista con el
         nombre "Zoom Attendance Tracker" y el ícono.

PASO 7 → Fijá la extensión en la barra de Chrome
         Hacé clic en el ícono de pieza de rompecabezas 🧩
         (arriba a la derecha en Chrome).
         Buscá "Zoom Attendance Tracker" y hacé clic en el
         ícono 📌 para fijarlo. Así lo tenés siempre a mano.

------------------------------------------------------------
AVISO NORMAL DE CHROME
------------------------------------------------------------
Al abrir Chrome, puede aparecer una notificación que dice
"Las extensiones en modo de desarrollador están habilitadas".
Esto es normal y esperado. Podés hacer clic en:
  → "Mantener" o simplemente ignorarlo y cerrarlo.
No afecta el funcionamiento de la extensión.
------------------------------------------------------------


============================================================
  USO EN CADA CLASE (30 segundos)
============================================================

Antes de empezar: necesitás un archivo CSV con la lista de
tus alumnos. Podés usar el archivo "lista_alumnos.csv"
de ejemplo y editarlo con Excel o el Bloc de notas.

  Formato del CSV:
  ┌─────────────┐
  │ Nombre      │
  │ Ana Perez   │
  │ Juan Gomez  │
  │ Maria Lopez │
  └─────────────┘

  TIP: Los nombres con o sin tilde funcionan igual.
       "María López" coincide con "Maria Lopez" en Zoom.


--- Durante la reunión ---

1. Entrá a la reunión de Zoom en Google Chrome (zoom.us)

2. Abrí el panel de "Participantes" en Zoom
   (botón "Participantes" en la barra de abajo de Zoom)

3. Hacé clic en el ícono de la extensión en Chrome
   (el ícono azul que fijaste antes)

4. En el popup que aparece:
   → Hacé clic en "Elegir archivo"
   → Seleccioná tu archivo CSV con la lista de alumnos

5. Hacé clic en "Escanear y procesar asistencia"

6. En unos segundos verás la tabla con los resultados:
   ✓ Presente / ✗ Ausente y estado de la cámara

7. Hacé clic en "Descargar reporte CSV" para guardar el
   archivo con la asistencia del día.


============================================================
  SOLUCIÓN DE PROBLEMAS
============================================================

PROBLEMA: "No se detectó la lista de participantes"
SOLUCIÓN:
  → Verificá que estés en la reunión de Zoom DENTRO de Chrome
     (no en la app de escritorio de Zoom)
  → Asegurate de tener el panel "Participantes" abierto
  → Si instalaste la extensión hace poco, recargá la página
     de Zoom y volvé a intentarlo

PROBLEMA: Todos los alumnos figuran como "Ausente"
SOLUCIÓN:
  → Verificá que el panel de Participantes esté abierto en Zoom
  → Compará visualmente que los nombres en Zoom sean similares
     a los del CSV (apellidos, nombres, orden)

PROBLEMA: No puedo abrir el CSV con Excel / aparece todo junto
SOLUCIÓN:
  → Hacé doble clic en el archivo CSV → elegí "Abrir con Excel"
  → O en Excel: Datos → Desde texto/CSV → elegí el archivo

PROBLEMA: Chrome me advierte sobre extensiones de desarrollador
SOLUCIÓN:
  → Es normal, hacé clic en "Mantener" y seguí usando la extensión

============================================================
>>>>>>> 331b947 (Add requirements.txt, instructions, and build icon)
