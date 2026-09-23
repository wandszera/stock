# Stock Flow - Inventory System

Stock Flow is an integrated solution for inventory management, sales, receipts, and analytics. The project features a split architecture with a robust API built with **FastAPI** (Python) and an interactive dashboard developed in **HTML, CSS, and plain JavaScript** (Vanilla JS).

---

## 🚀 Key Features

*   **General Dashboard:** Operational overview, analytical summaries, and real-time inventory context.
*   **Inventory Management:** Flows for transfer, adjustment, receipt, sale, and physical counting of goods.
*   **Receipts Management:** Manual registration with multiple items, drafts with a save flow, approval/discard, and execution.
*   **Documental Report:** Movement history with textual search by supplier/document, filters by period, end-to-end pagination, CSV export, and summary printing.
*   **Supplier Risk Analysis:** Dedicated dashboard with compliance history per supplier, allowing printing and export.
*   **Transactional Safety:** Row locking, atomic stock ledger updates, deterministic lock ordering, and idempotent sales and batch receipts.
*   **Demo Mode:** The frontend can be explored without authentication or a running API, operating based on simulations with local data.

---

## 🛠️ Technologies Used

### Backend
*   **Python 3.10+**
*   **FastAPI:** Asynchronous web framework for building the API.
*   **SQLAlchemy / Alembic:** ORM and database migrations control.
*   **Uvicorn:** High-performance ASGI server.
*   **Pytest:** Automated unit and integration testing suite.
*   **SQLite:** Default local database (`stock.db`).

### Frontend
*   **HTML5 / Vanilla CSS:** Modern, responsive layout styled without additional frameworks.
*   **Vanilla JavaScript (ES6):** State control, DOM manipulation, and API integrations natively.

---

## 📂 Project Folder Structure

```text
stock/
├── backend/
│   ├── app/                 # FastAPI application source code
│   │   ├── api/             # API routes and controllers
│   │   ├── core/            # Global configurations and security
│   │   ├── models/          # SQLAlchemy data models
│   │   ├── schemas/         # Pydantic validation schemas
│   │   ├── services/        # Regras de dominio e persistencia reutilizaveis
│   │   ├── static/          # Additional static files
│   │   └── main.py          # FastAPI backend entry point
│   ├── migrations/          # Database migration scripts (Alembic)
│   ├── tests/               # Automated tests (pytest)
│   ├── .env                 # Environment variables file
│   ├── alembic.ini          # Alembic configuration
│   ├── requirements.txt     # Python dependencies
│   └── stock.db             # Local SQLite database (auto-generated)
├── frontend/
│   ├── index.html           # Interface markup layout
│   ├── styles.css           # Dashboard visual styles
│   ├── app.js               # State logic, rendering, and API connections
│   ├── modules/             # Utilitarios reutilizaveis do navegador
│   └── README.md            # Dedicated frontend documentation
├── .gitignore               # Git ignored files configuration
└── pytest.ini               # Global pytest configurations
```

---

## ⚙️ Installation and Execution

### Prerequisites
*   Python 3.10 or higher installed.

### Step 1: Set up the Backend

1.  Navigate to the `backend` folder:
    ```bash
    cd backend
    ```

2.  Create a Python virtual environment:
    ```bash
    python -m venv env
    ```

3.  Activate the virtual environment:
    *   **On Windows (PowerShell):**
        ```powershell
        .\env\Scripts\Activate.ps1
        ```
    *   **On Linux/macOS:**
        ```bash
        source env/bin/activate
        ```

4.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

5.  Configure the `.env` file based on the standard:
    ```ini
    DATABASE_URL=sqlite:///./stock.db
    BACKEND_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173
    SECRET_KEY=stock-dev-jwt-secret-2026-rotacionada-com-tamanho-seguro-64chars
    ACCESS_TOKEN_EXPIRE_MINUTES=60
    ALGORITHM=HS256
    ```

6.  Run the FastAPI server with live reload:
    ```bash
    uvicorn app.main:app --reload
    ```

The backend will be active at `http://127.0.0.1:8000`. The interactive API documentation can be accessed at `http://127.0.0.1:8000/docs`.

---

### Step 2: Run the Frontend

The backend already mounts and serves the frontend automatically on the `/app` route.

*   Access the complete dashboard by going to: **`http://127.0.0.1:8000/app/index.html`** (or just **`http://127.0.0.1:8000/app/`**).

Alternatively, the `frontend` folder can be served independently by any static file server (like Live Server in VS Code, nginx, or by running `python -m http.server 3000` inside the `frontend` folder).
If the frontend runs isolated on another port, you can adjust the API endpoint by setting `window.STOCK_API_URL` before loading the `app.js` script in the HTML file.

### Execucao com Docker e PostgreSQL

1. Copie `backend/production.env.example` para `backend/production.env` e substitua os placeholders.
2. Execute a partir da raiz do projeto:

```bash
docker compose --env-file backend/production.env -f backend/compose.yaml up --build
```

O container da aplicacao executa as migracoes antes de iniciar, roda como usuario
nao privilegiado e expoe `/health` para liveness e `/ready` para readiness do banco.
Em producao, a inicializacao falha se SQLite, segredo curto, CORS curinga ou hosts
curinga forem configurados.

### Observabilidade

- Cada resposta inclui `X-Request-ID`; um identificador valido enviado pelo cliente e preservado.
- A aplicacao escreve logs JSON de inicializacao, encerramento, acesso e erros, sem corpo ou headers sensiveis.
- Erros inesperados retornam uma mensagem segura com o identificador da requisicao.
- `/metrics` expoe contadores, requisicoes em andamento e histogramas de latencia no formato Prometheus.
- `METRICS_ENABLED=false` desativa o endpoint quando a coleta nao for usada.

O container usa um worker por padrao para manter as metricas em memoria consistentes.
Para escalar, prefira aumentar o numero de containers. Proteja `/metrics` na camada
de rede ou proxy reverso quando o servico estiver exposto publicamente.

### Rastreabilidade operacional

Operacoes de venda, devolucao, cancelamento, recebimento, ajuste, transferencia
e contagem geram eventos na trilha unificada. Cada evento registra usuario,
loja, entidade, horario, metadados resumidos e o mesmo `request_id` gravado nos
movimentos de estoque relacionados.

Administradores consultam toda a rede e gerentes ficam limitados a propria loja:

```text
GET /audit/events
GET /audit/events?entity_type=sale&entity_id=<uuid>
GET /audit/events?request_id=<request-id>
GET /audit/events?store_id=<uuid>&action=inventory.transferred
```

A resposta inclui nome e e-mail do ator e os IDs dos movimentos correlacionados.
Operadores não têm acesso à trilha administrativa.

### Decision Intelligence — previsão e backtesting

A primeira camada analítica agrega vendas concluídas em séries semanais por
loja e variante. O backtesting usa origem móvel expansiva: cada previsão é
treinada somente com períodos anteriores, sem embaralhamento ou acesso ao
futuro.

Modelos comparados inicialmente:

- `naive`: repete a demanda da última semana;
- `moving_average_4`: média móvel das quatro semanas anteriores;
- `exponential_smoothing`: suavização exponencial com tendência quando há histórico suficiente.

Cada execução calcula MAE, RMSE, WAPE, viés e nível de serviço, persiste a
comparação e identifica o modelo vencedor por WAPE, usando RMSE e MAE como
desempate.

```text
POST /analytics/backtests
GET  /analytics/backtests
GET  /analytics/backtests/{run_id}
```

Uma execução exige, por padrão, oito semanas de treinamento mais o horizonte.
Séries curtas retornam uma mensagem explícita em vez de gerar uma recomendação
sem sustentação estatística.

### Decision Intelligence — risco de fornecedores

Entregas de fornecedores alimentam um score explicável de 0 a 100. O cálculo
combina atraso médio (35%), variabilidade do prazo (20%), defeitos (25%) e
concentração das compras da loja (20%). A resposta preserva cada componente,
sua contribuição ponderada, as métricas brutas e uma explicação dos principais
fatores, permitindo que o gestor revise a classificação antes de agir.

```text
POST /supplier-intelligence/deliveries
POST /supplier-intelligence/scores/run
GET  /supplier-intelligence/ranking?store_id=<uuid>
```

Os níveis são `low`, `moderate`, `high` e `critical`. Cada registro e execução
também entra na trilha unificada de auditoria e gerentes permanecem restritos à
própria loja.

### Decision Intelligence — reposição otimizada

A camada de reposição projeta a demanda semanal, considera prazo, estoque
mínimo, reserva de segurança e custo unitário. Ela compara explicitamente a
política atual (não repor), uma regra simples (cobrir a demanda no prazo) e a
recomendação proposta. Quando há orçamento, um alocador determinístico prioriza
as maiores exposições de ruptura sem ultrapassar o limite. O gestor pode aprovar,
rejeitar ou substituir manualmente cada quantidade; a decisão fica auditável.

```text
POST  /replenishment/recommendations/run
GET   /replenishment/recommendations?store_id=<uuid>
PATCH /replenishment/recommendations/{id}/decision
```

---

## 🧪 Running Automated Tests

The project has automated tests covering both the backend logic and the integration and contracts with the frontend.

To run all tests, ensure the virtual environment is activated, navigate to the project's root directory, and execute:

```bash
pytest
```

Para validar tambem a sintaxe dos modulos JavaScript:

```bash
npm run check
```

O workflow em `.github/workflows/ci.yml` executa essas verificacoes automaticamente
em pushes para `main` e em pull requests. As dependencias Python diretas ficam
fixadas em `backend/requirements.txt` para tornar instalações e CI reproduziveis.

Os testes de concorrencia com bloqueio real usam PostgreSQL. Para executa-los
localmente, configure uma base exclusiva para testes e rode:

```bash
TEST_POSTGRES_DATABASE_URL=postgresql+psycopg://usuario:senha@localhost:5432/stock_test pytest -m postgres
```

Cada teste cria um schema isolado e o remove ao terminar. O CI provisiona o
PostgreSQL automaticamente para essa validacao.

As rotas `POST /sales/` e `POST /inventory/entries` aceitam o header
`Idempotency-Key`. Repeticoes com a mesma chave e o mesmo payload retornam o
resultado original sem movimentar o estoque novamente; reutilizar a chave com
outro payload retorna conflito HTTP 409.

---

## 📝 Contract and Development

- Any changes to IDs, strings, or endpoints that affect the frontend's communication with the API must be accompanied by updates in the tests located at `backend/tests/test_frontend.py` and `backend/tests/test_inventory_and_sales.py`.
