document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("login-form");
  const feedback = document.getElementById("login-feedback");
  const email = document.getElementById("email");
  const password = document.getElementById("password");

  document.querySelectorAll("[data-demo]").forEach((button) => {
    button.addEventListener("click", () => {
      const account = button.dataset.demo;
      email.value = account === "admin"
        ? "admin@ecocity.local"
        : "cidadao@ecocity.local";
      password.value = account === "admin" ? "Admin123!" : "Cidadao123!";
      feedback.textContent = "Conta de demonstração preenchida. Clique em Entrar.";
      feedback.className = "feedback feedback-info";
    });
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const submit = form.querySelector("button[type='submit']");
    submit.disabled = true;
    submit.textContent = "Entrando...";
    feedback.textContent = "";
    try {
      const result = await EcoCity.apiRequest("/api/v1/auth/login", {
        method: "POST",
        body: { email: email.value.trim(), password: password.value },
      });
      EcoCity.saveSession(result);
      window.location.href = result.user.role === "admin" ? "painel.html" : "relatos.html";
    } catch (error) {
      feedback.textContent = error.message;
      feedback.className = "feedback feedback-error";
    } finally {
      submit.disabled = false;
      submit.textContent = "Entrar";
    }
  });
});
