# Stock Flow - Inventory System

Stock Flow is an integrated solution for inventory management, sales, receipts, and analytics. The project features a split architecture with a robust API built with **FastAPI** (Python) and an interactive dashboard developed in **HTML, CSS, and plain JavaScript** (Vanilla JS).

---

## 🚀 Key Features

*   **General Dashboard:** Operational overview, analytical summaries, and real-time inventory context.
*   **Inventory Management:** Flows for transfer, adjustment, receipt, sale, and physical counting of goods.
*   **Receipts Management:** Manual registration with multiple items, drafts with a save flow, approval/discard, and execution.
*   **Documental Report:** Movement history with textual search by supplier/document, filters by period, end-to-end pagination, CSV export, and summary printing.
*   **Supplier Risk Analysis:** Dedicated dashboard with compliance history per supplier, allowing printing and export.
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

---

## 🧪 Running Automated Tests

The project has automated tests covering both the backend logic and the integration and contracts with the frontend.

To run all tests, ensure the virtual environment is activated, navigate to the project's root directory, and execute:

```bash
pytest
```

---

## 📝 Contract and Development

- Any changes to IDs, strings, or endpoints that affect the frontend's communication with the API must be accompanied by updates in the tests located at `backend/tests/test_frontend.py` and `backend/tests/test_inventory_and_sales.py`.
