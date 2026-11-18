document.addEventListener("DOMContentLoaded", async () => {
  const user = await EcoCity.requireAuth(["admin"]);
  if (!user) return;

  const tbody = document.getElementById("reports-body");
  const search = document.getElementById("search-reports");
  const priorityFilter = document.getElementById("priority-filter");
  const statusFilter = document.getElementById("status-filter");
  const modal = document.getElementById("edit-dialog");
  const editForm = document.getElementById("edit-form");
  const feedback = document.getElementById("manager-feedback");
  let reports = [];

  async function loadReports() {
    tbody.innerHTML = '<tr><td colspan="8" class="table-message">Carregando relatos...</td></tr>';
    try {
      reports = await EcoCity.apiRequest("/api/v1/relatos");
      renderReports();
      updateMetrics();
    } catch (error) {
      tbody.innerHTML = `<tr><td colspan="8" class="table-message">${escapeHtml(error.message)}</td></tr>`;
    }
  }

  function updateMetrics() {
    document.getElementById("metric-total").textContent = reports.length;
    document.getElementById("metric-high").textContent = reports.filter((item) => item.nivel_risco >= 4).length;
    document.getElementById("metric-open").textContent = reports.filter((item) => !["Resolvido", "Arquivado"].includes(item.status)).length;
    document.getElementById("metric-done").textContent = reports.filter((item) => item.status === "Resolvido").length;
  }

  function renderReports() {
    const term = search.value.trim().toLocaleLowerCase("pt-BR");
    const priority = priorityFilter.value;
    const status = statusFilter.value;
    const filtered = reports.filter((item) => {
      const content = [item.id, item.usuario.nome, item.usuario.email, item.localizacao, item.descricao, item.categoria].join(" ").toLocaleLowerCase("pt-BR");
      return (!term || content.includes(term)) && (!priority || item.prioridade_atendimento === priority) && (!status || item.status === status);
    });
    tbody.replaceChildren();
    if (!filtered.length) {
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = 8;
      cell.className = "table-message";
      cell.textContent = "Nenhum relato corresponde aos filtros.";
      row.append(cell);
      tbody.append(row);
      return;
    }
    filtered.forEach((item) => {
      const row = document.createElement("tr");
      appendCell(row, `#${item.id}`);
      appendCell(row, formatDate(item.timestamp));
      appendCell(row, item.usuario.nome);
      appendCell(row, item.localizacao);
      appendCell(row, item.categoria);
      const riskCell = document.createElement("td");
      const risk = document.createElement("span");
      risk.className = `risk-pill risk-${item.nivel_risco >= 4 ? "high" : item.nivel_risco >= 3 ? "medium" : "low"}`;
      risk.textContent = `${item.nivel_risco}/5 · ${item.prioridade_atendimento}`;
      riskCell.append(risk);
      row.append(riskCell);
      const statusCell = document.createElement("td");
      statusCell.textContent = item.status;
      row.append(statusCell);
      const actionCell = document.createElement("td");
      actionCell.className = "table-actions";
      if (item.imagem_url) {
        const imageLink = document.createElement("a");
        imageLink.href = `${EcoCity.API_BASE}${item.imagem_url}`;
        imageLink.target = "_blank";
        imageLink.rel = "noopener";
        imageLink.textContent = "Imagem";
        imageLink.className = "text-action";
        actionCell.append(imageLink);
      }
      const edit = document.createElement("button");
      edit.type = "button";
      edit.className = "small-button";
      edit.textContent = "Editar";
      edit.addEventListener("click", () => openEdit(item));
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "small-button small-button-danger";
      remove.textContent = "Excluir";
      remove.addEventListener("click", () => deleteItem(item));
      actionCell.append(edit, remove);
      row.append(actionCell);
      tbody.append(row);
    });
  }

  function appendCell(row, text) {
    const cell = document.createElement("td");
    cell.textContent = text ?? "—";
    row.append(cell);
  }

  function openEdit(item) {
    document.getElementById("edit-id").value = item.id;
    document.getElementById("edit-location").value = item.localizacao;
    document.getElementById("edit-description").value = item.descricao;
    document.getElementById("edit-status").value = item.status;
    modal.showModal();
  }

  async function deleteItem(item) {
    if (!window.confirm(`Excluir permanentemente o relato #${item.id}?`)) return;
    try {
      await EcoCity.apiRequest(`/api/v1/relatos/${item.id}`, { method: "DELETE" });
      feedback.textContent = `Relato #${item.id} excluído.`;
      feedback.className = "feedback feedback-success";
      await loadReports();
    } catch (error) {
      feedback.textContent = error.message;
      feedback.className = "feedback feedback-error";
    }
  }

  editForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const id = document.getElementById("edit-id").value;
    const button = editForm.querySelector("button[type='submit']");
    button.disabled = true;
    try {
      await EcoCity.apiRequest(`/api/v1/relatos/${id}`, {
        method: "PATCH",
        body: {
          localizacao: document.getElementById("edit-location").value.trim(),
          descricao: document.getElementById("edit-description").value.trim(),
          status: document.getElementById("edit-status").value,
        },
      });
      modal.close();
      feedback.textContent = `Relato #${id} atualizado.`;
      feedback.className = "feedback feedback-success";
      await loadReports();
    } catch (error) {
      feedback.textContent = error.message;
      feedback.className = "feedback feedback-error";
    } finally {
      button.disabled = false;
    }
  });

  document.getElementById("close-edit").addEventListener("click", () => modal.close());
  [search, priorityFilter, statusFilter].forEach((control) => control.addEventListener("input", renderReports));
  document.getElementById("refresh-reports").addEventListener("click", loadReports);
  await loadReports();
});

function formatDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString("pt-BR");
}
function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}
