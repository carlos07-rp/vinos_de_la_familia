const STORAGE_KEY = "vintalytics-lotes";
let lots = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");

const titles = {
  dashboard: "Dashboard ejecutivo",
  lotes: "Lotes",
  laboratorio: "Laboratorio",
  inteligencia: "Inteligencia",
  catas: "Catas y observaciones",
  almacenamiento: "Almacenamiento",
  seguimiento: "Seguimiento",
  datos: "Datos y modelos",
  reportes: "Reportes"
};

const escapeHtml = (value = "") => String(value)
  .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");

function saveLots() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(lots));
}

function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2400);
}

function inProcess() {
  return lots.filter(l => ["Elaboración", "Fermentación"].includes(l.etapa)).length;
}

function inStorage() {
  return lots.filter(l => ["Crianza", "Almacenamiento"].includes(l.etapa)).length;
}

function renderDashboard() {
  const finalizados = lots.filter(l => l.etapa === "Finalizado").length;
  const stageCounts = ["Elaboración", "Fermentación", "Crianza", "Almacenamiento", "Finalizado"]
    .map(stage => ({ stage, count: lots.filter(l => l.etapa === stage).length }));
  const max = Math.max(1, ...stageCounts.map(x => x.count));

  return `
    <div class="kpi-grid">
      ${kpi("Lotes registrados", lots.length, "Base de datos propia")}
      ${kpi("En proceso", inProcess(), "Elaboración y fermentación")}
      ${kpi("Crianza", inStorage(), "Crianza y almacenamiento")}
      ${kpi("Finalizados", finalizados, "Lotes completados")}
      ${kpi("Análisis registrados", 0, "Sin registros")}
      ${kpi("Último análisis", "—", "Sin registros")}
    </div>
    <div class="panel-grid">
      <div class="panel">
        <h2>Distribución por etapa</h2>
        ${lots.length ? `
          <div class="chart-bars">
            ${stageCounts.map(x => `<div class="bar" style="height:${Math.max(8, x.count / max * 160)}px"><span>${x.stage}</span></div>`).join("")}
          </div>` : emptyState("Sin datos de lotes", "Registre el primer lote para comenzar")}
      </div>
      <div class="panel">
        <h2>Actividad reciente</h2>
        ${lots.length ? lots.slice(-5).reverse().map(l => `
          <div class="activity-row"><span class="activity-dot"></span><div><b>${escapeHtml(l.nombre)}</b><br><small>${escapeHtml(l.etapa)} · ${escapeHtml(l.fecha || "Fecha no registrada")}</small></div></div>
        `).join("") : emptyState("Sin actividad", "Las acciones aparecerán aquí")}
      </div>
      <div class="panel panel-wide">
        <h2>Distribución por variedad</h2>
        ${lots.length ? `<div class="table-wrap"><table><thead><tr><th>Variedad</th><th>Cantidad</th></tr></thead><tbody>${varietyRows()}</tbody></table></div>` : emptyState("Sin variedades registradas", "No existen registros reales")}
      </div>
    </div>`;
}

function kpi(label, value, note) {
  return `<div class="kpi"><span class="kpi-label">${label}</span><strong class="kpi-value">${value}</strong><span class="kpi-note">${note}</span></div>`;
}

function emptyState(title, text) {
  return `<div class="empty"><div><strong>${title}</strong>${text}</div></div>`;
}

function varietyRows() {
  const counts = {};
  lots.forEach(l => { const key = l.variedad || "Sin especificar"; counts[key] = (counts[key] || 0) + 1; });
  return Object.entries(counts).map(([name, count]) => `<tr><td>${escapeHtml(name)}</td><td>${count}</td></tr>`).join("");
}

function renderLots(search = "", variety = "Todas", stage = "Todas") {
  let view = lots.filter(l => {
    const textMatch = !search || Object.values(l).join(" ").toLowerCase().includes(search.toLowerCase());
    return textMatch && (variety === "Todas" || l.variedad === variety) && (stage === "Todas" || l.etapa === stage);
  });
  const varieties = ["Todas", ...new Set(lots.map(l => l.variedad).filter(Boolean))];
  const stages = ["Todas", "Elaboración", "Fermentación", "Crianza", "Almacenamiento", "Finalizado"];

  return `
    <div class="section-head"><h2>Listado de lotes</h2><button class="button primary" id="newLot">+ Nuevo lote</button></div>
    <div class="filters">
      <input id="lotSearch" value="${escapeHtml(search)}" placeholder="Buscar lote, código o responsable">
      <select id="lotVariety">${varieties.map(v => `<option ${v === variety ? "selected" : ""}>${escapeHtml(v)}</option>`).join("")}</select>
      <select id="lotStage">${stages.map(s => `<option ${s === stage ? "selected" : ""}>${escapeHtml(s)}</option>`).join("")}</select>
      <button class="button secondary" id="clearFilters">Limpiar</button>
    </div>
    ${view.length ? `
      <div class="table-wrap"><table><thead><tr><th>Código</th><th>Nombre</th><th>Variedad</th><th>Añada</th><th>Tipo</th><th>Etapa</th><th>Responsable</th><th></th></tr></thead>
      <tbody>${view.map(l => `<tr>
        <td>${escapeHtml(l.codigo)}</td><td><b>${escapeHtml(l.nombre)}</b></td><td>${escapeHtml(l.variedad || "—")}</td>
        <td>${escapeHtml(l.anada || "—")}</td><td>${escapeHtml(l.tipo)}</td>
        <td><span class="status activo">${escapeHtml(l.etapa)}</span></td><td>${escapeHtml(l.responsable || "—")}</td>
        <td><button class="button secondary delete-lot" data-id="${l.id}" title="Eliminar lote">Eliminar</button></td>
      </tr>`).join("")}</tbody></table></div>` : emptyState("No hay lotes que mostrar", "Modifique los filtros o registre un lote")}
  `;
}

function placeholderPage(title, text) {
  return `<div class="panel"><h2>${title}</h2>${emptyState("Módulo listo para datos reales", text)}</div>`;
}

function renderPage(page) {
  document.getElementById("pageTitle").textContent = titles[page];
  const content = document.getElementById("content");
  if (page === "dashboard") content.innerHTML = renderDashboard();
  else if (page === "lotes") content.innerHTML = renderLots();
  else if (page === "laboratorio") content.innerHTML = placeholderPage("Registro de laboratorio", "Seleccione un lote y registre análisis históricos.");
  else if (page === "inteligencia") content.innerHTML = placeholderPage("Inteligencia analítica", "Entrene modelos o compare perfiles cuando existan datos disponibles.");
  else if (page === "catas") content.innerHTML = placeholderPage("Catas y observaciones", "Agregue evaluaciones sensoriales vinculadas a un lote.");
  else if (page === "almacenamiento") content.innerHTML = placeholderPage("Almacenamiento", "Registre recipientes, temperaturas y condiciones.");
  else if (page === "seguimiento") content.innerHTML = placeholderPage("Seguimiento", "La línea de tiempo mostrará eventos reales del lote.");
  else if (page === "datos") content.innerHTML = placeholderPage("Datos y modelos", "Cargue un CSV académico y separelo claramente de los datos propios.");
  else if (page === "reportes") content.innerHTML = placeholderPage("Reportes", "El expediente estará disponible cuando existan registros.");
}

document.getElementById("navigation").addEventListener("click", event => {
  const button = event.target.closest(".nav-item");
  if (!button) return;
  document.querySelectorAll(".nav-item").forEach(item => item.classList.remove("active"));
  button.classList.add("active");
  renderPage(button.dataset.page);
  document.querySelector(".sidebar").classList.remove("open");
});

document.getElementById("menuButton").addEventListener("click", () => {
  document.querySelector(".sidebar").classList.toggle("open");
});

const modal = document.getElementById("modalBackdrop");
document.getElementById("content").addEventListener("click", event => {
  if (event.target.id === "newLot") modal.hidden = false;
  if (event.target.id === "clearFilters") renderPage("lotes");
  if (event.target.classList.contains("delete-lot")) {
    if (confirm("¿Eliminar este lote y sus datos asociados?")) {
      lots = lots.filter(l => l.id !== Number(event.target.dataset.id));
      saveLots();
      renderPage("lotes");
      showToast("Lote eliminado");
    }
  }
});

document.getElementById("content").addEventListener("input", event => {
  if (["lotSearch", "lotVariety", "lotStage"].includes(event.target.id)) {
    const search = document.getElementById("lotSearch")?.value || "";
    const variety = document.getElementById("lotVariety")?.value || "Todas";
    const stage = document.getElementById("lotStage")?.value || "Todas";
    document.getElementById("content").queryContent = null;
    document.querySelector(".content").innerHTML = renderLots(search, variety, stage);
  }
});

function closeModal() { modal.hidden = true; document.getElementById("loteForm").reset(); }
document.getElementById("closeModal").addEventListener("click", closeModal);
document.getElementById("cancelModal").addEventListener("click", closeModal);

document.getElementById("loteForm").addEventListener("submit", event => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.target));
  lots.push({ id: Date.now(), ...data });
  saveLots();
  closeModal();
  renderPage("lotes");
  showToast("Lote guardado correctamente");
});

renderPage("dashboard");
