def test_frontend_route_is_served_from_separate_folder(client):
    response = client.get("/app/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Stock Flow" in response.text
    assert "./styles.css" in response.text
    assert "./app.js" in response.text
    assert 'type="module"' in response.text
    assert "Recebimento de estoque" in response.text
    assert "Transferencia entre lojas" in response.text
    assert "Ajuste de saldo" in response.text
    assert "Venda da loja" in response.text
    assert "Contagem de estoque" in response.text
    assert "Escolha a tarefa principal" in response.text
    assert "Modo guiado" in response.text
    assert "Receber" in response.text
    assert "Vender" in response.text
    assert "Contar" in response.text
    assert "Transferir" in response.text
    assert "Ajustar" in response.text
    assert 'id="workspace-helper"' in response.text
    assert "Entre com um usuario operacional ja cadastrado na API." in response.text
    assert "Pagina anterior" in response.text
    assert "Vendas desde" in response.text
    assert "Movimentos desde" in response.text
    assert "Fornecedor, CD ou origem interna" in response.text
    assert "Buscar fornecedor ou documento no relatorio" in response.text
    assert 'id="receipt-report-date-from"' in response.text
    assert 'id="receipt-report-date-to"' in response.text
    assert 'id="print-receipt-report-button"' in response.text
    assert 'id="export-receipt-report-button"' in response.text
    assert "Exportar relatorio CSV" in response.text
    assert "Painel admin" in response.text
    assert 'id="admin-user-form"' in response.text
    assert 'id="admin-store-form"' in response.text
    assert 'id="admin-users-list"' in response.text
    assert 'id="admin-stores-list"' in response.text
    assert 'id="operation-context"' in response.text
    assert 'id="receipt-detail"' in response.text
    assert "Selecione um recebimento para ver fornecedor, documento e itens recebidos." in response.text
    assert 'id="print-receipt-button"' in response.text
    assert 'id="export-receipt-button"' in response.text
    assert "Exportar recebimento CSV" in response.text
    assert "Catalogo e escopo" in response.text
    assert "Operacao e recebimentos" in response.text
    assert "Analise documental" in response.text
    assert "Painel operacional" in response.text
    assert "Visao geral" in response.text
    assert "Catalogo e analise" in response.text
    assert "Consultar e analisar" in response.text
    assert "Admin" in response.text


def test_health_endpoint_is_still_served(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_endpoint_checks_database(client):
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_frontend_javascript_exposes_demo_receipt_and_report_flows(client):
    response = client.get("/app/app.js")

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    assert "Visual demonstrativo ativo. Entre para operar dados reais." in response.text
    assert "Modo demonstrativo: faca login para registrar recebimentos reais." in response.text
    assert "Resumo do recebimento demonstrativo enviado para impressao." in response.text
    assert "Recebimento demonstrativo exportado em CSV." in response.text
    assert "Relatorio documental demonstrativo exportado em CSV." in response.text
    assert "recebimento-demo-" in response.text
    assert "relatorio-recebimentos-demo.csv" in response.text
    assert 'apiFetch("/users/")' in response.text
    assert 'apiFetch("/stores/")' in response.text
    assert '"Idempotency-Key"' in response.text


def test_frontend_serves_shared_document_utilities(client):
    response = client.get("/app/modules/document-utils.js")

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    assert "export function downloadCsv" in response.text
    assert "export function buildPrintHtmlDocument" in response.text
