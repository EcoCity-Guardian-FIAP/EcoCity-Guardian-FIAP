# EcoCity Guardian

Plataforma web para prevenção de enchentes e zeladoria urbana colaborativa.

## Execução e configuração

### 1. Iniciar o backend (API)

Pré-requisito: Python 3.10 ou superior.

No terminal, entre na pasta `ia`:

```bash
cd ia
python -m venv .venv
```

Ainda na pasta `ia`, ative o ambiente virtual:

**Windows (PowerShell):**

```powershell
.\.venv\Scripts\Activate.ps1
```

**Windows (Prompt de Comando):**

```bat
.venv\Scripts\activate.bat
```

**Linux/macOS:**

```bash
source .venv/bin/activate
```

Instale as dependências e inicie a API:

```bash
pip install -r requirements.txt
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

### 2. Iniciar o frontend

Abra outro terminal e entre na pasta `frontend`:

```bash
cd frontend
python -m http.server 5500
```

### 3. Executar projeto

Abra `http://127.0.0.1:5500` no navegador.

## Contas de demonstração

- Administrador: `admin@ecocity.local` / `Admin123!`
- Cidadão: `cidadao@ecocity.local` / `Cidadao123!`
