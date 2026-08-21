# Contributing & Developer Guide

> **Zoom Attendance Tracker** — Developer Reference
>
> This document is aimed at developers and technical contributors who want to understand, modify, or extend the project. For end-user instructions, see [`README.md`](./README.md).

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Repository Layout](#repository-layout)
3. [How It Works — End-to-End Flow](#how-it-works--end-to-end-flow)
4. [Chrome Extension (`extension/`)](#chrome-extension-extension)
   - [manifest.json](#manifestjson)
   - [popup.js — Core Logic](#popupjs--core-logic)
5. [Python Backend (Optional)](#python-backend-optional)
   - [core.py — Shared Business Logic](#corepy--shared-business-logic)
   - [main.py — FastAPI App & CLI](#mainpy--fastapi-app--cli)
   - [server.py — Windows `.exe` Entry Point](#serverpy--windows-exe-entry-point)
6. [Running the Project Locally](#running-the-project-locally)
7. [Testing](#testing)
8. [Building the Windows Executable](#building-the-windows-executable)
9. [Packaging for Distribution](#packaging-for-distribution)
10. [Key Design Decisions](#key-design-decisions)
11. [Known Gotchas & Fragile Points](#known-gotchas--fragile-points)
12. [Extending the Project](#extending-the-project)

---

## Architecture Overview

The project has **two independent operating modes**. Pick the one that fits the deployment scenario:

```
┌──────────────────────────────────────────────────────────┐
│                   MODE 1 (DEFAULT)                       │
│            Browser-only · No server needed               │
│                                                          │
│  ┌────────────┐   DOM scrape   ┌────────────────────┐   │
│  │ Zoom Web   │ ─────────────► │ Chrome Extension   │   │
│  │ (zoom.us)  │                │  popup.js          │   │
│  └────────────┘                │  - scrapeZoomData  │   │
│                                │  - parsearCSV      │   │
│  ┌────────────┐   CSV file     │  - procesarAsist.  │   │
│  │ lista_     │ ─────────────► │  - generarCSV      │   │
│  │ alumnos    │                └──────────┬─────────┘   │
│  └────────────┘                           │ .csv        │
│                                           ▼             │
│                                    Downloaded file      │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                   MODE 2 (OPTIONAL)                      │
│       Python API (FastAPI) · For developers/CI           │
│                                                          │
│  POST /api/procesar-asistencia/                          │
│    · Accepts: CSV (UploadFile) + HTML/JSON (Form/File)   │
│    · Returns: CSV FileResponse                           │
│                                                          │
│  core.py ─ shared functions used by both modes          │
│  server.py ─ .exe launcher with system tray (Windows)   │
└──────────────────────────────────────────────────────────┘
```

The name-matching algorithm and camera-detection logic are **intentionally duplicated** in JavaScript (`popup.js`) and Python (`core.py`) so each mode works independently without cross-language dependencies.

---

## Repository Layout

```
zoom-asssistance/
│
├── extension/                  # Chrome Extension (MV3)
│   ├── manifest.json           #   Extension metadata and permissions
│   ├── popup.html              #   Extension popup UI (HTML/CSS)
│   ├── popup.js                #   All extension logic (scraping + processing)
│   └── icons/                  #   icon16.png, icon48.png, icon128.png
│
├── core.py                     # Python: shared parsing & matching logic
├── main.py                     # Python: FastAPI app + CLI entry point
├── server.py                   # Python: Windows .exe launcher (pystray tray icon)
├── test_zoom.py                # pytest test suite
│
├── formato-ejemplo.html        # Sample Zoom participants panel HTML (for tests)
├── lista_alumnos.csv           # Sample student list (CSV)
│
├── requirements.txt            # Python dependencies
├── build.bat                   # PyInstaller build script (Windows)
├── empaquetar.bat              # Distribution packaging script (Windows)
├── INSTRUCCIONES.txt           # End-user instructions (Spanish)
│
├── README.md                   # End-user documentation
├── CONTRIBUTING.md             # ← This file
└── icon.png                    # App icon (used by .exe and extension)
```

---

## How It Works — End-to-End Flow

### Mode 1: Chrome Extension (no Python required)

1. **User is inside a Zoom meeting** on `zoom.us` in Chrome with the Participants panel open.
2. User clicks the extension icon → popup opens.
3. User selects their student CSV file.
4. User clicks **"Escanear y procesar asistencia"**.
5. `popup.js` calls `chrome.scripting.executeScript` to inject `scrapeZoomData()` into **all frames** of the active tab.
6. `scrapeZoomData()` reads the live DOM and returns a `{ name: { camera_on: bool } }` object.
7. The popup parses the uploaded CSV with `parsearCSV()`.
8. `procesarAsistencia()` normalizes all names and cross-references both lists.
9. The result table is rendered inline and a UTF-8 BOM CSV is generated in memory.
10. User clicks **"Descargar reporte CSV"** to save the file.

### Mode 2: Python API

1. Client sends a `POST /api/procesar-asistencia/` with:
   - `file`: the student CSV (`UploadFile`)
   - `zoom_data`: raw HTML or JSON string (`Form`), **or**
   - `zoom_file`: an HTML/JSON file (`UploadFile`)
2. `main.py` saves both inputs to temp files, calls `procesar_asistencia()` from `core.py`, and returns the result CSV as a `FileResponse`.
3. Temp files are cleaned up in the `finally` block regardless of success or failure.

---

## Chrome Extension (`extension/`)

### `manifest.json`

| Field | Value | Notes |
|---|---|---|
| `manifest_version` | `3` | MV3 is required for modern Chrome |
| `permissions` | `activeTab`, `scripting` | Needed to inject `scrapeZoomData` into the tab |
| `host_permissions` | `https://*.zoom.us/*` | Restricts injection to Zoom pages only |

> **⚠️ Why `allFrames: true`?**
> Zoom Web embeds its participants panel inside an `<iframe>`. Without `allFrames: true` in `executeScript`, the injected script would only run in the top-level frame and would never find the participants DOM.

### `popup.js` — Core Logic

The file is structured in two distinct scopes:

#### Injected scope — `scrapeZoomData()`
This function runs **inside the Zoom tab's page context**, not in the extension popup. It has no access to extension APIs or popup variables.

**Participant detection strategy (3-tier fallback):**
```
1. document.getElementById("participants-ul") → .querySelectorAll(".participants-li, [id^='participants-list-']")
2. document.querySelectorAll(".participants-li, [id^='participants-list-']")  (global search)
3. [aria-label="Participants list"] or [aria-label="Lista de participantes"] → children with role='application'
```

**Camera state detection:**
- `svg[class*="video-off"]` present → camera OFF
- `aria-label` contains `"video off"` or `"video apagado"` → camera OFF
- `svg[class*="video-on"]` or aria `"video on"` → camera ON
- Default (no icon found) → camera ON (Zoom omits the video-off icon when cam is active)

#### Popup scope — all other functions

| Function | Purpose |
|---|---|
| `leerArchivo(file)` | Reads a `File` object as UTF-8 text via `FileReader` |
| `parsearCSV(text)` | Splits by newline, auto-detects and skips header (`"nombre"`, `"name"`, `"alumno"`) |
| `normalizar(nombre)` | NFD decomposition → strip diacritics → lowercase → strip Zoom suffixes |
| `procesarAsistencia(alumnos, zoomData)` | Normalizes zoom keys, cross-references students, returns `{ filas, resumen }` |
| `generarCSV(filas)` | Serializes rows to RFC 4180 CSV with `"` quoting |
| `renderTabla(filas)` | Dynamically builds the HTML table in the popup |

---

## Python Backend (Optional)

### `core.py` — Shared Business Logic

Two main exported functions:

#### `normalizar_nombre(nombre: str) -> str`
Pure function. Applies the same normalization pipeline as the JS `normalizar()`:
- `unicodedata.normalize('NFKD')` + strip combining characters → removes diacritics
- `re.sub(r'\s+', ' ')` → collapse whitespace
- `.lower()` → lowercase
- Regex strip of Zoom suffixes: `(yo)`, `(anfitrión)`, `(coanfitrión)`, `(host)`, `(co-host)`, `(me)`, `(guest)`, `(invitado)`

#### `extraer_participantes_zoom(html_content: str) -> dict`
Parses raw HTML with `BeautifulSoup`. Returns:
```python
{
    "normalized_name": {
        "nombre_original": str,
        "camera_on": bool,
        "aria_label": str
    }
}
```

Uses the same 3-tier fallback strategy as the JS scraper (class `participants-li` → ID prefix → layout class).

#### `procesar_asistencia(input_csv, output_csv, zoom_source) -> list`
Orchestrator function. `zoom_source` can be:
- `dict` → used directly
- `str` path to a file → read and auto-detect (HTML or JSON)
- `str` raw HTML → parsed with BeautifulSoup
- `str` raw JSON → `json.loads()`

CSV reading tries multiple encodings in order: `utf-8-sig → utf-8 → latin-1 → cp1252`.
Output CSV is always written as `utf-8-sig` (UTF-8 with BOM), which opens correctly in Excel without import dialogs.

### `main.py` — FastAPI App & CLI

**API endpoint:** `POST /api/procesar-asistencia/`

```
Request (multipart/form-data):
  file       (required) — CSV UploadFile
  zoom_data  (optional) — HTML or JSON string
  zoom_file  (optional) — HTML or JSON UploadFile

Response:
  200 OK — text/csv FileResponse
  400 Bad Request — if neither zoom_data nor zoom_file is provided
  500 Internal Server Error — on processing failure
```

**CLI mode:** `python main.py --csv <path> --html <path> --out <path>`

Prints a formatted attendance table to stdout and writes the CSV.

**Server mode:** `python main.py --server [--port 8000]`

Starts the uvicorn server. The FastAPI auto-docs are available at `http://127.0.0.1:8000/docs`.

### `server.py` — Windows `.exe` Entry Point

This file is the PyInstaller entry point and is **not needed for development**. It:
1. Checks if port 8000 is already in use (single-instance guard).
2. Starts the uvicorn server on a **daemon thread**.
3. Creates a `pystray` system tray icon with a menu to open API docs, toggle Windows autostart, and quit.
4. Handles the `icon.png` path correctly whether running as `.py` or as a frozen `.exe` via `sys._MEIPASS`.

> **Note:** The `winreg` module (used for autostart) is Windows-only. `server.py` will not run on Linux/macOS.

---

## Running the Project Locally

### Extension only (no Python)
1. Open `chrome://extensions/` in Chrome.
2. Enable Developer Mode.
3. Click **Load unpacked** and select the `extension/` folder.
4. Navigate to a Zoom meeting at `zoom.us`.

### Python backend
```bash
# 1. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate      # Linux/macOS
.venv\Scripts\activate.bat     # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the API server
python main.py --server

# 4. Or run the CLI tool
python main.py --csv lista_alumnos.csv --html formato-ejemplo.html --out reporte.csv
```

The API server starts at `http://127.0.0.1:8000`. Interactive docs at `http://127.0.0.1:8000/docs`.

---

## Testing

Tests use `pytest` and `fastapi.testclient`. Run from the project root:

```bash
pytest -v
```

| Test | What it covers |
|---|---|
| `test_normalizar_nombre` | Name normalization: accents, Zoom suffixes, whitespace |
| `test_extraer_participantes_ejemplo` | HTML parsing against the real `formato-ejemplo.html` fixture |
| `test_extraer_participante_camara_encendida` | Camera-on detection from inline SVG and aria-label |
| `test_procesar_asistencia_con_html_y_tildes` | Full pipeline: CSV + HTML → CSV output, accent-insensitive matching |
| `test_fastapi_endpoint_con_html` | API endpoint with HTML `zoom_data` |
| `test_fastapi_endpoint_con_json` | API endpoint with JSON `zoom_data` |

> **`formato-ejemplo.html`** is the reference Zoom HTML snapshot used by tests. If Zoom changes its DOM structure, update this file and adjust tests accordingly.

---

## Building the Windows Executable

> Requires Windows and PyInstaller installed in the virtual environment.

```bat
REM Activate venv first, then:
build.bat
```

This runs PyInstaller with `--onefile --windowed`, bundling `server.py` as the entry point, with `icon.png` and `core.py` embedded as data files. Output: `dist/ZoomAttendanceServer.exe`.

**Hidden imports** are explicitly declared in `build.bat` to avoid PyInstaller missing dynamically loaded uvicorn/pystray modules.

---

## Packaging for Distribution

```bat
empaquetar.bat
```

Creates `ZoomAttendanceTracker.zip` containing:
- `extension/` folder (ready to load in Chrome)
- `lista_alumnos.csv` (sample student list)
- `INSTRUCCIONES.txt` (end-user instructions)

> The `.exe` is **not** included in the distribution ZIP — it is distributed separately when needed, as most end users only need the Chrome extension.

---

## Key Design Decisions

### 1. Browser-first, server-optional
The extension was intentionally redesigned in v2.0 to run entirely in the browser. Earlier versions required the Python server to be running locally. This change eliminated the main friction point for non-technical users (installing Python, starting a process, etc.).

### 2. Name normalization is the core feature
The accent-insensitive, suffix-stripping normalization is the most critical piece of logic. Both `core.py` and `popup.js` implement it identically. Any change must be mirrored in both files and covered by tests.

### 3. CSV output with UTF-8 BOM
Output CSVs use `utf-8-sig` encoding (UTF-8 with a BOM prefix `\uFEFF`). This makes them open natively in Microsoft Excel on Windows without needing the import wizard — a common pain point for the target audience (teachers).

### 4. `allFrames: true` in scripting injection
Zoom Web renders the participant list inside an iframe. Without `allFrames: true`, the extension would silently fail to detect any participants.

### 5. Camera detection defaults to ON
When neither `video-on` nor `video-off` signals are found for a participant, the code defaults to `camera_on = true`. This is intentional: Zoom only renders the video-off icon when a camera is off, so absence of the icon is a positive signal.

---

## Known Gotchas & Fragile Points

| Area | Risk | Mitigation |
|---|---|---|
| **Zoom DOM structure** | Zoom can change class names or HTML structure in any update | Update `formato-ejemplo.html` and scraping selectors after Zoom updates; tests will catch regressions |
| **iframe detection** | If Zoom moves the participants panel to a different frame or a shadow DOM, the selector strategies may break | The 3-tier fallback is designed to be resilient; add a 4th strategy if needed |
| **CORS (API mode)** | `allow_origins=["*"]` is intentional for local use only — do not expose this API to the internet | Keep the server bound to `127.0.0.1` |
| **Temp file cleanup** | On Windows, `FileResponse` may hold a file handle when the `finally` block tries to delete it | The `try/except OSError: pass` handles this gracefully; the OS will clean up on process exit |
| **`winreg` import** | `server.py` imports `winreg` inside functions, not at module level, to avoid ImportError on Linux | Do not move these imports to the top of the file |
| **PyInstaller hidden imports** | Adding new dependencies to `server.py` / `main.py` may require adding new `--hidden-import` entries to `build.bat` | Always test the `.exe` after adding dependencies |

---

## Extending the Project

### Adding a new Zoom suffix to strip
Edit the regex in both places:
- `core.py` → `normalizar_nombre()`, the `re.sub(...)` pattern
- `extension/popup.js` → `normalizar()`, the `.replace(...)` regex

Then add a test case in `test_zoom.py::test_normalizar_nombre`.

### Supporting a new CSV column (e.g., student ID)
- `core.py` → `procesar_asistencia()`: read additional columns from the input CSV and write them to output
- `extension/popup.js` → `parsearCSV()` and `procesarAsistencia()`: extend to carry through extra fields
- `extension/popup.js` → `renderTabla()`: add the new column to the table

### Adding a new camera detection signal
- `core.py` → `extraer_participantes_zoom()`: extend the detection block around line 93
- `extension/popup.js` → `scrapeZoomData()`: extend the camera detection block around line 170
- Add a test in `test_zoom.py`

### Modifying the API
- All routes live in `main.py`. Add new routes there.
- `core.py` should stay as pure functions with no FastAPI dependencies — this keeps it testable and importable independently.
