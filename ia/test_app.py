from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def login(email="cidadao@ecocity.local", password="Cidadao123!"):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_e_perfil():
    headers = login()
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["role"] == "user"


def test_login_invalido():
    response = client.post("/api/v1/auth/login", json={"email": "naoexiste@example.com", "password": "senha"})
    assert response.status_code == 401


def test_triagem_e_persistencia(monkeypatch):
    monkeypatch.setattr("app.processar_com_llm_local", lambda descricao, nivel: None)
    headers = login()
    response = client.post(
        "/api/v1/analisar-ocorrencia",
        headers=headers,
        data={
            "localizacao": "Rua de teste, Moema",
            "descricao": "Rua alagada com água subindo rapidamente",
            "nivel_sensor_agua_cm": "65",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["triagem"]["nivel_risco"] == 5
    assert "Alagamento" in data["triagem"]["categoria"]
    assert data["relato"]["id"]


def test_envio_imagem(monkeypatch):
    monkeypatch.setattr("app.processar_com_llm_local", lambda descricao, nivel: None)
    headers = login()
    response = client.post(
        "/api/v1/analisar-ocorrencia",
        headers=headers,
        data={"localizacao": "Rua de teste, Moema", "descricao": "Bueiro entupido com folhas e resíduos"},
        files={"imagem": ("foto.png", b"fake-png-content", "image/png")},
    )
    assert response.status_code == 200
    assert response.json()["relato"]["imagem_url"].startswith("/uploads/")


def test_permissoes_e_crud_admin(monkeypatch):
    monkeypatch.setattr("app.processar_com_llm_local", lambda descricao, nivel: None)
    user_headers = login()
    assert client.get("/api/v1/relatos", headers=user_headers).status_code == 403

    admin_headers = login("admin@ecocity.local", "Admin123!")
    response = client.get("/api/v1/relatos", headers=admin_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    report_id = response.json()[0]["id"]

    edited = client.patch(
        f"/api/v1/relatos/{report_id}",
        headers=admin_headers,
        json={
            "status": "Em atendimento",
            "localizacao": "Local atualizado pelo teste",
            "descricao": "Rua alagada com água invadindo a calçada",
        },
    )
    assert edited.status_code == 200
    assert edited.json()["status"] == "Em atendimento"
    assert edited.json()["nivel_risco"] >= 4

    deleted = client.delete(f"/api/v1/relatos/{report_id}", headers=admin_headers)
    assert deleted.status_code == 200


def test_cidadao_visualiza_apenas_os_proprios_relatorios():
    headers = login()
    response = client.get("/api/v1/relatos/meus", headers=headers)
    assert response.status_code == 200
    assert all(item["usuario"]["email"] == "cidadao@ecocity.local" for item in response.json())


def test_alertas_publicos():
    response = client.get("/api/v1/alertas")
    assert response.status_code == 200
    assert len(response.json()["alertas"]) >= 1


def test_telemetria_sensor_com_chave():
    response = client.post(
        "/api/v1/telemetria",
        headers={"X-Sensor-Token": "ecocity-iot-demo-key"},
        json={
            "sensor_id": "ESP32-TEST-01",
            "localizacao": "Bueiro de teste, Moema",
            "descricao": "Alerta automático de enchente detectado pelo sensor.",
            "nivel_sensor_agua_cm": 60,
        },
    )
    assert response.status_code == 200
    assert response.json()["relato"]["usuario"]["nome"].startswith("Sensor IoT")
    assert response.json()["triagem"]["nivel_risco"] == 5


def test_telemetria_sensor_rejeita_chave_invalida():
    response = client.post(
        "/api/v1/telemetria",
        headers={"X-Sensor-Token": "chave-incorreta"},
        json={"sensor_id": "ESP32-TEST-02", "nivel_sensor_agua_cm": 60},
    )
    assert response.status_code == 401
