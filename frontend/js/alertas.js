document.addEventListener("DOMContentLoaded", async () => {
  const mapElement = document.getElementById("alert-map");
  if (!window.L) {
    document.getElementById("map-message").textContent = "Não foi possível carregar o mapa. Verifique sua conexão com a internet.";
    return;
  }
  const map = L.map(mapElement).setView([-23.605, -46.666], 14);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map);

  try {
    const data = await EcoCity.apiRequest("/api/v1/alertas");
    const alerts = data.alertas || [];
    document.getElementById("city-status").textContent = data.status_cidade;
    document.getElementById("alerts-updated").textContent = `Atualizado em ${new Date(data.atualizado_em).toLocaleString("pt-BR")}`;
    document.getElementById("alerts-source").textContent = data.origem;
    document.getElementById("alert-total").textContent = alerts.length;
    document.getElementById("alert-high").textContent = alerts.filter((alert) => alert.nivel === "alto").length;
    document.getElementById("alert-medium").textContent = alerts.filter((alert) => alert.nivel === "medio").length;
    document.getElementById("alert-low").textContent = alerts.filter((alert) => alert.nivel === "baixo").length;
    alerts.forEach((alert) => {
      const color = alert.nivel === "alto" ? "#b24531" : alert.nivel === "medio" ? "#d69364" : "#548b64";
      L.circleMarker([alert.lat, alert.lng], { radius: 10, color, fillColor: color, fillOpacity: 0.78, weight: 2 })
        .addTo(map)
        .bindPopup(`<strong>${escapeHtml(alert.titulo)}</strong><br>${escapeHtml(alert.local)}<br>Nível indicado: ${escapeHtml(alert.nivel)}<br>Sensor demonstrativo: ${alert.agua_cm} cm<br><small>${escapeHtml(alert.descricao)}</small>`);
    });
    if (alerts.length) map.fitBounds(alerts.map((alert) => [alert.lat, alert.lng]), { padding: [30, 30] });
    renderAlertList(alerts);
  } catch (error) {
    document.getElementById("map-message").textContent = `${error.message} O mapa precisa que a API esteja ligada.`;
  }

  function renderAlertList(alerts) {
    const list = document.getElementById("alert-list");
    list.replaceChildren();
    alerts.forEach((alert) => {
      const item = document.createElement("article");
      item.className = "alert-list-item";
      const heading = document.createElement("div");
      heading.className = "alert-list-heading";
      const title = document.createElement("h3");
      title.textContent = alert.titulo;
      const level = document.createElement("span");
      level.className = `risk-pill risk-${alert.nivel === "alto" ? "high" : alert.nivel === "medio" ? "medium" : "low"}`;
      level.textContent = alert.nivel.toUpperCase();
      heading.append(title, level);
      const location = document.createElement("p");
      location.textContent = alert.local;
      const description = document.createElement("p");
      description.className = "muted-text";
      description.textContent = alert.descricao;
      item.append(heading, location, description);
      item.addEventListener("click", () => map.setView([alert.lat, alert.lng], 16));
      list.append(item);
    });
  }
});

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}
