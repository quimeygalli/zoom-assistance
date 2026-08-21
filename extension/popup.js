// ============================================================
// Zoom Attendance Tracker — popup.js
// Toda la lógica corre en el browser. Sin servidor externo.
// ============================================================

document.addEventListener("DOMContentLoaded", () => {
  const processBtn   = document.getElementById("processBtn");
  const statusDiv    = document.getElementById("status");
  const resultSection = document.getElementById("resultSection");
  const resultBody   = document.getElementById("resultBody");
  const downloadBtn  = document.getElementById("downloadBtn");
  const summaryDiv   = document.getElementById("summary");

  let reporteCSV      = null; // CSV generado para el botón de descarga
  let lastZoomData    = null; // Datos del último escaneo de Zoom
  let lastXlsxMeta    = null; // { wb, wsName, ws, headerRow, colNombre, colApellido, alumnos }
  let selectedXlsxFile = null; // File reconstruido desde session storage

  const xlsxFileName = document.getElementById("xlsxFileName");
  const markExcelBtn = document.getElementById("markExcelBtn");
  const pickFileBtn  = document.getElementById("pickFileBtn");

  // Cargar archivo Excel guardado si ya existe
  cargarExcelGuardado();

  // ── Selección de archivo via ventana auxiliar ───────────────────────
  pickFileBtn.addEventListener("click", () => {
    try {
      chrome.windows.create(
        {
          url: chrome.runtime.getURL("file-picker.html"),
          type: "popup",
          width: 440,
          height: 280,
          focused: true,
        },
        (win) => {
          if (chrome.runtime.lastError || !win) {
            chrome.tabs.create({ url: chrome.runtime.getURL("file-picker.html") });
          }
        }
      );
    } catch (e) {
      chrome.tabs.create({ url: chrome.runtime.getURL("file-picker.html") });
    }
  });


  // Escuchar cuando el file-picker guarde el archivo
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.type === "xlsx-ready") {
      cargarExcelGuardado();
    }
  });

  async function cargarExcelGuardado() {
    try {
      const { pickedXlsxName, pickedXlsxBase64 } = await chrome.storage.local.get([
        "pickedXlsxName",
        "pickedXlsxBase64",
      ]);
      if (pickedXlsxName && pickedXlsxBase64) {
        const uint8 = base64ToUint8Array(pickedXlsxBase64);
        const blob  = new Blob([uint8], {
          type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        });
        selectedXlsxFile = new File([blob], pickedXlsxName, { type: blob.type });

        xlsxFileName.textContent = "✔ " + pickedXlsxName;
        xlsxFileName.className = "file-name selected";
      } else {
        selectedXlsxFile = null;
        xlsxFileName.textContent = "Ningún archivo seleccionado";
        xlsxFileName.className = "file-name";
      }
    } catch (err) {
      console.error("Error al cargar Excel guardado:", err);
    }
  }

  function base64ToUint8Array(base64) {
    const binaryString = atob(base64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes;
  }


  processBtn.addEventListener("click", async () => {
    if (!selectedXlsxFile) {
      setStatus("warning", "⚠️ No seleccionaste ninguna planilla. Hacé click en 'Elegir Excel'.");
      return;
    }
    if (typeof XLSX === "undefined") {
      setStatus("error", "Librería Excel no cargada. Verificá xlsx.mini.min.js.");
      return;
    }

    setStatus("loading", "Escaneando participantes de Zoom...");
    resultSection.style.display = "none";
    downloadBtn.style.display = "none";
    markExcelBtn.style.display = "none";
    reporteCSV = null;
    lastXlsxMeta = null;

    try {
      // 1. Obtener participantes de Zoom desde el DOM de la pestaña activa
      const [tab] = await chrome.tabs.query({
        active: true,
        currentWindow: true,
      });
      const injectionResults = await chrome.scripting.executeScript({
        target: { tabId: tab.id, allFrames: true },
        func: scrapeZoomData,
      });

      // Buscar el frame que devolvió datos reales
      let zoomData = null;
      for (const frameResult of injectionResults) {
        const r = frameResult.result;
        if (r && !r.error && Object.keys(r).length > 0) {
          zoomData = r;
          break;
        }
      }

      if (!zoomData) {
        const firstError = injectionResults.find(
          (r) => r.result && r.result.error,
        );
        setStatus(
          "warning",
          firstError
            ? firstError.result.error
            : "No se detectó la lista. Abrí el panel 'Participantes' en Zoom.",
        );
        return;
      }

      setStatus("loading", `${Object.keys(zoomData).length} participantes detectados. Leyendo planilla...`);

      // 2. Leer lista de alumnos desde el Excel (columnas nombre + apellido)
      const xlsxFile = selectedXlsxFile;
      const arrayBuffer = await xlsxFile.arrayBuffer();
      const wb = XLSX.read(arrayBuffer, { type: "array", cellStyles: false });
      const wsName = wb.SheetNames[0];
      const ws = wb.Sheets[wsName];

      const meta = leerAlumnosDeExcel(ws);
      if (!meta) {
        setStatus("warning", "No se encontraron columnas 'Nombre' y 'Apellido' en la planilla.");
        return;
      }

      if (meta.alumnos.length === 0) {
        setStatus("warning", "La planilla no tiene filas de datos después del encabezado.");
        return;
      }

      // Guardar meta para markExcelBtn
      lastXlsxMeta = { wb, wsName, ws, ...meta };

      // 3. Procesar asistencia
      const { filas, resumen } = procesarAsistencia(meta.alumnos, zoomData);

      // 4. Mostrar tabla de resultados en el popup
      renderTabla(filas);
      summaryDiv.textContent = `Presentes: ${resumen.presentes} | Ausentes: ${resumen.ausentes} | Total: ${resumen.total}`;
      resultSection.style.display = "block";

      // 5. Generar CSV en memoria (reporte opcional)
      reporteCSV = generarCSV(filas);
      downloadBtn.style.display = "block";

      setStatus("success", `¡Listo! ${meta.alumnos.length} alumnos en la planilla. Revisá el reporte.`);

      // Guardar zoomData y mostrar botón de Excel
      lastZoomData = zoomData;
      markExcelBtn.style.display = "block";
    } catch (err) {
      console.error("[ZoomAttendance] Error:", err);
      setStatus("error", "Error inesperado: " + err.message);
    }
  });

  // Botón de descarga separado del procesamiento
  downloadBtn.addEventListener("click", () => {
    if (!reporteCSV) return;
    const blob = new Blob(["\uFEFF" + reporteCSV], {
      type: "text/csv;charset=utf-8;",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "asistencia_procesada.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    setStatus("success", "¡Archivo descargado!");
  });

  // ── Botón: Marcar asistencia en Excel ─────────────────────────────────────
  markExcelBtn.addEventListener("click", async () => {
    if (!lastZoomData) {
      setStatus("warning", "Primero escanea la reunión de Zoom.");
      return;
    }
    if (!lastXlsxMeta) {
      setStatus("warning", "Primero presioná 'Escanear' para leer la planilla.");
      return;
    }

    setStatus("loading", "Marcando asistencia en la planilla...");

    try {
      const { wb, wsName, ws, headerRow, colNombre, colApellido, alumnos } = lastXlsxMeta;
      const range = XLSX.utils.decode_range(ws["!ref"] || "A1");

      // Columna destino: justo a la derecha de la última columna de nombre
      const colDestino = Math.max(colNombre, colApellido) + 1;
      if (range.e.c < colDestino) range.e.c = colDestino;

      const zoomNombres = Object.keys(lastZoomData);
      let presentes = 0, ausentes = 0;

      for (let R = headerRow + 1; R <= range.e.r; ++R) {
        const celdaNombre   = ws[XLSX.utils.encode_cell({ r: R, c: colNombre })];
        const celdaApellido = ws[XLSX.utils.encode_cell({ r: R, c: colApellido })];

        const nombre   = celdaNombre   ? String(celdaNombre.v).trim()   : "";
        const apellido = celdaApellido ? String(celdaApellido.v).trim() : "";
        if (!nombre && !apellido) continue;

        let encontrado = false;
        const alumnoObj = { nombre, apellido, nombreCompleto: (nombre + " " + apellido).trim() };
        for (const zNombre of Object.keys(lastZoomData)) {
          if (coincidenAlumno(alumnoObj, zNombre)) {
            encontrado = true;
            break;
          }
        }

        const estado = encontrado ? "Sí" : "No";
        if (encontrado) presentes++; else ausentes++;

        const styleGreen = {
          fill: { fgColor: { rgb: "C6EFCE" } }, // Fondo verde claro
          font: { color: { rgb: "006100" }, bold: true }, // Texto verde oscuro
          alignment: { horizontal: "center" }
        };

        const styleRed = {
          fill: { fgColor: { rgb: "FFC7CE" } }, // Fondo rojo claro
          font: { color: { rgb: "9C0006" }, bold: true }, // Texto rojo oscuro
          alignment: { horizontal: "center" }
        };

        ws[XLSX.utils.encode_cell({ r: R, c: colDestino })] = {
          t: "s",
          v: estado,
          s: encontrado ? styleGreen : styleRed
        };
      }

      // Encabezado de la columna de asistencia
      const cellHeaderRef = XLSX.utils.encode_cell({ r: headerRow, c: colDestino });
      if (!ws[cellHeaderRef] || !ws[cellHeaderRef].v) {
        ws[cellHeaderRef] = {
          t: "s",
          v: "Asistencia",
          s: { font: { bold: true }, alignment: { horizontal: "center" } }
        };
      }

      ws["!ref"] = XLSX.utils.encode_range(range);

      // Generar descarga
      const wbOut = XLSX.write(wb, { type: "array", bookType: "xlsx" });
      const blob = new Blob([wbOut], {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "asistencia_" + (selectedXlsxFile ? selectedXlsxFile.name : "planilla.xlsx");
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);

      setStatus(
        "success",
        `✓ Excel marcado: ${presentes} presentes, ${ausentes} ausentes. ¡Descargado!`
      );
    } catch (err) {
      console.error("[ZoomAttendance] Error Excel:", err);
      setStatus("error", "Error al procesar Excel: " + err.message);
    }
  });

  // ── Helpers de UI ──────────────────────────────────────────
  function setStatus(type, msg) {
    statusDiv.style.display = "flex";
    statusDiv.textContent = msg;
    statusDiv.className = "status " + type;
  }

  function renderTabla(filas) {
    resultBody.innerHTML = "";
    filas.slice(1).forEach(([nombre, asistencia, camara]) => {
      const tr = document.createElement("tr");
      const presente = asistencia === "Presente";
      const camOn = camara === "Encendida";
      tr.innerHTML = `
        <td class="nombre">${nombre}</td>
        <td class="${presente ? "presente" : "ausente"}">${presente ? "✓" : "✗"} ${asistencia}</td>
        <td class="${camOn ? "cam-on" : "cam-off"}">${camOn ? "🟢" : "🔴"} ${camara}</td>
      `;
      resultBody.appendChild(tr);
    });
  }
});

// ============================================================
// LÓGICA DE SCRAPING (se inyecta en la pestaña de Zoom)
// ============================================================
async function scrapeZoomData() {
  const data = {};

  // ── Helper interno: leer items actualmente renderizados en el DOM ────────
  function scrapeVisibleItems() {
    let items = document.querySelectorAll(
      ".participants-li, [id^='participants-list-']"
    );

    if (!items || items.length === 0) {
      const container =
        document.getElementById("participants-ul") ||
        document.querySelector('[aria-label="Participants list"]') ||
        document.querySelector('[aria-label="Lista de participantes"]');
      if (container) {
        items = container.querySelectorAll(
          ".participants-li, [id^='participants-list-'], [role='application']"
        );
      }
    }

    if (!items || items.length === 0) return false;

    items.forEach((el) => {
      // Nombre desde span de display
      const nameEl = el.querySelector(".participants-item__display-name");
      let name = nameEl ? nameEl.innerText.trim() : "";

      // Fallback: desde aria-label
      const aria = el.getAttribute("aria-label") || "";
      if (!name && aria) {
        name = aria.split(",")[0].replace(/\s*\([^)]*\)/g, "").trim();
      }

      if (!name) return;

      // Estado de cámara
      const ariaLower = aria.toLowerCase();
      const videoOffSvg  = el.querySelector('svg[class*="video-off"]');
      const videoOnSvg   = el.querySelector('svg[class*="video-on"]');
      const videoOffAria = ariaLower.includes("video off") || ariaLower.includes("video apagado");
      const videoOnAria  = ariaLower.includes("video on")  || ariaLower.includes("video encendido");

      let camera_on = true;
      if (videoOffSvg || videoOffAria) camera_on = false;
      else if (videoOnSvg || videoOnAria) camera_on = true;

      // Solo registra la primera aparición (no sobreescribe)
      if (!(name in data)) {
        data[name] = { camera_on };
      }
    });

    return true;
  }

  // ── Helper interno: encontrar contenedor scrolleable ────────────────────
  function findScrollContainer() {
    const candidates = [
      document.getElementById("participants-ul"),
      document.querySelector('[aria-label="Participants list"]'),
      document.querySelector('[aria-label="Lista de participantes"]'),
      document.querySelector(".participants-ul"),
      document.querySelector(".participants-list"),
      document.querySelector(".participant-list__container"),
    ];
    for (const el of candidates) {
      if (el && el.scrollHeight > el.clientHeight) return el;
    }
    // Búsqueda genérica: ancestro scrolleable del primer item
    const firstItem = document.querySelector(".participants-li, [id^='participants-list-']");
    if (firstItem) {
      let parent = firstItem.parentElement;
      while (parent && parent !== document.body) {
        if (parent.scrollHeight > parent.clientHeight + 5) return parent;
        parent = parent.parentElement;
      }
    }
    return null;
  }

  // ── Lectura inicial (posición de scroll = 0) ────────────────────────────
  const foundInitial = scrapeVisibleItems();

  if (!foundInitial) {
    return {
      error: "No se detectó la lista de participantes. Abrí el panel 'Participantes' en Zoom."
    };
  }

  // ── Scroll automático para recorrer toda la lista virtualizada ──────────
  const scrollEl = findScrollContainer();

  if (scrollEl && scrollEl.scrollHeight > scrollEl.clientHeight) {
    const scrollStep  = Math.max(scrollEl.clientHeight * 0.75, 100); // 75% del alto visible
    const maxScroll   = scrollEl.scrollHeight - scrollEl.clientHeight;
    const delayMs     = 120; // ms de espera para que el DOM virtualizado actualice

    let currentScroll = 0;
    while (currentScroll < maxScroll) {
      currentScroll = Math.min(currentScroll + scrollStep, maxScroll);
      scrollEl.scrollTop = currentScroll;
      await new Promise(r => setTimeout(r, delayMs));
      scrapeVisibleItems();
    }

    // Restaurar scroll al inicio para no desorientar al usuario
    scrollEl.scrollTop = 0;
    await new Promise(r => setTimeout(r, 80));
  }

  if (Object.keys(data).length === 0) {
    return {
      error: "No se detectó la lista de participantes. Abrí el panel 'Participantes' en Zoom."
    };
  }

  return data;
}

// ============================================================
// LÓGICA DE PROCESAMIENTO (corre en el contexto del popup)
// ============================================================

/** Lee un File como texto, detectando encoding automáticamente */
function leerArchivo(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => resolve(e.target.result);
    reader.onerror = reject;
    reader.readAsText(file, "UTF-8");
  });
}

/** Parsea un CSV y devuelve array de nombres (sin header) */
function parsearCSV(text) {
  const lineas = text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  if (lineas.length === 0) return [];
  const primeraLinea = lineas[0].toLowerCase().replace(/"/g, "");
  const tieneHeader =
    primeraLinea === "nombre" ||
    primeraLinea === "name" ||
    primeraLinea === "alumno";
  return tieneHeader ? lineas.slice(1) : lineas;
}

/**
 * Normaliza un nombre para comparación:
 * - Quita tildes/diacríticos
 * - Minúsculas, espacios limpios
 * - Remueve sufijos de Zoom: (yo), (anfitrión), (host), etc.
 */
function normalizar(nombre) {
  if (!nombre) return "";
  return nombre
    .normalize("NFD")                          // descomponer caracteres
    .replace(/[\u0300-\u036f]/g, "")           // quitar diacríticos
    .toLowerCase()
    .replace(/\s*\((yo|anfitri[oó]n|coanfitri[oó]n|host|co-host|me|guest|invitado)[^)]*\)/gi, "")
    .replace(/[^a-z0-9]/gi, " ")               // guiones, comas y símbolos -> espacio
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Devuelve los tokens de un nombre normalizado (solo letras y números,
 * descartando tokens que sean puramente numéricos — ej. IDs de Zoom).
 */
function tokenizar(nombreNorm) {
  return nombreNorm
    .split(/\s+/)
    .filter((t) => t.length > 0 && !/^\d+$/.test(t)); // descarta tokens solo numéricos
}

/**
 * Matching flexible entre el nombre del alumno y un nombre de Zoom.
 *
 * Reglas:
 * 1. Match exacto (normalizado) → presente.
 * 2. Subset de tokens: si todos los tokens del nombre más corto están
 *    contenidos en los tokens del nombre más largo → presente.
 */
function coinciden(claveAlumno, claveZoom) {
  if (claveAlumno === claveZoom) return true;

  const tokensAlumno = tokenizar(claveAlumno);
  const tokensZoom   = tokenizar(claveZoom);

  if (tokensAlumno.length === 0 || tokensZoom.length === 0) return false;

  // El conjunto más pequeño debe estar contenido en el más grande
  const [menores, mayores] =
    tokensAlumno.length <= tokensZoom.length
      ? [tokensAlumno, tokensZoom]
      : [tokensZoom, tokensAlumno];

  return menores.every((t) => mayores.includes(t));
}

/** Helper para evaluar coincidencia considerando si alumno es objeto u cadena */
function coincidenAlumno(alumnoObjOrStr, nombreZoom) {
  const nombreStr = typeof alumnoObjOrStr === "string" ? alumnoObjOrStr : alumnoObjOrStr.nombreCompleto;
  const claveAlumno = normalizar(nombreStr);
  const claveZoom = normalizar(nombreZoom);

  if (coinciden(claveAlumno, claveZoom)) return true;

  if (typeof alumnoObjOrStr === "object" && alumnoObjOrStr.nombre && alumnoObjOrStr.apellido) {
    const claveNA = normalizar(alumnoObjOrStr.nombre + " " + alumnoObjOrStr.apellido);
    const claveAN = normalizar(alumnoObjOrStr.apellido + " " + alumnoObjOrStr.nombre);
    if (coinciden(claveNA, claveZoom) || coinciden(claveAN, claveZoom)) return true;
  }

  return false;
}

/**
 * Busca en las primeras filas del worksheet una fila header que contenga
 * columnas con "nombre", "apellido", "alumno", "estudiante" o "participante".
 */
function leerAlumnosDeExcel(ws) {
  if (!ws["!ref"]) return null;
  const range = XLSX.utils.decode_range(ws["!ref"]);
  const MAX_HEADER_SEARCH = Math.min(range.e.r, range.s.r + 14); // buscar en max 15 filas

  let headerRow = -1, colNombre = -1, colApellido = -1;

  for (let R = range.s.r; R <= MAX_HEADER_SEARCH; R++) {
    colNombre = -1;
    colApellido = -1;
    for (let C = range.s.c; C <= range.e.c; C++) {
      const cell = ws[XLSX.utils.encode_cell({ r: R, c: C })];
      if (!cell || cell.v == null) continue;
      const rawVal = String(cell.v).trim();
      const val = normalizar(rawVal);

      // Detectar headers comunes
      if (
        (val.includes("apellido") && val.includes("nombre")) ||
        val.includes("alumno") ||
        val.includes("estudiante") ||
        val.includes("participante")
      ) {
        if (colNombre === -1) colNombre = C;
      } else if (val.includes("nombre")) {
        if (colNombre === -1) colNombre = C;
      } else if (val.includes("apellido")) {
        if (colApellido === -1) colApellido = C;
      }
    }

    if (colNombre >= 0 || colApellido >= 0) {
      if (colNombre === -1 && colApellido >= 0) {
        colNombre = colApellido;
        colApellido = -1;
      }
      headerRow = R;
      break;
    }
  }

  if (headerRow === -1) return null;

  // Extraer lista de alumnos guardando nombre, apellido y nombreCompleto
  const alumnos = [];
  for (let R = headerRow + 1; R <= range.e.r; R++) {
    const celdaN = ws[XLSX.utils.encode_cell({ r: R, c: colNombre })];
    const celdaA = colApellido >= 0 ? ws[XLSX.utils.encode_cell({ r: R, c: colApellido })] : null;
    const nombre   = celdaN ? String(celdaN.v).trim() : "";
    const apellido = celdaA ? String(celdaA.v).trim() : "";
    if (!nombre && !apellido) continue;
    alumnos.push({ nombre, apellido, nombreCompleto: (nombre + " " + apellido).trim() });
  }

  return { headerRow, colNombre, colApellido: colApellido >= 0 ? colApellido : colNombre, alumnos };
}




/** Compara la lista de alumnos contra los datos de Zoom y genera el reporte */
function procesarAsistencia(alumnos, zoomData) {
  const zoomEntries = Object.entries(zoomData).map(([nombre, info]) => ({
    nombreOriginal: nombre,
    info,
  }));

  const filas = [["Nombre", "Asistencia", "Cámara"]];
  let presentes = 0, ausentes = 0;

  for (const alumno of alumnos) {
    const nombreStr = typeof alumno === "string" ? alumno.replace(/^"|"$/g, "").trim() : alumno.nombreCompleto;
    if (!nombreStr) continue;

    let match = null;
    for (const entry of zoomEntries) {
      if (coincidenAlumno(alumno, entry.nombreOriginal)) {
        match = entry;
        break;
      }
    }

    if (match) {
      presentes++;
      filas.push([nombreStr, "Presente", match.info.camera_on ? "Encendida" : "Apagada"]);
    } else {
      ausentes++;
      filas.push([nombreStr, "Ausente", "Apagada"]);
    }
  }

  return {
    filas,
    resumen: { presentes, ausentes, total: presentes + ausentes },
  };
}


/** Convierte un array de filas en un string CSV válido */
function generarCSV(filas) {
  return filas
    .map((fila) =>
      fila.map((celda) => `"${celda.replace(/"/g, '""')}"`).join(","),
    )
    .join("\r\n");
}
