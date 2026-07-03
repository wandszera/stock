# Frontend

O frontend do Stock Flow vive nesta pasta e hoje representa uma interface operacional mais completa para estoque, recebimentos, vendas, contagens e analise documental.

## O que existe hoje

- Login operacional conectado a API FastAPI.
- Painel com visao geral, contexto operacional e resumo analitico.
- Fluxos de transferencia, ajuste, recebimento, venda e contagem.
- Lista paginada de vendas, movimentos, recebimentos e fila de rascunhos.
- Relatorio documental com busca, filtros dedicados, paginacao, impressao e exportacao CSV.
- Painel de risco por fornecedor com historico, impressao e exportacao CSV.
- Modo demonstrativo com dados locais para explorar a interface sem sessao autenticada.

## Como executar

### Opcao 1: servir como frontend estatico

1. Sirva esta pasta com qualquer servidor estatico.
2. Garanta que a API FastAPI esteja rodando.
3. Se a API nao estiver em `http://127.0.0.1:8000`, defina `window.STOCK_API_URL` antes de carregar `app.js`.

Exemplo:

```html
<script>
  window.STOCK_API_URL = "http://127.0.0.1:8000";
</script>
```

### Opcao 2: usar pelo backend

O backend tambem serve a interface em `/app/`, com `index.html`, `styles.css` e `app.js` separados da camada de API.

## Estrutura

- [index.html](C:/Users/wand/Desktop/projetos_pessoais/stock/frontend/index.html): markup principal da interface.
- [styles.css](C:/Users/wand/Desktop/projetos_pessoais/stock/frontend/styles.css): estilos do painel.
- [app.js](C:/Users/wand/Desktop/projetos_pessoais/stock/frontend/app.js): estado da aplicacao, chamadas de API, modo demo, renderizacao, exportacoes e impressoes.

## Integracao com a API

O frontend consome principalmente:

- `/health`
- `/auth`
- `/products`, `/variants`, `/stores`
- `/inventory/balances`
- `/inventory/movements`
- `/inventory/entry`, `/inventory/adjustment`, `/inventory/transfer`
- `/inventory/receipts`
- `/inventory/receipts/{receipt_id}`
- `/inventory/receipts/{receipt_id}/export`
- `/inventory/receipts-report`
- `/inventory/receipts-report/export`
- `/inventory/supplier-risk-history`
- `/sales`
- `/counts`

## Fluxos importantes

### Recebimentos

- Cadastro manual de recebimento com multiplos itens.
- Referencias recentes para acelerar preenchimento.
- Salvamento de rascunho, aprovacao, descarte e efetivacao.
- Detalhe do recebimento com itens, auditoria, impressao e exportacao CSV.

### Relatorio documental

- Busca textual por fornecedor ou documento.
- Filtros dedicados de periodo.
- Paginacao real ponta a ponta.
- Exportacao CSV e impressao de resumo.

### Modo demonstrativo

- Carrega contexto demo sem depender de login.
- Exibe recebimentos, rascunhos e relatorio documental simulados.
- Permite exportacoes e impressoes demonstrativas nos fluxos suportados.
- Acoes que exigem operacao real deixam isso explicito na mensagem ao usuario.

## Desenvolvimento

- O frontend foi separado da API, mas continua alinhado ao contrato do backend deste projeto.
- O bundle e validado por [backend/tests/test_frontend.py](C:/Users/wand/Desktop/projetos_pessoais/stock/backend/tests/test_frontend.py).
- As regras operacionais e de exportacao ligadas a recebimentos e relatorios tambem aparecem em [backend/tests/test_inventory_and_sales.py](C:/Users/wand/Desktop/projetos_pessoais/stock/backend/tests/test_inventory_and_sales.py).

## Observacoes

- O backend aceita origens locais comuns para desenvolvimento via CORS.
- Se voce alterar ids, textos-chave ou pontos de integracao do frontend, atualize os testes de frontend junto.
