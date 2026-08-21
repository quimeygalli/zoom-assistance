// background.js
// Cuando el usuario hace click en el ícono de la extensión,
// abre popup.html como una pestaña completa (para que el selector
// de archivos del sistema operativo funcione correctamente).
chrome.action.onClicked.addListener(() => {
  chrome.tabs.create({ url: chrome.runtime.getURL("popup.html") });
});
