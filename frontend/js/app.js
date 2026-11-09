const URL_API = "http://localhost:3000/api/usuarios";
const API = "http://localhost:3000/api";

const formUsuarios = document.getElementById("form-relato");
const formAgendamento = document.getElementById("form-agendamento");

const usuarioId = document.getElementById("relato-id");
const agendamentoId = document.getElementById("agendamento-id");

const inputNome = document.getElementById("nome");
const inputCpf = document.getElementById("cpf");
const inputEmail = document.getElementById("email");
const inputLocalRelato = document.getElementById("local-relato");
const inputRelato = document.getElementById("relato");

const inputEmailAgend = document.getElementById("emailAgend");
const inputNomePac = document.getElementById("nomePac");
const inputData = document.getElementById("data");
const inputHorario = document.getElementById("horario");

let pacienteId = null;

function limparFormulario() {
  formUsuarios.reset();
  usuarioId.value = "";
}

formUsuarios.addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = usuarioId.value;
  const payload = { nome: inputNome.value, cpf: inputCpf.value, email: inputEmail.value, localRelato: inputLocalRelato.value, relato: inputRelato.value };
  const config = {
    method: "POST",
    headers: { "content-Type": "application/json" },
    body: JSON.stringify(payload),
  };

  const urlFinal = id ? `${URL_API}/${id}` : URL_API;

  try {
    const resposta = await fetch(urlFinal, config);
    if (!resposta.ok) {
      const erroApi = await resposta.json();
      alert(`${resposta.status} - ${erroApi.mensagem}`);
      return;
    }
    limparFormulario();
  } catch (erro) {
    console.error("Erro na requisição externa", erro);
  }
});

/* formAgendamento.addEventListener("submit", async (e) => {
  e.preventDefault();

  if (!pacienteId) {
    alert("Busque o paciente pelo email primeiro.");
    return;
  }

  const data = inputData.value;
  const horario = inputHorario.value;

  if (!data || !horario) {
    alert("Selecione a data e o horário.");
    return;
  }

  const payload = {
    data,
    horario,
  };

  try {
    const resposta = await fetch(`${API}/agendamentos/${pacienteId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const dados = await resposta.json();

    if (!resposta.ok) {
      alert(dados.erro);
      return;
    }

    alert("Agendamento realizado com sucesso!");
    formAgendamento.reset();
    pacienteId = null;
    inputNomePac.value = "";
    inputHorario.innerHTML = '<option value="">Selecione uma data</option>';
  } catch (erro) {
    console.error("Erro ao criar agendamento:", erro);
  }
}); */

//CRUD
function preencherForm(id, nome, cpf, email, localRelato, relato) {
  usuarioId.value = id;
  inputNome.value = nome;
  inputCpf.value = cpf;
  inputEmail.value = email;
  inputLocalRelato.value = localRelato;
  inputRelato.value = relato;
}

const dataInput = document.getElementById("data");
const selectHorario = document.getElementById("horario");

inputData.addEventListener("change", async () => {
  if (!inputData.value) return;

  const dataEscolhida = new Date(inputData.value + "T00:00:00");
  const diaSemana = dataEscolhida.getDay();

  if (diaSemana === 0 || diaSemana === 6) {
    alert("Escolha um dia útil.");
    inputData.value = "";
    inputHorario.innerHTML = '<option value="">Selecione uma data</option>';
    return;
  }

  try {
    const response = await fetch(`${API}/agendamentos/disponiveis?data=${inputData.value}`);
    const dados = await response.json();

    if (!response.ok) {
      alert(dados.erro || "Erro ao buscar horários");
      return;
    }

    inputHorario.innerHTML = '<option value="">Selecione um horário</option>';

    if (dados.horarios.length === 0) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "Sem horários disponíveis";
      inputHorario.appendChild(option);
      return;
    }

    dados.horarios.forEach((hora) => {
      const option = document.createElement("option");
      option.value = hora;
      option.textContent = hora;
      inputHorario.appendChild(option);
    });
  } catch (erro) {
    console.error("Erro ao buscar horários:", erro);
  }
});

async function buscarPacientePorEmail() {
  const email = inputEmailAgend.value.trim();

  if (!email) return;

  const resposta = await fetch(`${API}/pacientes/email/${encodeURIComponent(email)}`);
  const dados = await resposta.json();

  if (!resposta.ok) {
    alert(dados.erro);
    pacienteId = null;
    inputNomePac.value = "";
    return;
  }

  pacienteId = dados.codPac;
  inputNomePac.value = dados.nome;
}

/* inputEmailAgend.addEventListener("blur", buscarPacientePorEmail);

inputEmailAgend.addEventListener("input", () => {
  pacienteId = null;
  inputNomePac.value = "";
});
 */
