(function () {
  const API_BASE = "http://127.0.0.1:8000";
  const SESSION_KEY = "ecocity_session";

  function getSession() {
    try { return JSON.parse(localStorage.getItem(SESSION_KEY) || "null"); }
    catch { return null; }
  }

  function saveSession(data) {
    localStorage.setItem(SESSION_KEY, JSON.stringify(data));
  }

  function clearSession() {
    localStorage.removeItem(SESSION_KEY);
  }

  async function apiRequest(path, options = {}) {
    const session = getSession();
    const headers = new Headers(options.headers || {});
    if (session?.access_token && !headers.has("Authorization")) {
      headers.set("Authorization", `Bearer ${session.access_token}`);
    }
    let body = options.body;
    if (body && !(body instanceof FormData) && typeof body !== "string") {
      headers.set("Content-Type", "application/json");
      body = JSON.stringify(body);
    }
    const response = await fetch(`${API_BASE}${path}`, { ...options, headers, body });
    const contentType = response.headers.get("content-type") || "";
    const data = contentType.includes("application/json") ? await response.json() : null;
    if (!response.ok) {
      if (response.status === 401 && path !== "/api/v1/auth/login") clearSession();
      throw new Error(data?.detail || data?.message || `Falha na API (${response.status}).`);
    }
    return data;
  }

  async function requireAuth(roles = []) {
    const session = getSession();
    if (!session?.access_token) {
      window.location.href = "login.html";
      return null;
    }
    try {
      const user = await apiRequest("/api/v1/auth/me");
      saveSession({ ...session, user });
      if (roles.length && !roles.includes(user.role)) {
        window.location.href = user.role === "admin" ? "painel.html" : "relatos.html";
        return null;
      }
      updateHeader(user);
      return user;
    } catch {
      clearSession();
      window.location.href = "login.html";
      return null;
    }
  }

  function updateHeader(user = getSession()?.user) {
    document.querySelectorAll("[data-link-report]").forEach((link) => {
      link.href = user ? "relatos.html" : "login.html";
      if (!user && link.dataset.guestLabel) link.textContent = link.dataset.guestLabel;
    });
    document.querySelectorAll("[data-link-manager]").forEach((link) => {
      link.hidden = user?.role !== "admin";
    });
    document.querySelectorAll("[data-login-link]").forEach((link) => {
      link.hidden = Boolean(user);
    });
    document.querySelectorAll("[data-user-area]").forEach((area) => {
      area.hidden = !user;
    });
    document.querySelectorAll("[data-logout]").forEach((button) => {
      button.hidden = !user;
    });
    document.querySelectorAll("[data-user-name]").forEach((node) => {
      node.textContent = user ? user.nome : "";
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    updateHeader();
    document.querySelectorAll("[data-logout]").forEach((button) => {
      button.addEventListener("click", async () => {
        try { await apiRequest("/api/v1/auth/logout", { method: "POST" }); }
        catch {}
        clearSession();
        window.location.href = "index.html";
      });
    });
  });

  window.EcoCity = { API_BASE, getSession, saveSession, clearSession, apiRequest, requireAuth, updateHeader };
})();
