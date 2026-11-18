document.addEventListener("DOMContentLoaded", async () => {
  const user = await EcoCity.requireAuth(["user", "admin"]);
  if (!user) return;

  const form = document.getElementById("form-relato");
  const submit = document.getElementById("btn-enviar");
  const feedback = document.getElementById("form-feedback");
  const resultPanel = document.getElementById("triage-result");
  const imageInput = document.getElementById("imagem");
  const preview = document.getElementById("image-preview");
  const userName = document.getElementById("reporter-name");

  imageInput.addEventListener("change", () => {
    preview.replaceChildren();
    const file = imageInput.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      feedback.textContent = "Selecione um arquivo de imagem.";
      feedback.className = "feedback feedback-error";
      imageInput.value = "";
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      feedback.textContent = "A imagem deve ter no máximo 5 MB.";
      feedback.className = "feedback feedback-error";
      imageInput.value = "";
      return;
    }
    const image = document.createElement("img");
    image.src = URL.createObjectURL(file);
    image.alt = "Pré-visualização da imagem selecionada";
    preview.append(image);
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    submit.disabled = true;
    submit.textContent = "Analisando ocorrência...";
    feedback.textContent = "Enviando relato e aguardando a triagem.";
    feedback.className = "feedback feedback-info";
    resultPanel.hidden = true;

    const formData = new FormData();
    formData.append("localizacao", document.getElementById("localizacao").value.trim());
    formData.append("descricao", document.getElementById("descricao").value.trim());
    formData.append("nivel_sensor_agua_cm", document.getElementById("nivel-agua").value || "0");
    if (imageInput.files?.[0]) formData.append("imagem", imageInput.files[0]);

    try {
      const session = EcoCity.getSession();
      const response = await fetch("http://127.0.0.1:8000/api/v1/analisar-ocorrencia", {
        method: "POST",
        headers: { Authorization: `Bearer ${session.access_token}` },
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Não foi possível enviar o relato.");
      showTriage(data);
      form.reset();
      preview.replaceChildren();
      feedback.textContent = "Ocorrência enviada. A classificação abaixo foi gerada pela triagem do sistema.";
      feedback.className = "feedback feedback-success";
    } catch (error) {
      feedback.textContent = `${error.message} Verifique se a API está em execução na porta 8000.`;
      feedback.className = "feedback feedback-error";
    } finally {
      submit.disabled = false;
      submit.textContent = "Enviar Ocorrência";
    }
  });

  function showTriage(data) {
    const result = data.triagem;
    document.getElementById("result-category").textContent = result.categoria;
    document.getElementById("result-priority").textContent = result.prioridade_atendimento;
    document.getElementById("result-risk").textContent = `${result.nivel_risco}/5`;
    document.getElementById("result-reason").textContent = result.justificativa_ia;
    document.getElementById("result-model").textContent = `${result.modelo_utilizado} · ${result.tempo_processamento_ms} ms`;
    document.getElementById("result-id").textContent = `Protocolo #${data.relato.id}`;
    resultPanel.hidden = false;
    resultPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
});
