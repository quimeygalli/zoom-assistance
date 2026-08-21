// file-picker.js
// Se ejecuta en la ventana auxiliar de selección de archivos.
// Guarda el archivo en chrome.storage.local y notifica al popup.

const fileInput = document.getElementById("fileInput");
const statusEl  = document.getElementById("status");

fileInput.addEventListener("change", async function () {
  const file = this.files[0];
  if (!file) return;

  statusEl.className = "";
  statusEl.textContent = "Cargando " + file.name + "...";

  try {
    const arrayBuffer = await file.arrayBuffer();
    const base64 = await bufferToBase64(arrayBuffer);

    await chrome.storage.local.set({
      pickedXlsxName: file.name,
      pickedXlsxBase64: base64,
    });

    statusEl.className = "success";
    statusEl.textContent = "✔ ¡Archivo cargado! Cerrando...";

    try {
      chrome.runtime.sendMessage({ type: "xlsx-ready", name: file.name });
    } catch (e) {
      // Si el popup estaba cerrado, ignore
    }

    setTimeout(() => {
      window.close();
    }, 400);
  } catch (err) {
    statusEl.className = "error";
    statusEl.textContent = "Error: " + err.message;
  }
});

function bufferToBase64(buffer) {
  return new Promise((resolve, reject) => {
    const blob = new Blob([buffer]);
    const reader = new FileReader();
    reader.onload = (e) => {
      const dataUrl = e.target.result;
      const base64 = dataUrl.split(",")[1];
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}
