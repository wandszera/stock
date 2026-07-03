# Stock Flow - Sistema de Estoque

Stock Flow é uma solução integrada de gerenciamento de estoque, vendas, recebimentos e analytics. O projeto possui uma arquitetura dividida em uma API robusta construída com **FastAPI** (Python) e um painel de controle interativo desenvolvido em **HTML, CSS e JavaScript puros** (Vanilla JS).

---

## 🚀 Funcionalidades Principais

*   **Painel Geral (Dashboard):** Visão geral operacional, resumos analíticos e contexto em tempo real do estoque.
*   **Gestão de Inventário:** Fluxos de transferência, ajuste, recebimento, venda e contagem física de mercadorias.
*   **Gestão de Recebimentos:** Cadastro manual com múltiplos itens, rascunhos com fluxo de salvamento, aprovação/descarte e efetivação.
*   **Relatório Documental:** Histórico de movimentações com busca textual por fornecedor/documento, filtros por período, paginação ponta a ponta, exportação para CSV e impressão de resumos.
*   **Análise de Risco de Fornecedor:** Painel dedicado com histórico de conformidade por fornecedor, permitindo impressão e exportação.
*   **Modo Demonstrativo:** O frontend pode ser explorado sem autenticação ou API rodando, operando a partir de simulações com dados locais.

---

## 🛠️ Tecnologias Utilizadas

### Backend
*   **Python 3.10+**
*   **FastAPI:** Framework web assíncrono para construção da API.
*   **SQLAlchemy / Alembic:** ORM e controle de migrações de banco de dados.
*   **Uvicorn:** Servidor ASGI de alta performance.
*   **Pytest:** Suíte de testes automatizados unitários e de integração.
*   **SQLite:** Banco de dados padrão local (`stock.db`).

### Frontend
*   **HTML5 / Vanilla CSS:** Layout moderno, responsivo e estilizado sem frameworks adicionais.
*   **Vanilla JavaScript (ES6):** Controle de estado, manipulação do DOM e integrações de API de forma nativa.

---

## 📂 Estrutura de Pastas do Projeto

```text
stock/
├── backend/
│   ├── app/                 # Código-fonte da aplicação FastAPI
│   │   ├── api/             # Rotas e controladores da API
│   │   ├── core/            # Configurações globais e segurança
│   │   ├── models/          # Modelos de dados SQLAlchemy
│   │   ├── schemas/         # Esquemas de validação Pydantic
│   │   ├── static/          # Arquivos estáticos adicionais
│   │   └── main.py          # Ponto de entrada do backend FastAPI
│   ├── migrations/          # Scripts de migração do banco de dados (Alembic)
│   ├── tests/               # Testes automatizados (pytest)
│   ├── .env                 # Arquivo de variáveis de ambiente
│   ├── alembic.ini          # Configuração do Alembic
│   ├── requirements.txt     # Dependências Python
│   └── stock.db             # Banco de dados local SQLite (gerado automaticamente)
├── frontend/
│   ├── index.html           # Layout markup da interface
│   ├── styles.css           # Estilos visuais do painel
│   ├── app.js               # Lógica de estados, renderização e conexões de API
│   └── README.md            # Documentação dedicada do frontend
├── .gitignore               # Configurações de arquivos ignorados pelo Git
└── pytest.ini               # Configurações globais do pytest
```

---

## ⚙️ Instalação e Execução

### Pré-requisitos
*   Python 3.10 ou superior instalado.

### Passo 1: Configurar o Backend

1.  Navegue até a pasta `backend`:
    ```bash
    cd backend
    ```

2.  Crie um ambiente virtual Python:
    ```bash
    python -m venv env
    ```

3.  Ative o ambiente virtual:
    *   **No Windows (PowerShell):**
        ```powershell
        .\env\Scripts\Activate.ps1
        ```
    *   **No Linux/macOS:**
        ```bash
        source env/bin/activate
        ```

4.  Instale as dependências necessárias:
    ```bash
    pip install -r requirements.txt
    ```

5.  Configure o arquivo `.env` com base no padrão:
    ```ini
    DATABASE_URL=sqlite:///./stock.db
    BACKEND_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173
    SECRET_KEY=stock-dev-jwt-secret-2026-rotacionada-com-tamanho-seguro-64chars
    ACCESS_TOKEN_EXPIRE_MINUTES=60
    ALGORITHM=HS256
    ```

6.  Execute o servidor FastAPI com recarregamento dinâmico (live reload):
    ```bash
    uvicorn app.main:app --reload
    ```

O backend estará ativo em `http://127.0.0.1:8000`. A documentação interativa da API poderá ser acessada em `http://127.0.0.1:8000/docs`.

---

### Passo 2: Executar o Frontend

O backend já monta e serve o frontend automaticamente na rota `/app`. 

*   Acesse o painel completo acessando: **`http://127.0.0.1:8000/app/index.html`** (ou apenas **`http://127.0.0.1:8000/app/`**).

Alternativamente, a pasta `frontend` pode ser servida de forma independente por qualquer servidor estático de arquivos (como Live Server do VS Code, nginx, ou rodando `python -m http.server 3000` dentro da pasta `frontend`). 
Se o frontend rodar isolado em outra porta, você poderá ajustar o endpoint da API definindo `window.STOCK_API_URL` antes de carregar o script `app.js` no arquivo HTML.

---

## 🧪 Executando os Testes Automatizados

O projeto conta com testes automatizados cobrindo tanto a lógica do backend quanto a integração e contratos com o frontend.

Para rodar todos os testes, certifique-se de que o ambiente virtual está ativado, posicione-se no diretório raiz do projeto e execute:

```bash
pytest
```

---

## 📝 Contrato e Desenvolvimento

- Qualquer alteração nos IDs, strings ou endpoints que afetem a comunicação do frontend com a API deve ser acompanhada de atualizações nos testes localizados em `backend/tests/test_frontend.py` e `backend/tests/test_inventory_and_sales.py`.
