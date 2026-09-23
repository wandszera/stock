const state = {
  token: localStorage.getItem("stock_token") || "",
  activeWorkspace: localStorage.getItem("stock_active_workspace") || "receive",
  currentUser: null,
  selectedSaleId: null,
  stores: [],
  variants: [],
  balances: [],
  productsById: new Map(),
  activeCountId: null,
  salesPage: 0,
  movementsPage: 0,
  salesPageSize: 8,
  movementsPageSize: 8,
  salesTotal: 0,
  movementsTotal: 0,
  currentSales: [],
  currentMovements: [],
  receiptReferences: [],
  receipts: [],
  receiptsPage: 0,
  receiptsPageSize: 12,
  receiptsTotal: 0,
  draftReceipts: [],
  draftReceiptsTotal: 0,
  selectedReceiptId: null,
  editingReceiptId: null,
  receiptDetailsById: new Map(),
  receiptAuditFilter: "",
  selectedDraftReceiptIds: new Set(),
  draftReceiptsQuery: "",
  receiptReportQuery: "",
  receiptReportDateFrom: "",
  receiptReportDateTo: "",
  receiptReport: [],
  receiptReportRaw: [],
  receiptReportPage: 0,
  receiptReportPageSize: 8,
  receiptReportTotal: 0,
  draftReceiptsPage: 0,
  draftReceiptsPageSize: 5,
  draftReceiptsSensitiveOnly: false,
  draftReceiptsCriticalOnly: false,
  receiptReportSensitiveOnly: false,
  supplierRiskFilter: "",
  supplierRiskDateFrom: "",
  supplierRiskDateTo: "",
  supplierRiskPage: 0,
  supplierRiskPageSize: 3,
  supplierRiskTargets: [],
  supplierRiskHistory: [],
  adminUsers: [],
  pendingSaleIdempotencyKey: null,
  pendingEntryIdempotencyKey: null,
};

import {
  buildCsvRows,
  buildPrintHtmlDocument,
  downloadBlob,
  downloadCsv,
  openPrintDocument,
} from "./modules/document-utils.js";

const API_BASE_URL = (window.STOCK_API_URL || window.location.origin || "").replace(/\/$/, "");

const demoData = {
  stores: [
    { id: "store-centro", name: "Loja Centro" },
    { id: "store-vitrine", name: "Loja Vitrine" },
    { id: "store-outlet", name: "Outlet Norte" },
  ],
  products: [
    { id: "prod-1", name: "Camisa Oxford", brand: "Stock Flow", is_active: true },
    { id: "prod-2", name: "Calca Chino", brand: "Stock Flow", is_active: true },
    { id: "prod-3", name: "Jaqueta Nylon", brand: "Stock Flow", is_active: true },
  ],
  variants: [
    { id: "var-1", product_id: "prod-1", sku: "OXF-BR-40", barcode: "789100000001", sale_price: 189.9 },
    { id: "var-2", product_id: "prod-2", sku: "CHI-KH-42", barcode: "789100000002", sale_price: 239.9 },
    { id: "var-3", product_id: "prod-3", sku: "NYL-BK-M", barcode: "789100000003", sale_price: 329.9 },
    { id: "var-4", product_id: "prod-1", sku: "OXF-AZ-38", barcode: "789100000004", sale_price: 179.9 },
  ],
  balances: [
    { store_id: "store-centro", variant_id: "var-1", on_hand_qty: 18 },
    { store_id: "store-centro", variant_id: "var-2", on_hand_qty: 11 },
    { store_id: "store-centro", variant_id: "var-3", on_hand_qty: 6 },
    { store_id: "store-centro", variant_id: "var-4", on_hand_qty: 9 },
    { store_id: "store-vitrine", variant_id: "var-1", on_hand_qty: 12 },
    { store_id: "store-vitrine", variant_id: "var-2", on_hand_qty: 7 },
    { store_id: "store-vitrine", variant_id: "var-3", on_hand_qty: 4 },
    { store_id: "store-outlet", variant_id: "var-4", on_hand_qty: 15 },
  ],
  dashboard: {
    sales: { net_revenue: 18450.35, completed_count: 42, canceled_count: 3, items_sold: 126 },
    inventory: { total_on_hand_qty: 82, tracked_variants: 4, low_stock_variants: 2, out_of_stock_variants: 0 },
    daily_sales: [
      { date: "2026-04-13", net_revenue: 1490.0 },
      { date: "2026-04-14", net_revenue: 2120.5 },
      { date: "2026-04-15", net_revenue: 1780.25 },
      { date: "2026-04-16", net_revenue: 2640.1 },
      { date: "2026-04-17", net_revenue: 1965.4 },
      { date: "2026-04-18", net_revenue: 3180.0 },
      { date: "2026-04-19", net_revenue: 2875.2 },
    ],
    top_variants: [
      { product_name: "Camisa Oxford", sku: "OXF-BR-40", quantity_sold: 28, net_revenue: 5317.2 },
      { product_name: "Calca Chino", sku: "CHI-KH-42", quantity_sold: 19, net_revenue: 4558.1 },
      { product_name: "Jaqueta Nylon", sku: "NYL-BK-M", quantity_sold: 11, net_revenue: 3628.9 },
      { product_name: "Camisa Oxford", sku: "OXF-AZ-38", quantity_sold: 15, net_revenue: 2698.5 },
    ],
  },
  sales: [
    {
      id: "sale-demo-1",
      status: "completed",
      total_amount: 569.7,
      discount_amount: 20,
      sold_at: "2026-04-19T14:20:00",
      store_id: "store-centro",
      user_id: "operador.centro",
      items: [
        { variant_id: "var-1", quantity: 2, unit_price: 189.9, line_total: 379.8 },
        { variant_id: "var-2", quantity: 1, unit_price: 209.9, line_total: 209.9 },
      ],
    },
    {
      id: "sale-demo-2",
      status: "completed",
      total_amount: 329.9,
      discount_amount: 0,
      sold_at: "2026-04-19T11:05:00",
      store_id: "store-vitrine",
      user_id: "gerente.vitrine",
      items: [
        { variant_id: "var-3", quantity: 1, unit_price: 329.9, line_total: 329.9 },
      ],
    },
    {
      id: "sale-demo-3",
      status: "canceled",
      total_amount: 179.9,
      discount_amount: 0,
      sold_at: "2026-04-18T16:40:00",
      store_id: "store-outlet",
      user_id: "caixa.outlet",
      items: [
        { variant_id: "var-4", quantity: 1, unit_price: 179.9, line_total: 179.9 },
      ],
    },
  ],
  counts: [
    {
      id: "count-demo-1",
      scope: "cycle",
      status: "open",
      store_id: "store-centro",
      created_at: "2026-04-19T09:00:00",
      items: [{ variant_id: "var-2" }],
    },
    {
      id: "count-demo-2",
      scope: "spot-check",
      status: "closed",
      store_id: "store-vitrine",
      created_at: "2026-04-18T18:15:00",
      items: [{ variant_id: "var-1" }, { variant_id: "var-3" }],
    },
  ],
  movements: [
    { movement_type: "sale", store_id: "store-centro", variant_id: "var-1", quantity_delta: -2 },
    { movement_type: "transfer_in", store_id: "store-vitrine", variant_id: "var-2", quantity_delta: 4 },
    { movement_type: "count_adjustment", store_id: "store-centro", variant_id: "var-2", quantity_delta: -1 },
    { movement_type: "sale", store_id: "store-outlet", variant_id: "var-4", quantity_delta: -1 },
  ],
  receiptReferences: [
    {
      supplier_reference: "Fornecedor Oxford",
      document_reference: "NF-88421",
      reason: "reposicao de colecao",
      item_count: 2,
      total_quantity: 14,
      created_at: "2026-04-19T08:30:00",
    },
    {
      supplier_reference: "CD Norte",
      document_reference: "TRF-1904",
      reason: "redistribuicao interna",
      item_count: 1,
      total_quantity: 6,
      created_at: "2026-04-18T16:10:00",
    },
  ],
  receipts: [
    {
      receipt_id: "receipt-demo-1",
      status: "draft",
      supplier_reference: "Fornecedor Oxford",
      document_reference: "NF-88421",
      total_quantity: 14,
      item_count: 2,
      created_at: "2026-04-19T08:30:00",
      store_id: "store-centro",
      reason: "reposicao de colecao",
      notes: "Conferencia inicial pendente de aprovacao gerencial.",
      requires_approval: true,
      approved_by: null,
      items: [
        { variant_id: "var-1", quantity: 8, created_at: "2026-04-19T08:31:00" },
        { variant_id: "var-4", quantity: 6, created_at: "2026-04-19T08:32:00" },
      ],
      audit: [
        { action: "draft_created", details: "Rascunho aberto pela operacao.", created_at: "2026-04-19T08:30:00", created_by: "operador.centro" },
      ],
    },
    {
      receipt_id: "receipt-demo-2",
      status: "checked",
      supplier_reference: "CD Norte",
      document_reference: "TRF-1904",
      total_quantity: 6,
      item_count: 1,
      created_at: "2026-04-18T16:10:00",
      store_id: "store-vitrine",
      reason: "redistribuicao interna",
      notes: "Recebimento conferido e liberado para abastecimento.",
      requires_approval: false,
      approved_by: null,
      items: [
        { variant_id: "var-2", quantity: 6, created_at: "2026-04-18T16:11:00" },
      ],
      audit: [
        { action: "direct_receipt_created", details: "Recebimento registrado no painel.", created_at: "2026-04-18T16:10:00", created_by: "gerente.vitrine" },
        { action: "status_updated", details: "Documento marcado como conferido.", created_at: "2026-04-18T16:40:00", created_by: "gerente.vitrine" },
      ],
    },
  ],
};

const preferenceKeys = {
  dashboardDays: "stock_dashboard_days",
  dashboardTopLimit: "stock_dashboard_top_limit",
  storeFilter: "stock_store_filter",
  productQuery: "stock_product_query",
  skuQuery: "stock_sku_query",
  barcodeQuery: "stock_barcode_query",
  movementTypeQuery: "stock_movement_type_query",
  movementSupplierQuery: "stock_movement_supplier_query",
  movementDocumentQuery: "stock_movement_document_query",
  receiptStatusQuery: "stock_receipt_status_query",
  draftReceiptsQuery: "stock_draft_receipts_query",
  draftReceiptsSort: "stock_draft_receipts_sort",
  draftReceiptsSensitiveOnly: "stock_draft_receipts_sensitive_only",
  draftReceiptsCriticalOnly: "stock_draft_receipts_critical_only",
  receiptReportQuery: "stock_receipt_report_query",
  receiptReportDateFrom: "stock_receipt_report_date_from",
  receiptReportDateTo: "stock_receipt_report_date_to",
  receiptReportSort: "stock_receipt_report_sort",
  receiptReportSensitiveOnly: "stock_receipt_report_sensitive_only",
  supplierRiskFilter: "stock_supplier_risk_filter",
  supplierRiskDateFrom: "stock_supplier_risk_date_from",
  supplierRiskDateTo: "stock_supplier_risk_date_to",
  movementDateFrom: "stock_movement_date_from",
  movementDateTo: "stock_movement_date_to",
  salesVariantQuery: "stock_sales_variant_query",
  salesStatusQuery: "stock_sales_status_query",
  salesDateFrom: "stock_sales_date_from",
  salesDateTo: "stock_sales_date_to",
  transferSourceStore: "stock_transfer_source_store",
  transferDestinationStore: "stock_transfer_destination_store",
  saleStore: "stock_sale_store",
  countStore: "stock_count_store",
};

const elements = {
  loginForm: document.getElementById("login-form"),
  workflowHelper: document.getElementById("workspace-helper"),
  workflowTabs: Array.from(document.querySelectorAll("[data-workspace]")),
  workspacePanels: Array.from(document.querySelectorAll("[data-workspace-panel]")),
  adminSection: document.getElementById("admin-section"),
  adminRoleChip: document.getElementById("admin-role-chip"),
  adminSummary: document.getElementById("admin-summary"),
  adminUserForm: document.getElementById("admin-user-form"),
  adminUserName: document.getElementById("admin-user-name"),
  adminUserEmail: document.getElementById("admin-user-email"),
  adminUserPassword: document.getElementById("admin-user-password"),
  adminUserRole: document.getElementById("admin-user-role"),
  adminUserStore: document.getElementById("admin-user-store"),
  adminUserStatus: document.getElementById("admin-user-status"),
  adminStoreForm: document.getElementById("admin-store-form"),
  adminStoreName: document.getElementById("admin-store-name"),
  adminStoreTimezone: document.getElementById("admin-store-timezone"),
  adminStoreActive: document.getElementById("admin-store-active"),
  adminStoreStatus: document.getElementById("admin-store-status"),
  adminUsersList: document.getElementById("admin-users-list"),
  adminUsersCount: document.getElementById("admin-users-count"),
  adminStoresList: document.getElementById("admin-stores-list"),
  adminStoresCount: document.getElementById("admin-stores-count"),
  transferForm: document.getElementById("transfer-form"),
  email: document.getElementById("email"),
  password: document.getElementById("password"),
  loginStatus: document.getElementById("login-status"),
  transferSourceStore: document.getElementById("transfer-source-store"),
  transferDestinationStore: document.getElementById("transfer-destination-store"),
  transferVariant: document.getElementById("transfer-variant"),
  transferQuantity: document.getElementById("transfer-quantity"),
  transferReason: document.getElementById("transfer-reason"),
  transferStatus: document.getElementById("transfer-status"),
  transferPreview: document.getElementById("transfer-preview"),
  useCurrentStoreTransferButton: document.getElementById("use-current-store-transfer"),
  swapTransferStoresButton: document.getElementById("swap-transfer-stores"),
  adjustmentForm: document.getElementById("adjustment-form"),
  adjustmentStore: document.getElementById("adjustment-store"),
  adjustmentVariant: document.getElementById("adjustment-variant"),
  adjustmentQuantity: document.getElementById("adjustment-quantity"),
  adjustmentReason: document.getElementById("adjustment-reason"),
  adjustmentPreview: document.getElementById("adjustment-preview"),
  adjustmentStatus: document.getElementById("adjustment-status"),
  entryForm: document.getElementById("entry-form"),
  entryStore: document.getElementById("entry-store"),
  entryItems: document.getElementById("entry-items"),
  addEntryItemButton: document.getElementById("add-entry-item"),
  saveEntryDraftButton: document.getElementById("save-entry-draft"),
  cancelEntryEditButton: document.getElementById("cancel-entry-edit"),
  entrySupplierReference: document.getElementById("entry-supplier-reference"),
  entryDocumentReference: document.getElementById("entry-document-reference"),
  entryReason: document.getElementById("entry-reason"),
  entryNotes: document.getElementById("entry-notes"),
  entryReferenceSuggestions: document.getElementById("entry-reference-suggestions"),
  entryPreview: document.getElementById("entry-preview"),
  entryStatus: document.getElementById("entry-status"),
  saleForm: document.getElementById("sale-form"),
  saleStore: document.getElementById("sale-store"),
  saleDiscount: document.getElementById("sale-discount"),
  saleItems: document.getElementById("sale-items"),
  addSaleItemButton: document.getElementById("add-sale-item"),
  saleFormStatus: document.getElementById("sale-form-status"),
  saleSummary: document.getElementById("sale-summary"),
  countForm: document.getElementById("count-form"),
  countStore: document.getElementById("count-store"),
  countScope: document.getElementById("count-scope"),
  countReason: document.getElementById("count-reason"),
  countVariant: document.getElementById("count-variant"),
  countQuantity: document.getElementById("count-quantity"),
  closeCountButton: document.getElementById("close-count-button"),
  countStatus: document.getElementById("count-status"),
  countPreview: document.getElementById("count-preview"),
  healthStatus: document.getElementById("health-status"),
  sessionStatus: document.getElementById("session-status"),
  executiveStrip: document.getElementById("executive-strip"),
  storeFilter: document.getElementById("store-filter"),
  productQuery: document.getElementById("product-query"),
  skuQuery: document.getElementById("sku-query"),
  barcodeQuery: document.getElementById("barcode-query"),
  movementTypeQuery: document.getElementById("movement-type-query"),
  movementSupplierQuery: document.getElementById("movement-supplier-query"),
  movementDocumentQuery: document.getElementById("movement-document-query"),
  receiptStatusQuery: document.getElementById("receipt-status-query"),
  movementDateFrom: document.getElementById("movement-date-from"),
  movementDateTo: document.getElementById("movement-date-to"),
  operationContext: document.getElementById("operation-context"),
  salesVariantQuery: document.getElementById("sales-variant-query"),
  salesStatusQuery: document.getElementById("sales-status-query"),
  salesDateFrom: document.getElementById("sales-date-from"),
  salesDateTo: document.getElementById("sales-date-to"),
  dashboardDays: document.getElementById("dashboard-days"),
  dashboardTopLimit: document.getElementById("dashboard-top-limit"),
  useCurrentStoreSaleButton: document.getElementById("use-current-store-sale"),
  useCurrentStoreCountButton: document.getElementById("use-current-store-count"),
  refreshButton: document.getElementById("refresh-button"),
  exportMovementsButton: document.getElementById("export-movements-button"),
  logoutButton: document.getElementById("logout-button"),
  productsList: document.getElementById("products-list"),
  variantsList: document.getElementById("variants-list"),
  balancesList: document.getElementById("balances-list"),
  movementsList: document.getElementById("movements-list"),
  salesList: document.getElementById("sales-list"),
  saleDetail: document.getElementById("sale-detail"),
  countsList: document.getElementById("counts-list"),
  receiptsList: document.getElementById("receipts-list"),
  draftReceiptsList: document.getElementById("draft-receipts-list"),
  draftReceiptsQuery: document.getElementById("draft-receipts-query"),
  draftReceiptsSensitiveOnly: document.getElementById("draft-receipts-sensitive-only"),
  draftReceiptsSort: document.getElementById("draft-receipts-sort"),
  showCriticalDraftsButton: document.getElementById("show-critical-drafts"),
  bulkApproveDraftsButton: document.getElementById("bulk-approve-drafts"),
  bulkPostDraftsButton: document.getElementById("bulk-post-drafts"),
  bulkDiscardDraftsButton: document.getElementById("bulk-discard-drafts"),
  draftsPrevPage: document.getElementById("drafts-prev-page"),
  draftsNextPage: document.getElementById("drafts-next-page"),
  draftsPageStatus: document.getElementById("drafts-page-status"),
  receiptsPrevPage: document.getElementById("receipts-prev-page"),
  receiptsNextPage: document.getElementById("receipts-next-page"),
  receiptsPageStatus: document.getElementById("receipts-page-status"),
  receiptReportQuery: document.getElementById("receipt-report-query"),
  receiptReportDateFrom: document.getElementById("receipt-report-date-from"),
  receiptReportDateTo: document.getElementById("receipt-report-date-to"),
  receiptReportSort: document.getElementById("receipt-report-sort"),
  receiptReportSensitiveOnly: document.getElementById("receipt-report-sensitive-only"),
  exportReceiptReportButton: document.getElementById("export-receipt-report-button"),
  printReceiptReportButton: document.getElementById("print-receipt-report-button"),
  receiptReportList: document.getElementById("receipt-report-list"),
  receiptReportPrevPage: document.getElementById("receipt-report-prev-page"),
  receiptReportNextPage: document.getElementById("receipt-report-next-page"),
  receiptReportPageStatus: document.getElementById("receipt-report-page-status"),
  receiptDetail: document.getElementById("receipt-detail"),
  exportReceiptButton: document.getElementById("export-receipt-button"),
  loadReceiptIntoEntryButton: document.getElementById("load-receipt-into-entry"),
  printReceiptButton: document.getElementById("print-receipt-button"),
  receiptAuditFilter: document.getElementById("receipt-audit-filter"),
  dashboardSummary: document.getElementById("dashboard-summary"),
  dailySalesChart: document.getElementById("daily-sales-chart"),
  topVariantsList: document.getElementById("top-variants-list"),
  productsCount: document.getElementById("products-count"),
  variantsCount: document.getElementById("variants-count"),
  balancesCount: document.getElementById("balances-count"),
  movementsCount: document.getElementById("movements-count"),
  salesPrevPage: document.getElementById("sales-prev-page"),
  salesNextPage: document.getElementById("sales-next-page"),
  salesPageStatus: document.getElementById("sales-page-status"),
  movementsPrevPage: document.getElementById("movements-prev-page"),
  movementsNextPage: document.getElementById("movements-next-page"),
  movementsPageStatus: document.getElementById("movements-page-status"),
  salesCount: document.getElementById("sales-count"),
  countsCount: document.getElementById("counts-count"),
  receiptsCount: document.getElementById("receipts-count"),
  draftReceiptsCount: document.getElementById("draft-receipts-count"),
  dailySalesCount: document.getElementById("daily-sales-count"),
  topVariantsCount: document.getElementById("top-variants-count"),
  salesStatus: document.getElementById("sales-status"),
  runScenarioButton: document.getElementById("run-scenario-button"),
  scenarioDemandMultiplier: document.getElementById("scenario-demand-multiplier"),
  scenarioDelayWeeks: document.getElementById("scenario-delay-weeks"),
  scenarioBudget: document.getElementById("scenario-budget"),
  scenarioStatus: document.getElementById("scenario-status"),
  scenarioSummary: document.getElementById("scenario-summary"),
  scenarioList: document.getElementById("scenario-list"),
  runReplenishmentButton: document.getElementById("run-replenishment-button"),
  replenishmentLeadTime: document.getElementById("replenishment-lead-time"),
  replenishmentMinimumStock: document.getElementById("replenishment-minimum-stock"),
  replenishmentBudget: document.getElementById("replenishment-budget"),
  replenishmentStatus: document.getElementById("replenishment-status"),
  replenishmentList: document.getElementById("replenishment-list"),
  runSupplierRiskButton: document.getElementById("run-supplier-risk-button"),
  saveSupplierDeliveryButton: document.getElementById("save-supplier-delivery-button"),
  supplierReference: document.getElementById("supplier-reference"),
  supplierOrderedAt: document.getElementById("supplier-ordered-at"),
  supplierExpectedAt: document.getElementById("supplier-expected-at"),
  supplierDeliveredAt: document.getElementById("supplier-delivered-at"),
  supplierReceivedQuantity: document.getElementById("supplier-received-quantity"),
  supplierDefectiveQuantity: document.getElementById("supplier-defective-quantity"),
  supplierPurchaseCost: document.getElementById("supplier-purchase-cost"),
  supplierIntelligenceStatus: document.getElementById("supplier-intelligence-status"),
  supplierRiskList: document.getElementById("supplier-risk-list"),
};

const workspaceMeta = {
  receive: {
    label: "Receber",
    helper: "Fluxo recomendado para entrada de estoque, rascunhos e conferencia de documentos.",
  },
  sell: {
    label: "Vender",
    helper: "Fluxo recomendado para registrar venda com revisao de itens, desconto e saldo.",
  },
  count: {
    label: "Contar",
    helper: "Fluxo recomendado para auditoria, contagem ciclica e fechamento de divergencias.",
  },
  transfer: {
    label: "Transferir",
    helper: "Fluxo recomendado para redistribuicao entre lojas com origem e destino definidos.",
  },
  adjust: {
    label: "Ajustar",
    helper: "Fluxo recomendado para acerto sistemico depois da validacao operacional.",
  },
};

function setSessionStatus() {
  elements.sessionStatus.textContent = state.token ? "ativa" : "desconectada";
}

function setActiveWorkspace(workspaceKey) {
  const nextWorkspace = workspaceMeta[workspaceKey] ? workspaceKey : "receive";
  state.activeWorkspace = nextWorkspace;
  localStorage.setItem("stock_active_workspace", nextWorkspace);

  elements.workflowTabs.forEach((button) => {
    const isActive = button.dataset.workspace === nextWorkspace;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });

  elements.workspacePanels.forEach((panel) => {
    panel.hidden = panel.dataset.workspacePanel !== nextWorkspace;
  });

  const meta = workspaceMeta[nextWorkspace];
  if (elements.workflowHelper && meta) {
    elements.workflowHelper.innerHTML = `<strong>${meta.label}</strong><span>${meta.helper}</span>`;
  }
}

function setStatus(message, kind = "muted") {
  elements.loginStatus.textContent = message;
  elements.loginStatus.className = `status ${kind}`;
}

function setTransferStatus(message, kind = "muted") {
  elements.transferStatus.textContent = message;
  elements.transferStatus.className = `status ${kind}`;
}

function setAdjustmentStatus(message, kind = "muted") {
  elements.adjustmentStatus.textContent = message;
  elements.adjustmentStatus.className = `status ${kind}`;
}

function setEntryStatus(message, kind = "muted") {
  elements.entryStatus.textContent = message;
  elements.entryStatus.className = `status ${kind}`;
}

function resetEntryFormState() {
  state.editingReceiptId = null;
  elements.entryForm.reset();
  elements.entryItems.innerHTML = "";
  elements.entryItems.appendChild(createEntryItemRow());
  renderEntryPreview();
}

function setSalesStatus(message, kind = "muted") {
  elements.salesStatus.textContent = message;
  elements.salesStatus.className = `status ${kind}`;
}

function setSaleFormStatus(message, kind = "muted") {
  elements.saleFormStatus.textContent = message;
  elements.saleFormStatus.className = `status ${kind}`;
}

function setCountStatus(message, kind = "muted") {
  elements.countStatus.textContent = message;
  elements.countStatus.className = `status ${kind}`;
}

function setAdminUserStatus(message, kind = "muted") {
  elements.adminUserStatus.textContent = message;
  elements.adminUserStatus.className = `status ${kind}`;
}

function setAdminStoreStatus(message, kind = "muted") {
  elements.adminStoreStatus.textContent = message;
  elements.adminStoreStatus.className = `status ${kind}`;
}

function isAdminUser() {
  return state.currentUser?.role === "admin";
}

function syncAdminUserStoreOptions() {
  if (!elements.adminUserStore) {
    return;
  }
  const currentValue = elements.adminUserStore.value;
  elements.adminUserStore.innerHTML = ['<option value="">Sem vinculo fixo</option>']
    .concat(
      state.stores.map((store) => `<option value="${store.id}">${store.name}</option>`)
    )
    .join("");
  if (currentValue) {
    elements.adminUserStore.value = currentValue;
  }
}

function renderAdminSummary() {
  if (!elements.adminSummary) {
    return;
  }
  if (!isAdminUser()) {
    elements.adminSummary.innerHTML = "";
    return;
  }
  const activeStores = state.stores.filter((store) => store.is_active).length;
  const activeUsers = state.adminUsers.filter((user) => user.is_active).length;
  elements.adminSummary.innerHTML = [
    {
      label: "Perfil atual",
      value: state.currentUser?.role || "-",
      detail: state.currentUser?.email || "Sessao nao identificada",
    },
    {
      label: "Usuarios ativos",
      value: String(activeUsers),
      detail: `${state.adminUsers.length} usuarios cadastrados`,
    },
    {
      label: "Lojas ativas",
      value: String(activeStores),
      detail: `${state.stores.length} lojas carregadas`,
    },
  ].map((item) => `
    <article class="summary-card">
      <span>${item.label}</span>
      <strong>${item.value}</strong>
      <small>${item.detail}</small>
    </article>
  `).join("");
}

function renderAdminUsers() {
  if (!elements.adminUsersList || !elements.adminUsersCount) {
    return;
  }
  if (!isAdminUser()) {
    renderList(elements.adminUsersList, elements.adminUsersCount, [], () => "");
    return;
  }
  renderList(elements.adminUsersList, elements.adminUsersCount, state.adminUsers, (user) => {
    const storeName = state.stores.find((store) => store.id === user.store_id)?.name || "Sem vinculo fixo";
    return `
      <article class="list-item">
        <strong>${user.name}</strong>
        <span>${user.email}</span>
        <div class="admin-card-meta">
          <span class="sale-tag">${user.role}</span>
          <span class="sale-tag ${user.is_active ? "" : "is-canceled"}">${user.is_active ? "ativo" : "inativo"}</span>
          <span class="sale-tag">${storeName}</span>
        </div>
      </article>
    `;
  });
}

function renderAdminStores() {
  if (!elements.adminStoresList || !elements.adminStoresCount) {
    return;
  }
  renderList(elements.adminStoresList, elements.adminStoresCount, state.stores, (store) => `
    <article class="list-item">
      <strong>${store.name}</strong>
      <span>Timezone: ${store.timezone}</span>
      <div class="admin-card-meta">
        <span class="sale-tag ${store.is_active ? "" : "is-canceled"}">${store.is_active ? "ativa" : "inativa"}</span>
        <span class="sale-tag">${store.id}</span>
      </div>
    </article>
  `);
}

function renderAdminPanel() {
  if (!elements.adminSection) {
    return;
  }
  const canShow = Boolean(state.token) && isAdminUser();
  elements.adminSection.hidden = !canShow;
  if (!canShow) {
    return;
  }
  elements.adminRoleChip.textContent = state.currentUser?.role || "admin";
  syncAdminUserStoreOptions();
  renderAdminSummary();
  renderAdminUsers();
  renderAdminStores();
}

function isDemoMode() {
  return !state.token;
}

function getSelectedDemoReceipt() {
  return demoData.receipts.find((item) => item.receipt_id === state.selectedReceiptId) || null;
}

function buildDemoReceiptReport() {
  const groups = new Map();
  demoData.receipts.forEach((item) => {
    const key = `${item.status}::${item.supplier_reference || "Nao informado"}::${item.requires_approval ? "yes" : "no"}`;
    if (!groups.has(key)) {
      groups.set(key, {
        status: item.status,
        supplier_reference: item.supplier_reference || "Nao informado",
        requires_approval: item.requires_approval,
        pending_approval_receipts: 0,
        approved_receipts: 0,
        receipts: 0,
        total_quantity: 0,
        item_count: 0,
      });
    }
    const group = groups.get(key);
    group.receipts += 1;
    group.total_quantity += Number(item.total_quantity || 0);
    group.item_count += Number(item.item_count || 0);
    if (item.requires_approval) {
      if (item.approved_by) {
        group.approved_receipts += 1;
      } else {
        group.pending_approval_receipts += 1;
      }
    }
  });
  return Array.from(groups.values());
}

async function exportCsvFromApi({
  path,
  filename,
  onSuccess,
  onError,
  setStatusMessage,
}) {
  try {
    const response = await apiFetch(path);
    if (!response.ok) {
      let message = onError;
      try {
        const data = await response.json();
        message = data.detail || message;
      } catch {
        // Resposta nao-JSON: preserva a mensagem padrao.
      }
      setStatusMessage(message, "error");
      return false;
    }

    const blob = await response.blob();
    downloadBlob(filename, blob);
    setStatusMessage(onSuccess, "success");
    return true;
  } catch {
    setStatusMessage(onError, "error");
    return false;
  }
}

function buildReceiptSummaryPrintBody(data, rows, approvalHistory, heading) {
  return `
    <h1>${heading}</h1>
    <p><strong>Status:</strong> ${data.status}</p>
    <p><strong>Fornecedor:</strong> ${data.supplier_reference || "-"}</p>
    <p><strong>Documento:</strong> ${data.document_reference || "-"}</p>
    <p><strong>Motivo:</strong> ${data.reason || "-"}</p>
    <p><strong>Data:</strong> ${formatDateTime(data.created_at)}</p>
    <p><strong>Total:</strong> ${data.total_quantity} unidades</p>
    <p><strong>Aprovacao:</strong> ${data.requires_approval ? (data.approved_by ? `Aprovado por ${formatActorLabel(data.approved_by)}` : "Pendente") : "Nao exigida"}</p>
    <p><strong>Observacoes:</strong> ${data.notes || "-"}</p>
    <table>
      <thead>
        <tr><th>SKU</th><th>Produto</th><th>Quantidade</th></tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
    <h2>Historico de aprovacao</h2>
    ${approvalHistory ? `<ul>${approvalHistory}</ul>` : "<p>Sem eventos de aprovacao registrados.</p>"}
  `;
}

function formatReceiptAuditAction(action) {
  const labels = {
    draft_created: "Rascunho criado",
    draft_updated: "Rascunho atualizado",
    draft_approved: "Rascunho aprovado",
    draft_posted: "Rascunho efetivado",
    bulk_post_confirmed: "Efetivacao em lote confirmada",
    status_updated: "Status atualizado",
    receipt_canceled: "Recebimento cancelado",
    direct_receipt_created: "Recebimento direto registrado",
    batch_receipt_created: "Recebimento em lote registrado",
  };
  return labels[action] || action || "Evento registrado";
}

function savePreference(key, value) {
  localStorage.setItem(key, value ?? "");
}

function loadPreference(key, fallback = "") {
  return localStorage.getItem(key) ?? fallback;
}

function loadPreferenceBool(key, fallback = false) {
  const value = localStorage.getItem(key);
  if (value === null) {
    return fallback;
  }
  return value === "true";
}

function restorePreferences() {
  elements.dashboardDays.value = loadPreference(preferenceKeys.dashboardDays, elements.dashboardDays.value);
  elements.dashboardTopLimit.value = loadPreference(preferenceKeys.dashboardTopLimit, elements.dashboardTopLimit.value);
  elements.productQuery.value = loadPreference(preferenceKeys.productQuery);
  elements.skuQuery.value = loadPreference(preferenceKeys.skuQuery);
  elements.barcodeQuery.value = loadPreference(preferenceKeys.barcodeQuery);
  elements.movementTypeQuery.value = loadPreference(preferenceKeys.movementTypeQuery);
  elements.movementSupplierQuery.value = loadPreference(preferenceKeys.movementSupplierQuery);
  elements.movementDocumentQuery.value = loadPreference(preferenceKeys.movementDocumentQuery);
  elements.receiptStatusQuery.value = loadPreference(preferenceKeys.receiptStatusQuery);
  elements.draftReceiptsQuery.value = loadPreference(preferenceKeys.draftReceiptsQuery);
  state.draftReceiptsQuery = elements.draftReceiptsQuery.value;
  elements.receiptReportQuery.value = loadPreference(preferenceKeys.receiptReportQuery);
  state.receiptReportQuery = elements.receiptReportQuery.value;
  elements.receiptReportDateFrom.value = loadPreference(preferenceKeys.receiptReportDateFrom);
  elements.receiptReportDateTo.value = loadPreference(preferenceKeys.receiptReportDateTo);
  state.receiptReportDateFrom = elements.receiptReportDateFrom.value;
  state.receiptReportDateTo = elements.receiptReportDateTo.value;
  elements.draftReceiptsSensitiveOnly.checked = loadPreferenceBool(preferenceKeys.draftReceiptsSensitiveOnly);
  state.draftReceiptsSensitiveOnly = elements.draftReceiptsSensitiveOnly.checked;
  state.draftReceiptsCriticalOnly = loadPreferenceBool(preferenceKeys.draftReceiptsCriticalOnly);
  elements.draftReceiptsSort.value = loadPreference(preferenceKeys.draftReceiptsSort, elements.draftReceiptsSort.value);
  elements.movementDateFrom.value = loadPreference(preferenceKeys.movementDateFrom);
  elements.movementDateTo.value = loadPreference(preferenceKeys.movementDateTo);
  elements.receiptReportSort.value = loadPreference(preferenceKeys.receiptReportSort, elements.receiptReportSort.value);
  elements.receiptReportSensitiveOnly.checked = loadPreferenceBool(preferenceKeys.receiptReportSensitiveOnly);
  state.receiptReportSensitiveOnly = elements.receiptReportSensitiveOnly.checked;
  state.supplierRiskFilter = loadPreference(preferenceKeys.supplierRiskFilter);
  state.supplierRiskDateFrom = loadPreference(preferenceKeys.supplierRiskDateFrom);
  state.supplierRiskDateTo = loadPreference(preferenceKeys.supplierRiskDateTo);
  elements.salesVariantQuery.value = loadPreference(preferenceKeys.salesVariantQuery);
  elements.salesStatusQuery.value = loadPreference(preferenceKeys.salesStatusQuery);
  elements.salesDateFrom.value = loadPreference(preferenceKeys.salesDateFrom);
  elements.salesDateTo.value = loadPreference(preferenceKeys.salesDateTo);
}

function persistFilterPreferences() {
  savePreference(preferenceKeys.dashboardDays, elements.dashboardDays.value);
  savePreference(preferenceKeys.dashboardTopLimit, elements.dashboardTopLimit.value);
  savePreference(preferenceKeys.productQuery, elements.productQuery.value.trim());
  savePreference(preferenceKeys.skuQuery, elements.skuQuery.value.trim());
  savePreference(preferenceKeys.barcodeQuery, elements.barcodeQuery.value.trim());
  savePreference(preferenceKeys.movementTypeQuery, elements.movementTypeQuery.value.trim());
  savePreference(preferenceKeys.movementSupplierQuery, elements.movementSupplierQuery.value.trim());
  savePreference(preferenceKeys.movementDocumentQuery, elements.movementDocumentQuery.value.trim());
  savePreference(preferenceKeys.receiptStatusQuery, elements.receiptStatusQuery.value.trim());
  savePreference(preferenceKeys.draftReceiptsQuery, elements.draftReceiptsQuery.value.trim());
  savePreference(preferenceKeys.receiptReportQuery, elements.receiptReportQuery.value.trim());
  savePreference(preferenceKeys.receiptReportDateFrom, elements.receiptReportDateFrom.value);
  savePreference(preferenceKeys.receiptReportDateTo, elements.receiptReportDateTo.value);
  savePreference(preferenceKeys.draftReceiptsSensitiveOnly, String(elements.draftReceiptsSensitiveOnly.checked));
  savePreference(preferenceKeys.draftReceiptsCriticalOnly, String(state.draftReceiptsCriticalOnly));
  savePreference(preferenceKeys.draftReceiptsSort, elements.draftReceiptsSort.value);
  savePreference(preferenceKeys.movementDateFrom, elements.movementDateFrom.value);
  savePreference(preferenceKeys.movementDateTo, elements.movementDateTo.value);
  savePreference(preferenceKeys.receiptReportSort, elements.receiptReportSort.value);
  savePreference(preferenceKeys.receiptReportSensitiveOnly, String(elements.receiptReportSensitiveOnly.checked));
  savePreference(preferenceKeys.supplierRiskFilter, state.supplierRiskFilter.trim());
  savePreference(preferenceKeys.supplierRiskDateFrom, state.supplierRiskDateFrom);
  savePreference(preferenceKeys.supplierRiskDateTo, state.supplierRiskDateTo);
  savePreference(preferenceKeys.salesVariantQuery, elements.salesVariantQuery.value.trim());
  savePreference(preferenceKeys.salesStatusQuery, elements.salesStatusQuery.value.trim());
  savePreference(preferenceKeys.salesDateFrom, elements.salesDateFrom.value);
  savePreference(preferenceKeys.salesDateTo, elements.salesDateTo.value);
}

async function apiFetch(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (state.token) {
    headers.set("Authorization", `Bearer ${state.token}`);
  }
  return fetch(`${API_BASE_URL}${path}`, { ...options, headers });
}

async function loadHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    const data = await response.json();
    elements.healthStatus.textContent = data.status === "ok" ? "online" : "instavel";
  } catch {
    elements.healthStatus.textContent = "offline";
  }
}

function renderList(container, counter, items, formatter) {
  counter.textContent = String(items.length);
  if (!items.length) {
    container.innerHTML = '<div class="list-item"><span>Nenhum dado para exibir.</span></div>';
    return;
  }

  container.innerHTML = items.map(formatter).join("");
}

function formatCurrency(value) {
  const amount = Number(value || 0);
  return amount.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

function setScenarioStatus(message, tone = "muted") {
  elements.scenarioStatus.textContent = message;
  elements.scenarioStatus.className = `status ${tone}`;
}

function renderScenario(data) {
  elements.scenarioSummary.innerHTML = [["Política atual", data.total_current_policy_stockout], ["Regra simples", data.total_simple_rule_stockout], ["Modelo", data.total_model_stockout]].map(([label, value]) => `<div class="summary-card"><span>${label}</span><strong>${value}</strong><small>unidades em ruptura</small></div>`).join("");
  elements.scenarioList.innerHTML = data.items.map((item) => `<div class="list-item"><strong>${item.variant_id}</strong><span>Recomendação: ${item.recommended_quantity} unidades · ${formatCurrency(item.planned_cost)}</span><span>${item.explanation}</span></div>`).join("") || '<div class="list-item"><span>Nenhum item para simular.</span></div>';
}

async function runScenario() {
  if (!state.token) return setScenarioStatus("Entre para simular um cenário com dados reais.");
  const storeId = elements.storeFilter.value || state.currentUser?.store_id;
  if (!storeId) return setScenarioStatus("Selecione uma loja antes de simular.", "error");
  const budget = elements.scenarioBudget.value.trim();
  try {
    const response = await apiFetch("/scenarios/replenishment", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ store_id: storeId, demand_multiplier: Number(elements.scenarioDemandMultiplier.value || 1), supplier_delay_weeks: Number(elements.scenarioDelayWeeks.value || 0), ...(budget ? { budget_limit: Number(budget) } : {}) }) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Não foi possível simular o cenário.");
    renderScenario(data); setScenarioStatus("Cenário atualizado com os dados atuais da loja.", "success");
  } catch (error) { setScenarioStatus(error.message || "Falha de comunicação ao simular o cenário.", "error"); }
}

function setReplenishmentStatus(message, tone = "muted") {
  elements.replenishmentStatus.textContent = message;
  elements.replenishmentStatus.className = `status ${tone}`;
}

function renderReplenishment(items) {
  elements.replenishmentList.innerHTML = items.map((item) => `<div class="list-item"><strong>${item.variant_id}</strong><span>Atual: ${item.current_quantity} · Regra simples: ${item.simple_rule_quantity} · Modelo: ${item.recommended_quantity}</span><span>${item.explanation}</span><div class="action-row"><button type="button" class="ghost replenishment-decision" data-id="${item.id}" data-action="approved">Aprovar</button><button type="button" class="ghost replenishment-decision" data-id="${item.id}" data-action="rejected">Rejeitar</button><button type="button" class="ghost replenishment-decision" data-id="${item.id}" data-action="overridden">Ajustar</button></div></div>`).join("") || '<div class="list-item"><span>Nenhuma recomendação gerada.</span></div>';
}

async function runReplenishment() {
  if (!state.token) return setReplenishmentStatus("Entre para gerar recomendações com dados reais.");
  const storeId = elements.storeFilter.value || state.currentUser?.store_id;
  if (!storeId) return setReplenishmentStatus("Selecione uma loja antes de gerar recomendações.", "error");
  const budget = elements.replenishmentBudget.value.trim();
  try {
    const response = await apiFetch("/replenishment/recommendations/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ store_id: storeId, lead_time_weeks: Number(elements.replenishmentLeadTime.value || 2), minimum_stock: Number(elements.replenishmentMinimumStock.value || 0), ...(budget ? { budget_limit: Number(budget) } : {}) }) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Não foi possível gerar as recomendações.");
    renderReplenishment(data.items); setReplenishmentStatus("Recomendações atualizadas. Revise cada item antes de confirmar.", "success");
  } catch (error) { setReplenishmentStatus(error.message || "Falha de comunicação ao gerar recomendações.", "error"); }
}

async function decideReplenishment(button) {
  const status = button.dataset.action;
  let approvedQuantity;
  if (status === "overridden") {
    const value = window.prompt("Quantidade aprovada:");
    if (value === null) return;
    approvedQuantity = Number(value);
    if (!Number.isInteger(approvedQuantity) || approvedQuantity < 0) return setReplenishmentStatus("Informe uma quantidade inteira igual ou maior que zero.", "error");
  }
  try {
    const response = await apiFetch(`/replenishment/recommendations/${button.dataset.id}/decision`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status, ...(status === "overridden" ? { approved_quantity: approvedQuantity } : {}) }) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Não foi possível registrar a decisão.");
    setReplenishmentStatus(`Decisão registrada: ${data.status}.`, "success");
    await runReplenishment();
  } catch (error) { setReplenishmentStatus(error.message || "Falha de comunicação ao registrar a decisão.", "error"); }
}

function setSupplierIntelligenceStatus(message, tone = "muted") {
  elements.supplierIntelligenceStatus.textContent = message;
  elements.supplierIntelligenceStatus.className = `status ${tone}`;
}

function getSelectedStoreId() {
  return elements.storeFilter.value || state.currentUser?.store_id;
}

function renderSupplierRisk(items) {
  elements.supplierRiskList.innerHTML = items.map((item) => `<div class="list-item"><strong>${item.supplier_reference} · ${item.risk_level}</strong><span>Score: ${item.score} · ${item.delivery_count} entrega(s)</span><span>${item.explanation}</span></div>`).join("") || '<div class="list-item"><span>Nenhum risco calculado para esta loja.</span></div>';
}

async function refreshSupplierRisk() {
  if (!state.token) return setSupplierIntelligenceStatus("Entre para consultar riscos reais.");
  const storeId = getSelectedStoreId();
  if (!storeId) return setSupplierIntelligenceStatus("Selecione uma loja antes de atualizar o ranking.", "error");
  try {
    const scored = await apiFetch("/supplier-intelligence/scores/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ store_id: storeId }) });
    const data = await scored.json();
    if (!scored.ok) throw new Error(data.detail || "Não foi possível calcular o risco.");
    renderSupplierRisk(data.items); setSupplierIntelligenceStatus("Ranking atualizado com base nas entregas registradas.", "success");
  } catch (error) { setSupplierIntelligenceStatus(error.message || "Falha de comunicação ao atualizar o ranking.", "error"); }
}

async function saveSupplierDelivery() {
  const storeId = getSelectedStoreId();
  const received = Number(elements.supplierReceivedQuantity.value || 0);
  if (!state.token) return setSupplierIntelligenceStatus("Entre para registrar entregas reais.");
  if (!storeId || !elements.supplierReference.value.trim() || !elements.supplierOrderedAt.value || !elements.supplierExpectedAt.value || !elements.supplierDeliveredAt.value || received <= 0) return setSupplierIntelligenceStatus("Preencha fornecedor, datas e quantidade recebida.", "error");
  try {
    const response = await apiFetch("/supplier-intelligence/deliveries", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ store_id: storeId, supplier_reference: elements.supplierReference.value.trim(), ordered_at: elements.supplierOrderedAt.value, expected_at: elements.supplierExpectedAt.value, delivered_at: elements.supplierDeliveredAt.value, ordered_quantity: received, received_quantity: received, defective_quantity: Number(elements.supplierDefectiveQuantity.value || 0), purchase_cost: Number(elements.supplierPurchaseCost.value || 0) }) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Não foi possível registrar a entrega.");
    setSupplierIntelligenceStatus("Entrega registrada. Atualize o ranking para recalcular o risco.", "success");
  } catch (error) { setSupplierIntelligenceStatus(error.message || "Falha de comunicação ao registrar a entrega.", "error"); }
}

function getOperationIdempotencyKey(stateField) {
  if (!state[stateField]) {
    state[stateField] = window.crypto?.randomUUID?.()
      || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }
  return state[stateField];
}

function buildVariantOptionLabel(variant, suffix = "") {
  const parts = [variant.sku, getProductName(variant.product_id), formatCurrency(variant.sale_price)];
  if (suffix) {
    parts.push(suffix);
  }
  return parts.join(" - ");
}

function buildPagerStatusLabel(currentPage, pageCount, total, noun) {
  return `Pagina ${currentPage} de ${pageCount} - ${total} ${noun}`;
}

function buildSupplierSnapshotLabel(supplierReference, snapshotDate) {
  return `${supplierReference} - ${formatDateTime(snapshotDate)}`;
}

function getDraftAgeHours(dateValue) {
  const createdAt = new Date(dateValue);
  if (Number.isNaN(createdAt.getTime())) {
    return 0;
  }
  return Math.max(0, (Date.now() - createdAt.getTime()) / 36e5);
}

function getSupplierTargetHours(supplierReference) {
  return state.supplierRiskTargets.find((item) => item.supplier_reference === (supplierReference || "Nao informado"))?.target_hours || 48;
}

function getDraftSlaMeta(item) {
  const targetHours = getSupplierTargetHours(item.supplier_reference || "Nao informado");
  const hours = getDraftAgeHours(item.created_at);
  if (hours >= targetHours) {
    return { label: `SLA critico (${Math.floor(hours)}h)`, level: "critical" };
  }
  if (hours >= Math.max(1, targetHours / 2)) {
    return { label: `SLA atencao (${Math.floor(hours)}h)`, level: "warning" };
  }
  return { label: `SLA ok (${Math.floor(hours)}h)`, level: "ok" };
}

function isCriticalDraft(item) {
  return getDraftSlaMeta(item).level === "critical";
}

function getDraftTimeToBreachLabel(item) {
  const targetHours = getSupplierTargetHours(item.supplier_reference || "Nao informado");
  const hours = getDraftAgeHours(item.created_at);
  if (hours >= targetHours) {
    return `Violado ha ${Math.floor(hours - targetHours)}h`;
  }
  const remaining = Math.max(0, targetHours - hours);
  if (remaining < 1) {
    return "Vence em menos de 1h";
  }
  return `Vence em ${Math.ceil(remaining)}h`;
}

function exportSupplierRiskCsv(items) {
  const rows = buildCsvRows(
    ["supplier", "pending", "critical"],
    items,
    (item) => [item.supplier, String(item.pending), String(item.critical)],
  );
  downloadCsv("supplier-risk.csv", rows);
}

async function exportSupplierRiskHistoryCsv() {
  const params = new URLSearchParams();
  const selectedStore = selectedStoreId();
  if (selectedStore) {
    params.set("store_id", selectedStore);
  }
  if (state.supplierRiskFilter.trim()) {
    params.set("supplier_reference", state.supplierRiskFilter.trim());
  }
  if (state.supplierRiskDateFrom) {
    params.set("created_from", state.supplierRiskDateFrom);
  }
  if (state.supplierRiskDateTo) {
    params.set("created_to", state.supplierRiskDateTo);
  }
  await exportCsvFromApi({
    path: `/inventory/supplier-risk-history/export?${params}`,
    filename: "supplier-risk-history.csv",
    onSuccess: "Historico analitico de risco exportado em CSV.",
    onError: "Nao foi possivel exportar o historico analitico de risco.",
    setStatusMessage: setEntryStatus,
  });
}

function exportSupplierRiskDetailsCsv(supplier, drafts) {
  const rows = buildCsvRows(
    ["supplier", "document_reference", "receipt_id", "created_at", "total_quantity", "item_count", "critical"],
    drafts,
    (item) => [
      supplier,
      item.document_reference || "",
      item.receipt_id,
      item.created_at,
      String(item.total_quantity),
      String(item.item_count),
      isCriticalDraft(item) ? "true" : "false",
    ],
  );
  downloadCsv(`supplier-risk-details-${supplier.replaceAll(" ", "-").toLowerCase()}.csv`, rows);
}

function printSupplierRiskSummary(supplier, drafts) {
  const criticalDrafts = drafts.filter((item) => isCriticalDraft(item));
  const targetHours = getSupplierTargetHours(supplier);
  const rows = drafts.map((item) => `
    <tr>
      <td>${item.document_reference || "-"}</td>
      <td>${formatDateTime(item.created_at)}</td>
      <td>${item.total_quantity}</td>
      <td>${getDraftSlaMeta(item).label}</td>
      <td>${getDraftTimeToBreachLabel(item)}</td>
    </tr>
  `).join("");

  const opened = openPrintDocument(buildPrintHtmlDocument(
    "Resumo operacional de risco por fornecedor",
    `
      <h1>Resumo operacional de risco por fornecedor</h1>
      <p><strong>Fornecedor:</strong> ${supplier}</p>
      <p><strong>Pendentes:</strong> ${drafts.length}</p>
      <p><strong>Criticos:</strong> ${criticalDrafts.length}</p>
      <p><strong>SLA alvo:</strong> ${targetHours}h</p>
      <p><strong>Gerado em:</strong> ${new Date().toLocaleString("pt-BR")}</p>
      <table>
        <thead>
          <tr>
            <th>Documento</th>
            <th>Data</th>
            <th>Quantidade</th>
            <th>SLA</th>
            <th>Prazo</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
      <h2>Documentos criticos</h2>
      ${criticalDrafts.length ? `<ul>${criticalDrafts.map((item) => `<li>${item.document_reference || item.receipt_id} - ${getDraftTimeToBreachLabel(item)}</li>`).join("")}</ul>` : "<p>Sem documentos criticos neste fornecedor.</p>"}
    `,
    { listMarginTop: 12 },
  ), { width: 960, height: 720 });
  if (!opened) {
    setEntryStatus("Nao foi possivel abrir a janela do resumo de risco.", "error");
    return;
  }
}

function printSupplierRiskHistorySummary(historyItems) {
  const rows = historyItems.map((item) => `
    <tr>
      <td>${item.label}</td>
      <td>${item.openCritical}</td>
      <td>${item.resolvedEstimate}</td>
    </tr>
  `).join("");

  const opened = openPrintDocument(buildPrintHtmlDocument(
    "Historico analitico de risco",
    `
      <h1>Historico analitico de risco</h1>
      <p>Periodo: ${state.supplierRiskDateFrom || "-"} ate ${state.supplierRiskDateTo || "-"}</p>
      <p>Gerado em: ${new Date().toLocaleString("pt-BR")}</p>
      <table>
        <thead>
          <tr>
            <th>Faixa</th>
            <th>Criticos abertos</th>
            <th>Resolvidos estimados</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    `,
  ), { width: 900, height: 680 });
  if (!opened) {
    setEntryStatus("Nao foi possivel abrir a janela do historico analitico de risco.", "error");
    return;
  }
}

function getSupplierPriorityLevel(item) {
  if (item.critical > 0) {
    return { label: "Prioridade critica de atendimento", level: "critical" };
  }
  if (item.pending > 2) {
    return { label: "Prioridade em atencao", level: "warning" };
  }
  return { label: "Prioridade dentro do SLA", level: "ok" };
}

function renderDashboardSummary(data) {
  const cards = [
    {
      label: "Receita liquida no periodo",
      value: formatCurrency(data.sales.net_revenue),
      meta: `${data.sales.completed_count} vendas concluidas na janela atual`,
    },
    {
      label: "Itens vendidos no periodo",
      value: String(data.sales.items_sold),
      meta: `${data.sales.canceled_count} vendas canceladas no mesmo intervalo`,
    },
    {
      label: "Estoque disponivel",
      value: String(data.inventory.total_on_hand_qty),
      meta: `${data.inventory.tracked_variants} variantes monitoradas no painel`,
    },
    {
      label: "Variantes em atencao",
      value: String(data.inventory.low_stock_variants + data.inventory.out_of_stock_variants),
      meta: `${data.inventory.out_of_stock_variants} sem saldo e ${data.inventory.low_stock_variants} com baixa cobertura`,
    },
  ];

  elements.dashboardSummary.innerHTML = cards.map((card) => `
    <div class="summary-card">
      <span>${card.label}</span>
      <strong>${card.value}</strong>
      <small>${card.meta}</small>
    </div>
  `).join("");
}

function renderDailySales(points) {
  elements.dailySalesCount.textContent = String(points.length);
  if (!points.length) {
    elements.dailySalesChart.innerHTML = '<div class="list-item"><span>Nao ha vendas consolidadas para exibir neste periodo.</span></div>';
    return;
  }

  const maxRevenue = Math.max(...points.map((point) => Number(point.net_revenue || 0)), 0);
  elements.dailySalesChart.innerHTML = points.map((point) => {
    const value = Number(point.net_revenue || 0);
    const height = maxRevenue > 0 ? Math.max(24, Math.round((value / maxRevenue) * 160)) : 24;
    const label = new Date(`${point.date}T00:00:00`).toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
    });
    return `
      <div class="chart-bar">
        <div class="chart-value">${formatCurrency(point.net_revenue)}</div>
        <div class="chart-column ${value === 0 ? "is-empty" : ""}" style="height: ${height}px"></div>
        <div class="chart-label">${label}</div>
      </div>
    `;
  }).join("");
}

function renderTopVariants(items) {
  renderList(elements.topVariantsList, elements.topVariantsCount, items, (item, index) => `
    <div class="list-item rank-item">
      <span class="rank-badge">${index + 1}</span>
      <div class="rank-meta">
        <strong>${item.product_name}</strong>
        <span>${item.sku}</span>
      </div>
      <div class="rank-metrics">
        <strong>${item.quantity_sold} un.</strong>
        <span>${formatCurrency(item.net_revenue)}</span>
      </div>
    </div>
  `);
}

function renderExecutiveStrip(data, sales, counts) {
  const latestSale = sales[0] || null;
  const openCount = counts.find((item) => item.status === "open") || null;
  const highlights = [
    {
      label: "Receita da janela",
      value: formatCurrency(data.sales.net_revenue),
      meta: `${data.sales.completed_count} vendas concluidas no periodo`,
    },
    {
      label: "Ultima venda",
      value: latestSale ? formatCurrency(latestSale.total_amount) : "Sem vendas",
      meta: latestSale ? `${state.stores.find((store) => store.id === latestSale.store_id)?.name || latestSale.store_id} - ${formatDateTime(latestSale.sold_at)}` : "Aguardando movimentacao",
    },
    {
      label: "Contagem ativa",
      value: openCount ? openCount.scope : "Nenhuma aberta",
      meta: openCount ? `${state.stores.find((store) => store.id === openCount.store_id)?.name || openCount.store_id} - ${openCount.items.length} itens registrados` : "Fluxo sem pendencias no momento",
    },
  ];

  elements.executiveStrip.innerHTML = highlights.map((item) => `
    <article class="executive-card">
      <span>${item.label}</span>
      <strong>${item.value}</strong>
      <small>${item.meta}</small>
    </article>
  `).join("");
}

function formatDateTime(value) {
  return new Date(value).toLocaleString("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

function formatActorLabel(value) {
  if (!value) {
    return "sistema";
  }
  const actor = String(value);
  if (actor.includes("@")) {
    return actor;
  }
  return actor.length > 10 ? `${actor.slice(0, 8)}...` : actor;
}

function updateSelectOptions(select, items, formatter, emptyLabel = "Selecione") {
  const currentValue = select.value;
  select.innerHTML = [`<option value="">${emptyLabel}</option>`]
    .concat(items.map((item) => `<option value="${item.id}">${formatter(item)}</option>`))
    .join("");
  if (items.some((item) => item.id === currentValue)) {
    select.value = currentValue;
  } else if (items.length === 1) {
    select.value = items[0].id;
  }
}

function getProductName(productId) {
  return state.productsById.get(productId)?.name || "Produto";
}

function variantLabel(variant) {
  return buildVariantOptionLabel(variant);
}

function selectedStoreId() {
  return elements.storeFilter.value.trim() || "";
}

function applyCurrentStoreTo(select, preferenceKey) {
  const storeId = selectedStoreId();
  if (!storeId) {
    return;
  }
  select.value = storeId;
  savePreference(preferenceKey, storeId);
}

function filterVariantsByQuery(query) {
  const search = query.trim().toLowerCase();
  if (!search) {
    return state.variants;
  }

  return state.variants.filter((variant) => {
    const productName = getProductName(variant.product_id).toLowerCase();
    return variant.sku.toLowerCase().includes(search) || productName.includes(search);
  });
}

function hydrateHelperOptions(stores, variants, products) {
  state.stores = stores;
  state.variants = variants;
  state.productsById = new Map(products.map((product) => [product.id, product]));

  updateSelectOptions(elements.transferSourceStore, stores, (item) => item.name, "Selecione a origem");
  updateSelectOptions(elements.transferDestinationStore, stores, (item) => item.name, "Selecione o destino");
  updateSelectOptions(elements.adjustmentStore, stores, (item) => item.name, "Selecione a loja");
  updateSelectOptions(elements.entryStore, stores, (item) => item.name, "Selecione a loja");
  updateSelectOptions(elements.saleStore, stores, (item) => item.name, "Selecione a loja");
  updateSelectOptions(elements.countStore, stores, (item) => item.name, "Selecione a loja");
  updateSelectOptions(elements.countVariant, variants, variantLabel, "Selecione a variante");
  updateSelectOptions(elements.storeFilter, stores, (item) => item.name, "Todas / minha loja");

  elements.storeFilter.value = loadPreference(preferenceKeys.storeFilter, elements.storeFilter.value);
  elements.transferSourceStore.value = loadPreference(preferenceKeys.transferSourceStore, elements.transferSourceStore.value);
  elements.transferDestinationStore.value = loadPreference(preferenceKeys.transferDestinationStore, elements.transferDestinationStore.value);
  elements.saleStore.value = loadPreference(preferenceKeys.saleStore, elements.saleStore.value);
  elements.countStore.value = loadPreference(preferenceKeys.countStore, elements.countStore.value);
}

function setBalances(balances) {
  state.balances = balances;
}

function getBalanceFor(storeId, variantId) {
  return state.balances.find((balance) => balance.store_id === storeId && balance.variant_id === variantId) || null;
}

function variantsForStore(storeId) {
  if (!storeId) {
    return state.variants;
  }
  const variantIds = new Set(
    state.balances
      .filter((balance) => balance.store_id === storeId)
      .map((balance) => balance.variant_id)
  );
  return state.variants.filter((variant) => variantIds.has(variant.id));
}

function refreshTransferVariantOptions() {
  const sourceStoreId = elements.transferSourceStore.value;
  const availableVariants = variantsForStore(sourceStoreId);
  updateSelectOptions(elements.transferVariant, availableVariants, (variant) => {
    const balance = getBalanceFor(sourceStoreId, variant.id);
    return buildVariantOptionLabel(variant, `saldo ${balance?.on_hand_qty ?? 0}`);
  }, "Selecione a variante");
}

function refreshCountVariantOptions() {
  const storeId = elements.countStore.value;
  const availableVariants = variantsForStore(storeId);
  updateSelectOptions(elements.countVariant, availableVariants, (variant) => {
    const balance = getBalanceFor(storeId, variant.id);
    return buildVariantOptionLabel(variant, `sistema ${balance?.on_hand_qty ?? 0}`);
  }, "Selecione a variante");
}

function refreshAdjustmentVariantOptions() {
  const storeId = elements.adjustmentStore.value;
  const availableVariants = variantsForStore(storeId);
  updateSelectOptions(elements.adjustmentVariant, availableVariants, (variant) => {
    const balance = getBalanceFor(storeId, variant.id);
    return buildVariantOptionLabel(variant, `saldo ${balance?.on_hand_qty ?? 0}`);
  }, "Selecione a variante");
}

function refreshEntryVariantOptions() {
  const storeId = elements.entryStore.value;
  const availableVariants = variantsForStore(storeId);
  const values = Array.from(elements.entryItems.children).map((row) => ({
    variant_id: row.querySelector(".entry-item-variant").value,
    quantity: row.querySelector(".entry-item-quantity").value,
  }));
  elements.entryItems.innerHTML = "";
  values.forEach((value) => {
    elements.entryItems.appendChild(createEntryItemRow(value, availableVariants));
  });
}

function renderTransferPreview() {
  const sourceStoreId = elements.transferSourceStore.value;
  const destinationStoreId = elements.transferDestinationStore.value;
  const variantId = elements.transferVariant.value;
  if (!sourceStoreId || !destinationStoreId || !variantId) {
    elements.transferPreview.className = "inline-card empty-state";
    elements.transferPreview.innerHTML = "Selecione origem, destino e variante para ver o saldo antes da transferencia.";
    return;
  }

  const source = getBalanceFor(sourceStoreId, variantId);
  const destination = getBalanceFor(destinationStoreId, variantId);
  elements.transferPreview.className = "inline-card";
  elements.transferPreview.innerHTML = `
    <div class="preview-grid">
      <div>
        <strong>${state.stores.find((store) => store.id === sourceStoreId)?.name || "Origem"}</strong>
        <span>Saldo atual: ${source?.on_hand_qty ?? 0}</span>
      </div>
      <div>
        <strong>${state.stores.find((store) => store.id === destinationStoreId)?.name || "Destino"}</strong>
        <span>Saldo atual: ${destination?.on_hand_qty ?? 0}</span>
      </div>
    </div>
  `;
}

function renderCountPreview() {
  const storeId = elements.countStore.value;
  const variantId = elements.countVariant.value;
  const countedQuantity = Number(elements.countQuantity.value || 0);
  if (!storeId || !variantId) {
    elements.countPreview.className = "inline-card empty-state";
    elements.countPreview.innerHTML = "Selecione loja, variante e quantidade para ver o saldo atual e a diferenca prevista.";
    return;
  }

  const balance = getBalanceFor(storeId, variantId);
  const systemQty = balance?.on_hand_qty ?? 0;
  const diff = countedQuantity - systemQty;
  elements.countPreview.className = "inline-card";
  elements.countPreview.innerHTML = `
    <div class="preview-grid">
      <div>
        <strong>Sistema</strong>
        <span>${systemQty} unidades</span>
      </div>
      <div>
        <strong>Diferenca prevista</strong>
        <span>${diff > 0 ? "+" : ""}${diff} unidades</span>
      </div>
    </div>
  `;
}

function renderAdjustmentPreview() {
  const storeId = elements.adjustmentStore.value;
  const variantId = elements.adjustmentVariant.value;
  if (!storeId || !variantId) {
    elements.adjustmentPreview.className = "inline-card empty-state";
    elements.adjustmentPreview.innerHTML = "Selecione loja e variante para revisar o saldo atual antes de aplicar o ajuste.";
    return;
  }

  const balance = getBalanceFor(storeId, variantId);
  const targetQty = Number(elements.adjustmentQuantity.value || 0);
  const currentQty = balance?.on_hand_qty ?? 0;
  const delta = targetQty - currentQty;

  elements.adjustmentPreview.className = "inline-card";
  elements.adjustmentPreview.innerHTML = `
    <div class="preview-grid">
      <div>
        <strong>Saldo atual</strong>
        <span>${currentQty} unidades</span>
      </div>
      <div>
        <strong>Delta previsto</strong>
        <span>${delta > 0 ? "+" : ""}${delta} unidades</span>
      </div>
    </div>
  `;
}

function renderEntryPreview() {
  const storeId = elements.entryStore.value;
  const payload = getEntryPayload();
  if (!storeId || !payload.items.length || payload.items.every((item) => !item.variant_id)) {
    elements.entryPreview.className = "inline-card empty-state";
    elements.entryPreview.innerHTML = "Selecione loja e itens para revisar o saldo projetado antes de registrar a entrada.";
    return;
  }

  const totals = payload.items.reduce((sum, item) => sum + Number(item.quantity || 0), 0);
  const impacted = payload.items
    .filter((item) => item.variant_id)
    .map((item) => {
      const balance = getBalanceFor(storeId, item.variant_id);
      const variant = state.variants.find((entry) => entry.id === item.variant_id);
      const currentQty = balance?.on_hand_qty ?? 0;
      const projectedQty = currentQty + Number(item.quantity || 0);
      return `<span>${variant?.sku || item.variant_id}: ${currentQty} -> ${projectedQty}</span>`;
    })
    .join("");

  elements.entryPreview.className = "inline-card";
  elements.entryPreview.innerHTML = `
    <div class="preview-grid">
      <div>
        <strong>Itens no recebimento</strong>
        <span>${payload.items.filter((item) => item.variant_id).length} variantes, ${totals} unidades</span>
      </div>
      <div>
        <strong>Saldos projetados</strong>
        ${impacted}
      </div>
    </div>
  `;
}

function applyReceiptReference(reference) {
  elements.entrySupplierReference.value = reference.supplier_reference || "";
  elements.entryDocumentReference.value = reference.document_reference || "";
  elements.entryReason.value = reference.reason || elements.entryReason.value;
  renderEntryPreview();
  setEntryStatus("Referencia recente aplicada ao recebimento em preparacao.", "muted");
}

function renderReceiptReferenceSuggestions(items) {
  state.receiptReferences = items;
  if (!items.length) {
    elements.entryReferenceSuggestions.innerHTML =
      '<div class="inline-card empty-state">Os ultimos recebimentos referenciados aparecerao aqui.</div>';
    return;
  }

  elements.entryReferenceSuggestions.innerHTML = items.map((item, index) => `
    <div class="inline-card reference-card" data-reference-index="${index}">
      <div class="reference-card-head">
        <strong>${item.supplier_reference || "Fornecedor nao informado"}</strong>
        <span>${formatDateTime(item.created_at)}</span>
      </div>
      <div class="reference-card-meta">
        <span>Documento: ${item.document_reference || "Nao informado"}</span>
        <span>Motivo base: ${item.reason || "Nao informado"}</span>
        <span>${item.item_count} itens com ${item.total_quantity} unidades</span>
      </div>
      <button type="button" class="ghost apply-reference-button" data-reference-index="${index}">Usar referencia</button>
    </div>
  `).join("");

  document.querySelectorAll(".apply-reference-button").forEach((button) => {
    button.addEventListener("click", () => {
      const reference = state.receiptReferences[Number(button.dataset.referenceIndex)];
      if (reference) {
        applyReceiptReference(reference);
      }
    });
  });
}

function createEntryItemRow(prefill = {}, availableVariants = variantsForStore(elements.entryStore.value)) {
  const row = document.createElement("div");
  row.className = "inline-card";
  row.innerHTML = `
    <div class="inline-grid">
      <label>
        Variante
        <select class="entry-item-variant" required></select>
      </label>
      <label>
        Quantidade
        <input class="entry-item-quantity" type="number" min="1" value="${prefill.quantity || 1}" required>
      </label>
      <button type="button" class="ghost remove-entry-item">Remover</button>
    </div>
  `;

  const select = row.querySelector(".entry-item-variant");
  select.innerHTML = [`<option value="">Selecione a variante</option>`]
    .concat(
      availableVariants.map((variant) => {
        const balance = getBalanceFor(elements.entryStore.value, variant.id);
        return `<option value="${variant.id}">${buildVariantOptionLabel(variant, `saldo ${balance?.on_hand_qty ?? 0}`)}</option>`;
      })
    )
    .join("");

  if (prefill.variant_id) {
    select.value = prefill.variant_id;
  }

  row.querySelector(".remove-entry-item").addEventListener("click", () => {
    row.remove();
    if (!elements.entryItems.children.length) {
      elements.entryItems.appendChild(createEntryItemRow());
    }
    renderEntryPreview();
  });
  select.addEventListener("change", renderEntryPreview);
  row.querySelector(".entry-item-quantity").addEventListener("input", renderEntryPreview);
  return row;
}

function getEntryPayload() {
  return {
    store_id: elements.entryStore.value,
    supplier_reference: elements.entrySupplierReference.value.trim() || null,
    document_reference: elements.entryDocumentReference.value.trim() || null,
    reason: elements.entryReason.value.trim(),
    notes: elements.entryNotes.value.trim() || null,
    items: Array.from(elements.entryItems.querySelectorAll(".inline-card")).map((row) => ({
      variant_id: row.querySelector(".entry-item-variant").value,
      quantity: Number(row.querySelector(".entry-item-quantity").value),
    })),
  };
}

function renderSaleSummary() {
  const payload = getSalePayload();
  if (!payload.store_id || !payload.items.length || payload.items.every((item) => !item.variant_id)) {
    elements.saleSummary.className = "inline-card empty-state";
    elements.saleSummary.innerHTML = "Selecione loja e itens para revisar subtotal, desconto e alertas de saldo antes de concluir.";
    return;
  }

  const subtotal = payload.items.reduce((sum, item) => sum + (Number(item.quantity || 0) * Number(item.unit_price || 0)), 0);
  const discount = Number(payload.discount_amount || 0);
  const total = Math.max(subtotal - discount, 0);
  const warnings = payload.items
    .filter((item) => item.variant_id)
    .map((item) => {
      const balance = getBalanceFor(payload.store_id, item.variant_id);
      const available = balance?.on_hand_qty ?? 0;
      if (Number(item.quantity || 0) > available) {
        const variant = state.variants.find((entry) => entry.id === item.variant_id);
        return `${variant?.sku || item.variant_id}: solicitado ${item.quantity}, saldo ${available}`;
      }
      return "";
    })
    .filter(Boolean);

  elements.saleSummary.className = "inline-card";
  elements.saleSummary.innerHTML = `
    <div class="preview-grid sale-summary-grid">
      <div>
        <strong>Subtotal</strong>
        <span>${formatCurrency(subtotal)}</span>
      </div>
      <div>
        <strong>Desconto</strong>
        <span>${formatCurrency(discount)}</span>
      </div>
      <div>
        <strong>Total previsto</strong>
        <span>${formatCurrency(total)}</span>
      </div>
      <div>
        <strong>Itens na venda</strong>
        <span>${payload.items.reduce((sum, item) => sum + Number(item.quantity || 0), 0)} unidades</span>
      </div>
    </div>
    <div class="context-note ${warnings.length ? "warning" : ""}">
      ${warnings.length ? `Atencao de saldo: ${warnings.join(" | ")}` : "Saldos aparentam suficientes para os itens preenchidos."}
    </div>
  `;
}

function renderOperationContext(dashboard, counts) {
  if (!state.token) {
    elements.operationContext.className = "inline-card empty-state";
    elements.operationContext.innerHTML = "Selecione uma loja no painel para ver o contexto operacional consolidado desta sessao.";
    return;
  }

  const storeId = selectedStoreId();
  const storeName = state.stores.find((store) => store.id === storeId)?.name || "Todas / minha loja";
  const openCount = counts.find((count) => count.status === "open") || null;
  const draftReceipts = state.receipts.filter((item) => item.status === "draft").length;
  const checkedReceipts = state.receipts.filter((item) => item.status === "checked").length;
  const sensitivePendingDrafts = state.receipts
    .filter((item) => item.status === "draft" && item.requires_approval && !item.approved_by);
  const criticalSensitiveDrafts = sensitivePendingDrafts.filter((item) => getDraftAgeHours(item.created_at) >= 48).length;
  const warningSensitiveDrafts = sensitivePendingDrafts.filter((item) => {
    const ageHours = getDraftAgeHours(item.created_at);
    return ageHours >= 24 && ageHours < 48;
  }).length;
  const okSensitiveDrafts = sensitivePendingDrafts.length - criticalSensitiveDrafts - warningSensitiveDrafts;
  const targetMap = new Map(state.supplierRiskTargets.map((item) => [item.supplier_reference, item.target_hours]));
  const pendingBySupplier = sensitivePendingDrafts.reduce((acc, item) => {
    const key = item.supplier_reference || "Nao informado";
    if (!acc[key]) {
      acc[key] = { supplier: key, pending: 0, critical: 0, targetHours: targetMap.get(key) || 48 };
    }
    acc[key].pending += 1;
    if (isCriticalDraft(item)) {
      acc[key].critical += 1;
    }
    return acc;
  }, {});
  const filteredSupplierTerm = state.supplierRiskFilter.trim().toLowerCase();
  const filteredSuppliers = Object.values(pendingBySupplier)
    .filter((item) => !filteredSupplierTerm || item.supplier.toLowerCase().includes(filteredSupplierTerm))
    .sort((a, b) => (b.critical - a.critical) || (b.pending - a.pending) || a.supplier.localeCompare(b.supplier));
  const supplierPageCount = Math.max(1, Math.ceil(filteredSuppliers.length / state.supplierRiskPageSize));
  state.supplierRiskPage = Math.min(state.supplierRiskPage, supplierPageCount - 1);
  const pagedSuppliers = filteredSuppliers.slice(
    state.supplierRiskPage * state.supplierRiskPageSize,
    (state.supplierRiskPage + 1) * state.supplierRiskPageSize
  );
  const riskHistory = state.supplierRiskHistory.length ? state.supplierRiskHistory.slice(0, 3).map((item) => ({
    label: buildSupplierSnapshotLabel(item.supplier_reference, item.snapshot_date),
    openCritical: item.open_critical_count,
    resolvedEstimate: item.resolved_estimate_count,
  })) : [
    {
      label: "Inicio do periodo",
      openCritical: sensitivePendingDrafts.filter((item) => getDraftAgeHours(item.created_at) >= 72).length,
      resolvedEstimate: Math.max(0, sensitivePendingDrafts.length - sensitivePendingDrafts.filter((item) => getDraftAgeHours(item.created_at) >= 72).length),
    },
    {
      label: "Meio do periodo",
      openCritical: sensitivePendingDrafts.filter((item) => getDraftAgeHours(item.created_at) >= 48).length,
      resolvedEstimate: Math.max(0, sensitivePendingDrafts.length - sensitivePendingDrafts.filter((item) => getDraftAgeHours(item.created_at) >= 48).length),
    },
    {
      label: "Agora",
      openCritical: criticalSensitiveDrafts,
      resolvedEstimate: Math.max(0, warningSensitiveDrafts + okSensitiveDrafts),
    },
  ];

  elements.operationContext.className = "inline-card";
  elements.operationContext.innerHTML = `
    <div class="preview-grid">
      <div>
        <strong>Escopo atual</strong>
        <span>${storeName}</span>
      </div>
      <div>
        <strong>Receita da janela</strong>
        <span>${formatCurrency(dashboard.sales.net_revenue)}</span>
      </div>
      <div>
        <strong>Estoque em atencao</strong>
        <span>${dashboard.inventory.low_stock_variants + dashboard.inventory.out_of_stock_variants} variantes com cobertura reduzida</span>
      </div>
      <div>
        <strong>Contagem aberta</strong>
        <span>${openCount ? `${openCount.scope} em ${formatDateTime(openCount.created_at)}` : "Nenhuma contagem aberta"}</span>
      </div>
      <div>
        <strong>Rascunhos pendentes</strong>
        <span>${draftReceipts} documentos</span>
      </div>
      <div>
        <strong>Conferidos aguardando</strong>
        <span>${checkedReceipts} documentos aguardando o proximo passo</span>
      </div>
      <div>
        <strong>Sensiveis pendentes</strong>
        <span>${sensitivePendingDrafts.length} documentos</span>
      </div>
      <div>
        <strong>Alerta operacional</strong>
        <span>${criticalSensitiveDrafts ? `${criticalSensitiveDrafts} criticos` : warningSensitiveDrafts ? `${warningSensitiveDrafts} em atencao` : "Sem pendencias criticas"}</span>
      </div>
    </div>
    <div class="sla-overview">
      <div class="sla-overview-card is-ok">
        <strong>${okSensitiveDrafts}</strong>
        <span>Dentro do SLA</span>
      </div>
      <div class="sla-overview-card is-warning">
        <strong>${warningSensitiveDrafts}</strong>
        <span>Em atencao</span>
      </div>
      <div class="sla-overview-card is-critical">
        <strong>${criticalSensitiveDrafts}</strong>
        <span>Critico</span>
      </div>
    </div>
    <div class="filter-section analytic-section supplier-risk-analytic-section">
      <div class="eyebrow">Analise de risco por fornecedor</div>
      <div class="supplier-risk-controls analytic-controls">
        <input id="supplier-risk-filter" type="text" placeholder="Filtrar fornecedor no risco" value="${state.supplierRiskFilter}">
        <input id="supplier-risk-date-from" type="date" value="${state.supplierRiskDateFrom}">
        <input id="supplier-risk-date-to" type="date" value="${state.supplierRiskDateTo}">
        <button id="export-supplier-risk-button" type="button" class="ghost">Exportar risco CSV</button>
        <button id="export-supplier-risk-history-button" type="button" class="ghost">Exportar historico</button>
        <button id="print-supplier-risk-history-button" type="button" class="ghost">Imprimir historico</button>
      </div>
    </div>
    <div class="supplier-risk-list">
      ${pagedSuppliers.length ? pagedSuppliers.map((item) => `
        <div class="supplier-risk-card supplier-priority-${getSupplierPriorityLevel(item).level}" data-risk-supplier="${encodeURIComponent(item.supplier)}">
          <strong>${item.supplier}</strong>
          <span class="supplier-priority-tag is-${getSupplierPriorityLevel(item).level}">${getSupplierPriorityLevel(item).label}</span>
          <span>${item.pending} documentos pendentes</span>
          <span>${item.critical} documentos criticos</span>
          <span>SLA alvo: ${item.targetHours}h</span>
          <button type="button" class="ghost select-risk-supplier-button" data-risk-select-supplier="${encodeURIComponent(item.supplier)}">Selecionar rascunhos</button>
          <button type="button" class="ghost approve-risk-supplier-button" data-risk-approve-supplier="${encodeURIComponent(item.supplier)}">Aprovar selecionados</button>
          <button type="button" class="ghost post-risk-supplier-button" data-risk-post-supplier="${encodeURIComponent(item.supplier)}">Efetivar selecionados</button>
          <button type="button" class="ghost target-risk-supplier-button" data-risk-target-supplier="${encodeURIComponent(item.supplier)}">Ajustar SLA</button>
          <button type="button" class="ghost export-risk-details-button" data-risk-export-supplier="${encodeURIComponent(item.supplier)}">Exportar documentos</button>
          <button type="button" class="ghost print-risk-summary-button" data-risk-print-supplier="${encodeURIComponent(item.supplier)}">Imprimir resumo</button>
        </div>
      `).join("") : '<div class="supplier-risk-card"><strong>Fornecedores monitorados</strong><span>Sem concentracao critica no momento</span></div>'}
    </div>
    <div class="pager supplier-risk-pager">
      <button id="supplier-risk-prev-page" type="button" class="ghost">Pagina anterior</button>
      <span id="supplier-risk-page-status" class="pager-status">Pagina ${state.supplierRiskPage + 1} de ${supplierPageCount}</span>
      <button id="supplier-risk-next-page" type="button" class="ghost">Proxima pagina</button>
    </div>
    <div class="context-note ${sensitivePendingDrafts.length ? "warning" : ""}">
      ${sensitivePendingDrafts.length
        ? `Rascunhos sensiveis sem aprovacao: ${sensitivePendingDrafts.length}. Criticos: ${criticalSensitiveDrafts}. Em atencao: ${warningSensitiveDrafts}. <button id="focus-critical-drafts" type="button" class="ghost inline-action">Abrir criticos</button>`
        : "Nao ha rascunhos sensiveis pendentes de aprovacao no momento."}
    </div>
    <div class="supplier-risk-history">
      ${riskHistory.map((item) => `
        <div class="supplier-risk-history-card">
          <strong>${item.openCritical}</strong>
          <span>${item.label}</span>
          <span>Resolvidos no intervalo: ${item.resolvedEstimate}</span>
        </div>
      `).join("")}
    </div>
  `;
  document.getElementById("focus-critical-drafts")?.addEventListener("click", () => {
    state.draftReceiptsCriticalOnly = true;
    state.draftReceiptsSensitiveOnly = true;
    elements.draftReceiptsSensitiveOnly.checked = true;
    persistFilterPreferences();
    state.draftReceiptsPage = 0;
    renderDraftReceiptsQueue(state.draftReceipts, state.draftReceiptsTotal);
    scrollToTarget("draft-receipts-list");
  });
  document.getElementById("supplier-risk-filter")?.addEventListener("input", (event) => {
    state.supplierRiskFilter = event.target.value;
    state.supplierRiskPage = 0;
    persistFilterPreferences();
    renderOperationContext(dashboard, counts);
  });
  document.getElementById("supplier-risk-date-from")?.addEventListener("change", (event) => {
    state.supplierRiskDateFrom = event.target.value;
    persistFilterPreferences();
    loadDashboard();
  });
  document.getElementById("supplier-risk-date-to")?.addEventListener("change", (event) => {
    state.supplierRiskDateTo = event.target.value;
    persistFilterPreferences();
    loadDashboard();
  });
  document.getElementById("export-supplier-risk-button")?.addEventListener("click", () => {
    exportSupplierRiskCsv(filteredSuppliers);
  setEntryStatus("Painel analitico de risco por fornecedor exportado em CSV com sucesso.", "success");
  });
  document.getElementById("export-supplier-risk-history-button")?.addEventListener("click", () => {
    exportSupplierRiskHistoryCsv();
  });
  document.getElementById("print-supplier-risk-history-button")?.addEventListener("click", () => {
    printSupplierRiskHistorySummary(riskHistory);
  });
  document.getElementById("supplier-risk-prev-page")?.addEventListener("click", () => {
    state.supplierRiskPage = Math.max(0, state.supplierRiskPage - 1);
    renderOperationContext(dashboard, counts);
  });
  document.getElementById("supplier-risk-next-page")?.addEventListener("click", () => {
    if (state.supplierRiskPage + 1 < supplierPageCount) {
      state.supplierRiskPage += 1;
      renderOperationContext(dashboard, counts);
    }
  });
  document.querySelectorAll("[data-risk-supplier]").forEach((card) => {
    card.addEventListener("click", (event) => {
      if (
        event.target?.classList?.contains("export-risk-details-button")
        || event.target?.classList?.contains("print-risk-summary-button")
        || event.target?.classList?.contains("select-risk-supplier-button")
      ) {
        return;
      }
      const supplier = decodeURIComponent(card.dataset.riskSupplier);
      state.draftReceiptsQuery = supplier;
      elements.draftReceiptsQuery.value = supplier;
      state.draftReceiptsSensitiveOnly = true;
      elements.draftReceiptsSensitiveOnly.checked = true;
      state.draftReceiptsCriticalOnly = false;
      elements.draftReceiptsSort.value = "sla_desc";
      persistFilterPreferences();
      state.draftReceiptsPage = 0;
      renderDraftReceiptsQueue(state.draftReceipts, state.draftReceiptsTotal);
      scrollToTarget("draft-receipts-list");
    });
  });
  document.querySelectorAll(".select-risk-supplier-button").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      const supplier = decodeURIComponent(button.dataset.riskSelectSupplier);
  const drafts = sensitivePendingDrafts.filter((item) => (item.supplier_reference || "Nao informado") === supplier);
  state.selectedDraftReceiptIds = new Set(drafts.map((item) => item.receipt_id));
      state.draftReceiptsQuery = supplier;
      elements.draftReceiptsQuery.value = supplier;
      state.draftReceiptsSensitiveOnly = true;
      elements.draftReceiptsSensitiveOnly.checked = true;
      elements.draftReceiptsSort.value = "sla_desc";
      persistFilterPreferences();
      state.draftReceiptsPage = 0;
      renderDraftReceiptsQueue(state.draftReceipts, state.draftReceiptsTotal);
      setEntryStatus(`Rascunhos de ${supplier} selecionados na fila para a proxima acao.`, "success");
      scrollToTarget("draft-receipts-list");
    });
  });
  document.querySelectorAll(".approve-risk-supplier-button").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.stopPropagation();
      const supplier = decodeURIComponent(button.dataset.riskApproveSupplier);
      const drafts = sensitivePendingDrafts.filter((item) => (item.supplier_reference || "Nao informado") === supplier);
      state.selectedDraftReceiptIds = new Set(drafts.map((item) => item.receipt_id));
      await bulkApproveSelectedDrafts();
    });
  });
  document.querySelectorAll(".target-risk-supplier-button").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.stopPropagation();
      const supplier = decodeURIComponent(button.dataset.riskTargetSupplier);
      const currentTarget = targetMap.get(supplier) || 48;
      const nextValue = window.prompt(`Defina o SLA alvo em horas para ${supplier}:`, String(currentTarget));
      if (!nextValue) {
        return;
      }
      const targetHours = Number(nextValue);
      if (!Number.isFinite(targetHours) || targetHours <= 0) {
        setEntryStatus("Informe um SLA valido em horas.", "error");
        return;
      }
      const response = await apiFetch("/inventory/supplier-risk-targets", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          store_id: selectedStoreId(),
          supplier_reference: supplier,
          target_hours: targetHours,
        }),
      });
      if (!response.ok) {
        setEntryStatus("Nao foi possivel atualizar o SLA alvo do fornecedor.", "error");
        return;
      }
      setEntryStatus(`SLA alvo atualizado para ${supplier} com janela de ${targetHours}h.`, "success");
      await loadDashboard();
    });
  });
  document.querySelectorAll(".post-risk-supplier-button").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.stopPropagation();
      const supplier = decodeURIComponent(button.dataset.riskPostSupplier);
      const drafts = sensitivePendingDrafts.filter((item) => (item.supplier_reference || "Nao informado") === supplier);
      const confirmed = window.confirm(`Efetivar ${drafts.length} rascunho(s) de ${supplier}? Essa acao impacta o estoque.`);
      if (!confirmed) {
        return;
      }
      state.selectedDraftReceiptIds = new Set(drafts.map((item) => item.receipt_id));
      await bulkPostSelectedDrafts();
    });
  });
  document.querySelectorAll(".export-risk-details-button").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      const supplier = decodeURIComponent(button.dataset.riskExportSupplier);
      const drafts = sensitivePendingDrafts.filter((item) => (item.supplier_reference || "Nao informado") === supplier);
      exportSupplierRiskDetailsCsv(supplier, drafts);
      setEntryStatus(`Documentos de risco de ${supplier} exportados em CSV.`, "success");
    });
  });
  document.querySelectorAll(".print-risk-summary-button").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      const supplier = decodeURIComponent(button.dataset.riskPrintSupplier);
      const drafts = sensitivePendingDrafts.filter((item) => (item.supplier_reference || "Nao informado") === supplier);
      printSupplierRiskSummary(supplier, drafts);
    });
  });
}

function renderDemoOperationContext() {
  elements.operationContext.className = "inline-card";
  elements.operationContext.innerHTML = `
    <div class="preview-grid">
      <div>
        <strong>Escopo demonstrativo</strong>
        <span>Loja Centro em destaque</span>
      </div>
      <div>
        <strong>Receita da janela</strong>
        <span>${formatCurrency(demoData.dashboard.sales.net_revenue)}</span>
      </div>
      <div>
        <strong>Estoque em atencao</strong>
        <span>${demoData.dashboard.inventory.low_stock_variants} variantes com cobertura reduzida</span>
      </div>
      <div>
        <strong>Contagem aberta</strong>
        <span>Contagem ciclica iniciada hoje as 09:00</span>
      </div>
      <div>
        <strong>Rascunhos pendentes</strong>
        <span>1 documento</span>
      </div>
      <div>
        <strong>Conferidos aguardando</strong>
        <span>1 documento aguardando o proximo passo</span>
      </div>
    </div>
  `;
}

function createSaleItemRow(prefill = {}) {
  const row = document.createElement("div");
  row.className = "inline-card";
  row.innerHTML = `
    <div class="inline-grid">
      <label>
        Variante
        <select class="sale-item-variant" required></select>
      </label>
      <label>
        Quantidade
        <input class="sale-item-quantity" type="number" min="1" value="${prefill.quantity || 1}" required>
      </label>
      <label>
        Preco unitario
        <input class="sale-item-price" type="number" min="0" step="0.01" value="${prefill.unit_price || ""}" required>
      </label>
      <button type="button" class="ghost remove-sale-item">Remover</button>
    </div>
  `;

  const select = row.querySelector(".sale-item-variant");
  const storeId = elements.saleStore.value;
  select.innerHTML = [`<option value="">Selecione a variante</option>`]
    .concat(
      filterVariantsByQuery(elements.salesVariantQuery?.value || "")
        .filter((variant) => !storeId || variantsForStore(storeId).some((item) => item.id === variant.id))
        .map((variant) => {
          const balance = getBalanceFor(storeId, variant.id);
          return `<option value="${variant.id}">${buildVariantOptionLabel(variant, `saldo ${balance?.on_hand_qty ?? 0}`)}</option>`;
        })
    )
    .join("");

  if (prefill.variant_id) {
    select.value = prefill.variant_id;
  }

  row.querySelector(".remove-sale-item").addEventListener("click", () => {
    row.remove();
    if (!elements.saleItems.children.length) {
      elements.saleItems.appendChild(createSaleItemRow());
    }
    renderSaleSummary();
  });

  select.addEventListener("change", () => {
    const variant = state.variants.find((item) => item.id === select.value);
    if (variant && !row.querySelector(".sale-item-price").value) {
      row.querySelector(".sale-item-price").value = variant.sale_price;
    }
    renderSaleSummary();
  });
  row.querySelector(".sale-item-quantity").addEventListener("input", renderSaleSummary);
  row.querySelector(".sale-item-price").addEventListener("input", renderSaleSummary);

  return row;
}

function getSalePayload() {
  return {
    store_id: elements.saleStore.value,
    discount_amount: elements.saleDiscount.value || "0",
    items: Array.from(elements.saleItems.querySelectorAll(".inline-card")).map((row) => ({
      variant_id: row.querySelector(".sale-item-variant").value,
      quantity: Number(row.querySelector(".sale-item-quantity").value),
      unit_price: row.querySelector(".sale-item-price").value,
    })),
  };
}

function renderPager(kind, total, page, pageSize) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const currentPage = Math.min(page + 1, pageCount);

  if (kind === "sales") {
    elements.salesPageStatus.textContent = buildPagerStatusLabel(currentPage, pageCount, total, "vendas");
    elements.salesPrevPage.disabled = page <= 0;
    elements.salesNextPage.disabled = (page + 1) * pageSize >= total;
    return;
  }

  elements.movementsPageStatus.textContent = buildPagerStatusLabel(currentPage, pageCount, total, "movimentos");
  elements.movementsPrevPage.disabled = page <= 0;
  elements.movementsNextPage.disabled = (page + 1) * pageSize >= total;
}

function renderSaleDetail(sale) {
  if (!sale) {
    elements.saleDetail.className = "sale-detail empty-state";
    elements.saleDetail.innerHTML = "Selecione uma venda para ver itens, valores e status.";
    return;
  }

  const canCancel = sale.status === "completed";
  elements.saleDetail.className = "sale-detail";
  elements.saleDetail.innerHTML = `
    <div class="detail-grid">
      <div class="detail-card">
        <span>Status</span>
        <strong>${sale.status === "completed" ? "Venda concluida" : "Venda cancelada"}</strong>
      </div>
      <div class="detail-card">
        <span>Total liquido</span>
        <strong>${formatCurrency(sale.total_amount)}</strong>
      </div>
      <div class="detail-card">
        <span>Desconto</span>
        <strong>${formatCurrency(sale.discount_amount)}</strong>
      </div>
      <div class="detail-card">
        <span>Data</span>
        <strong>${formatDateTime(sale.sold_at)}</strong>
      </div>
      <div class="detail-card">
        <span>Loja</span>
        <strong>${state.stores.find((item) => item.id === sale.store_id)?.name || sale.store_id}</strong>
      </div>
      <div class="detail-card">
        <span>Usuario</span>
        <strong>${sale.user_id || "-"}</strong>
      </div>
    </div>
    <div>
      <strong>Itens</strong>
      <div class="sale-items">
        ${sale.items.map((item) => `
          <div class="sale-item-row">
            <div>
              <strong>${state.variants.find((variant) => variant.id === item.variant_id)?.sku || item.variant_id}</strong>
              <span>${getProductName(state.variants.find((variant) => variant.id === item.variant_id)?.product_id)}</span>
              <span>${item.quantity} un. x ${formatCurrency(item.unit_price)}</span>
            </div>
            <strong>${formatCurrency(item.line_total)}</strong>
          </div>
          ${sale.status === "completed" ? `
            <div class="return-row">
              <label>
                Quantidade para devolucao
                <input class="return-quantity" data-variant-id="${item.variant_id}" type="number" min="1" max="${item.quantity}" value="1">
              </label>
              <button type="button" class="ghost return-item-button" data-variant-id="${item.variant_id}">Devolver este item</button>
            </div>
          ` : ""}
        `).join("")}
      </div>
    </div>
    <div class="detail-actions">
      ${canCancel ? `<button type="button" id="cancel-sale-button">Cancelar venda</button>` : ""}
    </div>
  `;

  if (canCancel) {
    document.getElementById("cancel-sale-button")?.addEventListener("click", () => {
      cancelSelectedSale();
    });
  }
  document.querySelectorAll(".return-item-button").forEach((button) => {
    button.addEventListener("click", () => {
      const variantId = button.dataset.variantId;
      const quantity = Number(
        document.querySelector(`.return-quantity[data-variant-id="${variantId}"]`)?.value || 0
      );
      returnSelectedSaleItem(variantId, quantity);
    });
  });
}

function renderSalesList(items) {
  elements.salesCount.textContent = String(state.salesTotal || items.length);
  if (!items.length) {
    elements.salesList.innerHTML = '<div class="list-item"><span>Nenhuma venda encontrada com os filtros atuais.</span></div>';
    state.selectedSaleId = null;
    renderSaleDetail(null);
    renderPager("sales", state.salesTotal, state.salesPage, state.salesPageSize);
    return;
  }

  if (!items.some((item) => item.id === state.selectedSaleId)) {
    state.selectedSaleId = items[0].id;
  }

  elements.salesList.innerHTML = items.map((item) => `
    <div class="list-item sale-card ${item.id === state.selectedSaleId ? "is-active" : ""}" data-sale-id="${item.id}">
      <strong>${formatCurrency(item.total_amount)}</strong>
      <span>${formatDateTime(item.sold_at)} - ${state.stores.find((store) => store.id === item.store_id)?.name || item.store_id}</span>
      <span>${item.items.length} itens movimentados nesta venda</span>
      <div class="sale-meta">
        <span class="sale-tag ${item.status === "canceled" ? "is-canceled" : ""}">${item.status === "completed" ? "venda concluida" : "venda cancelada"}</span>
        <span class="sale-tag">desconto aplicado: ${formatCurrency(item.discount_amount)}</span>
      </div>
    </div>
  `).join("");
  document.querySelectorAll("[data-sale-id]").forEach((card) => {
    card.addEventListener("click", async () => {
      state.selectedSaleId = card.dataset.saleId;
      await loadDashboard();
    });
  });

  renderPager("sales", state.salesTotal || items.length, state.salesPage, state.salesPageSize);
}

function renderMovementsList(items) {
  renderList(elements.movementsList, elements.movementsCount, items, (item) => `
    <div class="list-item">
      <strong>${item.movement_type}</strong>
      <span>${state.stores.find((store) => store.id === item.store_id)?.name || item.store_id} - ${state.variants.find((variant) => variant.id === item.variant_id)?.sku || item.variant_id}</span>
      <span>Impacto no saldo: ${item.quantity_delta > 0 ? "+" : ""}${item.quantity_delta} unidades</span>
      <span>Referencia operacional: ${item.document_reference || item.supplier_reference || "nao informada"}</span>
      <span>Motivo registrado: ${item.reason || "nao informado"}</span>
    </div>
  `);
  renderPager("movements", state.movementsTotal || items.length, state.movementsPage, state.movementsPageSize);
}

function renderReceiptDetail(receipt) {
  if (!receipt) {
    elements.receiptDetail.className = "sale-detail empty-state";
    elements.receiptDetail.innerHTML = "Selecione um recebimento para ver fornecedor, documento e itens recebidos.";
    return;
  }

  const auditItems = (receipt.audit || []).filter((entry) => {
    return !state.receiptAuditFilter || entry.action === state.receiptAuditFilter;
  });
  const approvalLabel = receipt.requires_approval
    ? (receipt.approved_by ? "Aprovado" : "Pendente")
    : "Nao exigida";
  const approvalMeta = receipt.requires_approval
    ? (receipt.approved_by ? formatActorLabel(receipt.approved_by) : "Aguardando manager ou admin")
    : "Regra de aprovacao nao aplicada";
  elements.receiptDetail.className = "sale-detail";
  elements.receiptDetail.innerHTML = `
    <div class="detail-grid">
      <div class="detail-card">
        <span>Status</span>
        <strong>${receipt.status || "-"}</strong>
      </div>
      <div class="detail-card">
        <span>Fornecedor</span>
        <strong>${receipt.supplier_reference || "Fornecedor nao informado"}</strong>
      </div>
      <div class="detail-card">
        <span>Total recebido</span>
        <strong>${receipt.total_quantity} unidades</strong>
      </div>
      <div class="detail-card">
        <span>Documento</span>
        <strong>${receipt.document_reference || "Documento nao informado"}</strong>
      </div>
      <div class="detail-card">
        <span>Itens no documento</span>
        <strong>${receipt.item_count}</strong>
      </div>
      <div class="detail-card">
        <span>Data</span>
        <strong>${formatDateTime(receipt.created_at)}</strong>
      </div>
      <div class="detail-card">
        <span>Motivo</span>
        <strong>${receipt.reason || "Motivo nao informado"}</strong>
      </div>
      <div class="detail-card">
        <span>Observacoes</span>
        <strong>${receipt.notes || "Sem observacoes registradas"}</strong>
      </div>
      <div class="detail-card">
        <span>Aprovacao</span>
        <strong>${approvalLabel}</strong>
        <span>${approvalMeta}</span>
      </div>
    </div>
    <div>
      <strong>Itens recebidos</strong>
      <div class="sale-items">
        ${receipt.items.map((item) => `
          <div class="sale-item-row">
            <div>
              <strong>${state.variants.find((variant) => variant.id === item.variant_id)?.sku || item.variant_id}</strong>
              <span>${getProductName(state.variants.find((variant) => variant.id === item.variant_id)?.product_id)}</span>
              <span>Registrado em ${formatDateTime(item.created_at)}</span>
            </div>
            <strong>+${item.quantity} un.</strong>
          </div>
        `).join("")}
      </div>
    </div>
    <div>
      <strong>Auditoria</strong>
      <div class="sale-items">
        ${auditItems.map((entry) => `
          <div class="sale-item-row">
            <div>
              <strong>${formatReceiptAuditAction(entry.action)}</strong>
              <span>${entry.details || "Sem detalhe adicional"}</span>
              <span>Evento em ${formatDateTime(entry.created_at)}</span>
            </div>
            <strong>${formatActorLabel(entry.created_by)}</strong>
          </div>
        `).join("") || '<div class="list-item"><span>Sem eventos para o filtro atual.</span></div>'}
      </div>
    </div>
    <div class="detail-actions">
      ${receipt.status === "draft" ? '<button type="button" id="edit-receipt-draft-button" class="ghost">Editar rascunho</button>' : ""}
      ${receipt.status === "draft" && receipt.requires_approval && !receipt.approved_by ? '<button type="button" id="approve-receipt-button" class="ghost">Aprovar rascunho</button>' : ""}
      ${receipt.status === "draft" ? '<button type="button" id="post-receipt-button">Efetivar recebimento</button>' : ""}
      ${receipt.status === "posted" ? '<button type="button" id="mark-receipt-checked-button">Marcar como conferido</button>' : ""}
      ${receipt.status === "checked" ? '<button type="button" id="mark-receipt-posted-button">Voltar para postado</button>' : ""}
      ${receipt.status === "draft" ? '<button type="button" id="discard-receipt-button" class="ghost">Descartar rascunho</button>' : ""}
      ${receipt.status !== "canceled" ? '<button type="button" id="cancel-receipt-button" class="ghost">Cancelar recebimento</button>' : ""}
    </div>
  `;

  document.getElementById("edit-receipt-draft-button")?.addEventListener("click", async () => {
    loadSelectedReceiptIntoEntryForm();
  });
  document.getElementById("approve-receipt-button")?.addEventListener("click", async () => {
    await approveSelectedReceiptDraft();
  });
  document.getElementById("post-receipt-button")?.addEventListener("click", async () => {
    await postSelectedReceiptDraft();
  });
  document.getElementById("mark-receipt-checked-button")?.addEventListener("click", async () => {
    await updateSelectedReceiptStatus("checked");
  });
  document.getElementById("mark-receipt-posted-button")?.addEventListener("click", async () => {
    await updateSelectedReceiptStatus("posted");
  });
  document.getElementById("cancel-receipt-button")?.addEventListener("click", async () => {
    await cancelSelectedReceipt();
  });
  document.getElementById("discard-receipt-button")?.addEventListener("click", async () => {
    await discardSelectedReceiptDraft();
  });
}

function renderReceiptsList(items, total = items.length, limit = state.receiptsPageSize, offset = state.receiptsPage * state.receiptsPageSize) {
  state.receipts = items;
  state.receiptsTotal = total;
  elements.receiptsCount.textContent = String(total);
  if (!items.length) {
    elements.receiptsList.innerHTML = '<div class="list-item"><span>Nenhum recebimento encontrado com os filtros atuais.</span></div>';
    elements.receiptsPageStatus.textContent = "Pagina 1";
    elements.receiptsPrevPage.disabled = true;
    elements.receiptsNextPage.disabled = true;
    state.selectedReceiptId = null;
    renderReceiptDetail(null);
    return;
  }

  const pageCount = Math.max(1, Math.ceil(total / limit));
  const currentPage = Math.floor(offset / limit) + 1;
  elements.receiptsPageStatus.textContent = `Pagina ${currentPage} de ${pageCount}`;
  elements.receiptsPrevPage.disabled = currentPage <= 1;
  elements.receiptsNextPage.disabled = currentPage >= pageCount;

  if (!items.some((item) => item.receipt_id === state.selectedReceiptId)) {
    state.selectedReceiptId = items[0].receipt_id;
  }

  elements.receiptsList.innerHTML = items.map((item) => `
    <div class="list-item sale-card ${item.receipt_id === state.selectedReceiptId ? "is-active" : ""}" data-receipt-id="${encodeURIComponent(item.receipt_id)}">
      <strong>${item.document_reference || "Recebimento sem documento"}</strong>
      <span>${item.supplier_reference || "Fornecedor nao informado"} - ${state.stores.find((store) => store.id === item.store_id)?.name || item.store_id}</span>
      <span>${item.total_quantity} unidades distribuidas em ${item.item_count} itens</span>
      <div class="sale-meta">
        <span class="sale-tag receipt-status-tag is-${item.status || "posted"}">status ${item.status || "posted"}</span>
        <span class="sale-tag">registrado em ${formatDateTime(item.created_at)}</span>
      </div>
    </div>
  `).join("");

  document.querySelectorAll("[data-receipt-id]").forEach((card) => {
    card.addEventListener("click", async () => {
      state.selectedReceiptId = decodeURIComponent(card.dataset.receiptId);
      if (!state.token) {
        renderReceiptDetail(demoData.receipts.find((item) => item.receipt_id === state.selectedReceiptId) || null);
        renderReceiptsList(state.receipts, state.receiptsTotal, state.receiptsPageSize, state.receiptsPage * state.receiptsPageSize);
        return;
      }
      await loadReceiptDetail();
      renderReceiptsList(state.receipts, state.receiptsTotal, state.receiptsPageSize, state.receiptsPage * state.receiptsPageSize);
    });
  });
}

function renderDraftReceiptsQueue(items, total = items.length) {
  state.draftReceipts = items;
  state.draftReceiptsTotal = total;
  let drafts = items
    .filter((item) => {
      const query = state.draftReceiptsQuery.trim().toLowerCase();
      if (!query) {
        return true;
      }
      return (
        (item.supplier_reference || "").toLowerCase().includes(query)
        || (item.document_reference || "").toLowerCase().includes(query)
      );
    })
    .filter((item) => !state.draftReceiptsCriticalOnly || isCriticalDraft(item));
  switch (elements.draftReceiptsSort.value) {
    case "date_asc":
      drafts.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
      break;
    case "sla_desc":
      drafts.sort((a, b) => {
        const priority = { critical: 3, warning: 2, ok: 1 };
        const levelDiff = priority[getDraftSlaMeta(b).level] - priority[getDraftSlaMeta(a).level];
        if (levelDiff !== 0) {
          return levelDiff;
        }
        return new Date(a.created_at) - new Date(b.created_at);
      });
      break;
    case "quantity_desc":
      drafts.sort((a, b) => b.total_quantity - a.total_quantity);
      break;
    case "supplier_asc":
      drafts.sort((a, b) => (a.supplier_reference || "").localeCompare(b.supplier_reference || ""));
      break;
    default:
      drafts.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      break;
  }
  elements.draftReceiptsCount.textContent = String(total);
  if (!drafts.length) {
    elements.draftReceiptsList.innerHTML = '<div class="list-item"><span>Nenhum rascunho pendente com os filtros atuais.</span></div>';
    elements.draftsPageStatus.textContent = "Pagina 1";
    elements.draftsPrevPage.disabled = state.draftReceiptsPage <= 0;
    elements.draftsNextPage.disabled = true;
    return;
  }

  const pageCount = Math.max(1, Math.ceil(total / state.draftReceiptsPageSize));
  state.draftReceiptsPage = Math.min(state.draftReceiptsPage, pageCount - 1);
  elements.draftsPageStatus.textContent = `Pagina ${state.draftReceiptsPage + 1} de ${pageCount}`;
  elements.draftsPrevPage.disabled = state.draftReceiptsPage <= 0;
  elements.draftsNextPage.disabled = state.draftReceiptsPage + 1 >= pageCount || drafts.length < state.draftReceiptsPageSize;
  elements.showCriticalDraftsButton.textContent = state.draftReceiptsCriticalOnly ? "Mostrar todos" : "Ver criticos";

  elements.draftReceiptsList.innerHTML = drafts.map((item) => `
    <div class="list-item sale-card ${item.requires_approval ? "requires-approval" : ""}" data-draft-receipt-id="${encodeURIComponent(item.receipt_id)}">
      <label class="inline-check">
        <input type="checkbox" class="draft-receipt-checkbox" data-draft-receipt-id="${encodeURIComponent(item.receipt_id)}" ${state.selectedDraftReceiptIds.has(item.receipt_id) ? "checked" : ""}>
        <span>Selecionar</span>
      </label>
      <strong>${item.document_reference || "Rascunho sem documento"}</strong>
      <span>${item.supplier_reference || "Fornecedor nao informado"}</span>
      <span>${item.total_quantity} unidades distribuidas em ${item.item_count} itens</span>
      ${item.requires_approval && !item.approved_by ? `<span class="draft-deadline ${isCriticalDraft(item) ? "is-critical" : ""}">${getDraftTimeToBreachLabel(item)}</span>` : ""}
      <div class="sale-meta">
        <span class="sale-tag receipt-status-tag is-draft">draft</span>
        ${item.requires_approval ? `<span class="sale-tag ${item.approved_by ? "approval-tag is-approved" : "approval-tag is-pending"}">${item.approved_by ? "aprovado" : "aguarda aprovacao"}</span>` : ""}
        <span class="sale-tag sla-tag is-${getDraftSlaMeta(item).level}">${getDraftSlaMeta(item).label}</span>
        ${state.draftReceiptsQuery.trim() && (item.supplier_reference || "").toLowerCase().includes(state.draftReceiptsQuery.trim().toLowerCase()) ? '<span class="sale-tag drilldown-tag">drill-down fornecedor</span>' : ""}
        <span class="sale-tag">${formatDateTime(item.created_at)}</span>
      </div>
    </div>
  `).join("");

  document.querySelectorAll("[data-draft-receipt-id]").forEach((card) => {
    card.addEventListener("click", async (event) => {
      if (event.target?.classList?.contains("draft-receipt-checkbox")) {
        return;
      }
      state.selectedReceiptId = decodeURIComponent(card.dataset.draftReceiptId);
      await loadReceiptDetail();
      loadSelectedReceiptIntoEntryForm();
      renderReceiptsList(state.receipts, state.receiptsTotal, state.receiptsPageSize, state.receiptsPage * state.receiptsPageSize);
    });
  });
  document.querySelectorAll(".draft-receipt-checkbox").forEach((checkbox) => {
    checkbox.addEventListener("change", () => {
      const receiptId = decodeURIComponent(checkbox.dataset.draftReceiptId);
      if (checkbox.checked) {
        state.selectedDraftReceiptIds.add(receiptId);
      } else {
        state.selectedDraftReceiptIds.delete(receiptId);
      }
    });
  });
}

function renderReceiptReport(items, total = items.length, limit = state.receiptReportPageSize, offset = state.receiptReportPage * state.receiptReportPageSize) {
  state.receiptReportRaw = items;
  state.receiptReportTotal = total;
  const filteredItems = items.filter((item) => !state.receiptReportSensitiveOnly || item.requires_approval);
  state.receiptReport = filteredItems;
  if (!filteredItems.length) {
    elements.receiptReportList.innerHTML = '<div class="list-item"><span>Nenhum dado documental para o periodo.</span></div>';
    elements.receiptReportPageStatus.textContent = "Pagina 1";
    elements.receiptReportPrevPage.disabled = state.receiptReportPage <= 0;
    elements.receiptReportNextPage.disabled = true;
    return;
  }

  const pageCount = Math.max(1, Math.ceil(total / limit));
  const currentPage = Math.floor(offset / limit) + 1;
  elements.receiptReportPageStatus.textContent = `Pagina ${currentPage} de ${pageCount}`;
  elements.receiptReportPrevPage.disabled = currentPage <= 1;
  elements.receiptReportNextPage.disabled = currentPage >= pageCount;

  elements.receiptReportList.innerHTML = filteredItems.map((item) => `
    <div class="list-item">
      <strong>${item.status}</strong>
      <span>Pendentes: ${item.pending_approval_receipts} | Aprovados: ${item.approved_receipts}</span>
      <span>Aprovacao sensivel: ${item.requires_approval ? "sim" : "nao"}</span>
      <span>${item.receipts} documentos</span>
      <span>${item.total_quantity} unidades distribuidas em ${item.item_count} itens</span>
    </div>
  `).join("");
}

function printReceiptReportSummary() {
  if (isDemoMode() && !state.receiptReport.length) {
    renderReceiptReport(buildDemoReceiptReport(), buildDemoReceiptReport().length, state.receiptReportPageSize, 0);
  }
  if (!state.receiptReport.length) {
    setEntryStatus("Nao ha dados documentais para imprimir no periodo atual.", "error");
    return;
  }

  const selectedStore = selectedStoreId();
  const selectedStoreName = selectedStore
    ? state.stores.find((store) => store.id === selectedStore)?.name || selectedStore
    : "Todas / minha loja";
  const periodLabel = `${elements.receiptReportDateFrom.value || "-"} ate ${elements.receiptReportDateTo.value || "-"}`;
  const rows = state.receiptReport.map((item) => `
    <tr>
      <td>${item.status}</td>
      <td>${item.supplier_reference || "Nao informado"}</td>
      <td>${item.requires_approval ? "Sim" : "Nao"}</td>
      <td>${item.pending_approval_receipts}</td>
      <td>${item.approved_receipts}</td>
      <td>${item.receipts}</td>
      <td>${item.total_quantity}</td>
    </tr>
  `).join("");

  const opened = openPrintDocument(buildPrintHtmlDocument(
    "Relatorio documental de recebimentos",
    `
      <h1>Relatorio documental de recebimentos</h1>
      <p>Loja: ${selectedStoreName}</p>
      <p>Periodo: ${periodLabel}</p>
      <p>Gerado em: ${new Date().toLocaleString("pt-BR")}</p>
      <table>
        <thead>
          <tr>
            <th>Status</th>
            <th>Fornecedor</th>
            <th>Exige aprovacao</th>
            <th>Pendentes</th>
            <th>Aprovados</th>
            <th>Documentos</th>
            <th>Quantidade total</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    `,
    { margin: 32, color: "#1f2933", borderColor: "#d9e2ec", headerBackground: "#f5f7fa", paragraphColor: "#52606d", tableMarginTop: 24 },
  ), { width: 960, height: 720 });
  if (!opened) {
    setEntryStatus("Nao foi possivel abrir a janela do relatorio documental.", "error");
    return;
  }
  setEntryStatus("Relatorio documental de recebimentos enviado para impressao.", "success");
}

async function printSelectedReceiptSummary() {
  if (isDemoMode()) {
    const data = getSelectedDemoReceipt();
    if (!data) {
      setEntryStatus("Selecione um recebimento demonstrativo antes de imprimir o resumo.", "error");
      return;
    }

    const rows = data.items.map((item) => `
      <tr>
        <td>${demoData.variants.find((variant) => variant.id === item.variant_id)?.sku || item.variant_id}</td>
        <td>${demoData.products.find((product) => product.id === demoData.variants.find((variant) => variant.id === item.variant_id)?.product_id)?.name || "-"}</td>
        <td>${item.quantity}</td>
      </tr>
    `).join("");
    const approvalHistory = (data.audit || [])
      .filter((entry) => entry.action === "draft_approved")
      .map((entry) => `
        <li>${formatDateTime(entry.created_at)} - ${formatActorLabel(entry.created_by)} - ${entry.details || "Aprovacao registrada"}</li>
      `)
      .join("");

    const opened = openPrintDocument(buildPrintHtmlDocument(
      "Resumo demonstrativo do recebimento",
      buildReceiptSummaryPrintBody(data, rows, approvalHistory, `Recebimento demonstrativo ${data.document_reference || data.receipt_id}`),
    ), { width: 900, height: 700 });
    if (!opened) {
      setEntryStatus("Nao foi possivel abrir a janela do resumo demonstrativo de recebimento.", "error");
      return;
    }
    setEntryStatus("Resumo do recebimento demonstrativo enviado para impressao.", "success");
    return;
  }
  if (!state.selectedReceiptId) {
    setEntryStatus("Selecione um recebimento antes de imprimir o resumo.", "error");
    return;
  }

  try {
    const response = await apiFetch(`/inventory/receipts/${encodeURIComponent(state.selectedReceiptId)}`);
    const data = await response.json();
    if (!response.ok) {
      setEntryStatus(data.detail || "Nao foi possivel montar o resumo do recebimento para impressao.", "error");
      return;
    }

    const rows = data.items.map((item) => `
      <tr>
        <td>${state.variants.find((variant) => variant.id === item.variant_id)?.sku || item.variant_id}</td>
        <td>${getProductName(state.variants.find((variant) => variant.id === item.variant_id)?.product_id)}</td>
        <td>${item.quantity}</td>
      </tr>
    `).join("");
    const approvalHistory = (data.audit || [])
      .filter((entry) => entry.action === "draft_approved")
      .map((entry) => `
        <li>${formatDateTime(entry.created_at)} - ${formatActorLabel(entry.created_by)} - ${entry.details || "Aprovacao registrada"}</li>
      `)
      .join("");

    const opened = openPrintDocument(buildPrintHtmlDocument(
      "Resumo do recebimento",
      buildReceiptSummaryPrintBody(data, rows, approvalHistory, `Recebimento ${data.document_reference || data.receipt_id}`),
    ), { width: 900, height: 700 });
    if (!opened) {
      setEntryStatus("Nao foi possivel abrir a janela do resumo de recebimento.", "error");
      return;
    }
    setEntryStatus("Resumo do recebimento selecionado enviado para impressao.", "success");
  } catch {
    setEntryStatus("Falha de comunicacao ao preparar o resumo de recebimento para impressao.", "error");
  }
}

async function exportSelectedReceiptCsv() {
  if (isDemoMode()) {
    const data = getSelectedDemoReceipt();
    if (!data) {
      setEntryStatus("Selecione um recebimento demonstrativo antes de exportar o CSV.", "error");
      return;
    }
    const rows = buildCsvRows(
      ["receipt_id", "supplier_reference", "document_reference", "reason", "store_id", "movement_id", "variant_id", "quantity", "created_at"],
      data.items,
      (item, index) => [
        data.receipt_id,
        data.supplier_reference || "",
        data.document_reference || "",
        data.reason || "",
        data.store_id,
        `demo-movement-${index + 1}`,
        item.variant_id,
        String(item.quantity),
        item.created_at || data.created_at,
      ],
    );
    downloadCsv(`recebimento-demo-${data.receipt_id}.csv`, rows);
    setEntryStatus("Recebimento demonstrativo exportado em CSV.", "success");
    return;
  }

  if (!state.selectedReceiptId) {
    setEntryStatus("Selecione um recebimento antes de exportar o CSV.", "error");
    return;
  }

  await exportCsvFromApi({
    path: `/inventory/receipts/${encodeURIComponent(state.selectedReceiptId)}/export`,
    filename: `recebimento-${state.selectedReceiptId}.csv`,
    onSuccess: "Recebimento selecionado exportado em CSV.",
    onError: "Nao foi possivel exportar o recebimento selecionado em CSV.",
    setStatusMessage: setEntryStatus,
  });
}

async function exportReceiptReportCsv() {
  if (isDemoMode()) {
    const reportItems = state.receiptReport.length ? state.receiptReport : buildDemoReceiptReport();
    if (!reportItems.length) {
      setEntryStatus("Nao ha dados documentais demonstrativos para exportar no periodo atual.", "error");
      return;
    }
    const rows = buildCsvRows(
      ["status", "supplier_reference", "requires_approval", "pending_approval_receipts", "approved_receipts", "receipts", "total_quantity"],
      reportItems,
      (item) => [
        item.status,
        item.supplier_reference || "",
        item.requires_approval ? "true" : "false",
        String(item.pending_approval_receipts),
        String(item.approved_receipts),
        String(item.receipts),
        String(item.total_quantity),
      ],
    );
    downloadCsv("relatorio-recebimentos-demo.csv", rows);
    setEntryStatus("Relatorio documental demonstrativo exportado em CSV.", "success");
    return;
  }

  const selectedStore = selectedStoreId();
  const params = new URLSearchParams();
  const [reportSortBy, reportDirection] = elements.receiptReportSort.value.split("_");
  if (selectedStore) {
    params.set("store_id", selectedStore);
  }
  if (elements.receiptReportDateFrom.value) {
    params.set("created_from", elements.receiptReportDateFrom.value);
  }
  if (elements.receiptReportDateTo.value) {
    params.set("created_to", elements.receiptReportDateTo.value);
  }
  if (state.receiptReportQuery.trim()) {
    params.set("q", state.receiptReportQuery.trim());
  }
  params.set("sort_by", reportSortBy || "receipts");
  params.set("direction", reportDirection || "desc");

  await exportCsvFromApi({
    path: `/inventory/receipts-report/export${params.toString() ? `?${params}` : ""}`,
    filename: "receipts-report.csv",
    onSuccess: "Relatorio documental de recebimentos exportado em CSV.",
    onError: "Nao foi possivel exportar o relatorio documental em CSV.",
    setStatusMessage: setEntryStatus,
  });
}

function buildMovementQueryParams(includePagination = true) {
  const params = new URLSearchParams();
  if (includePagination) {
    params.set("limit", String(state.movementsPageSize));
    params.set("offset", String(state.movementsPage * state.movementsPageSize));
  }
  if (elements.movementTypeQuery.value.trim()) {
    params.set("movement_type", elements.movementTypeQuery.value.trim());
  }
  if (elements.movementSupplierQuery.value.trim()) {
    params.set("supplier_reference", elements.movementSupplierQuery.value.trim());
  }
  if (elements.movementDocumentQuery.value.trim()) {
    params.set("document_reference", elements.movementDocumentQuery.value.trim());
  }
  if (elements.movementDateFrom.value) {
    params.set("created_from", elements.movementDateFrom.value);
  }
  if (elements.movementDateTo.value) {
    params.set("created_to", elements.movementDateTo.value);
  }

  const selectedStore = selectedStoreId();
  if (selectedStore) {
    params.set("store_id", selectedStore);
  }
  return params;
}

async function exportMovementsCsv() {
  if (isDemoMode()) {
    setSalesStatus("Modo demonstrativo: faca login para exportar movimentos reais em CSV.", "muted");
    return;
  }

  const params = buildMovementQueryParams(false);
  await exportCsvFromApi({
    path: `/inventory/movements/export${params.toString() ? `?${params}` : ""}`,
    filename: `movimentos-${new Date().toISOString().slice(0, 10)}.csv`,
    onSuccess: "Movimentos exportados em CSV com o filtro atual.",
    onError: "Nao foi possivel exportar os movimentos em CSV.",
    setStatusMessage: setSalesStatus,
  });
}

function renderCountsList(items) {
  elements.countsCount.textContent = String(items.length);
  const openCount = items.find((item) => item.status === "open") || null;
  state.activeCountId = openCount?.id || null;

  renderList(elements.countsList, elements.countsCount, items.slice(0, 8), (item) => `
    <div class="list-item">
      <strong>${item.scope}</strong>
      <span>Loja auditada: ${state.stores.find((store) => store.id === item.store_id)?.name || item.store_id}</span>
      <span>Status operacional: ${item.status === "open" ? "contagem em aberto" : "contagem encerrada"}</span>
      <span>Itens revisados: ${item.items.length}</span>
      <span>Inicio da contagem: ${formatDateTime(item.created_at)}</span>
      ${item.items.length ? `<span>Ultima variante auditada: ${state.variants.find((variant) => variant.id === item.items[item.items.length - 1].variant_id)?.sku || item.items[item.items.length - 1].variant_id}</span>` : ""}
    </div>
  `);
}

function refreshSaleItemsOptions() {
  const values = Array.from(elements.saleItems.children).map((row) => ({
    variant_id: row.querySelector(".sale-item-variant").value,
    quantity: row.querySelector(".sale-item-quantity").value,
    unit_price: row.querySelector(".sale-item-price").value,
  }));
  elements.saleItems.innerHTML = "";
  values.forEach((value) => {
    elements.saleItems.appendChild(createSaleItemRow(value));
  });
  renderSaleSummary();
}

async function handleCreateSale(event) {
  event.preventDefault();
  if (!state.token) {
    setSaleFormStatus("Entre com sua sessao antes de registrar uma venda.", "error");
    return;
  }

  const payload = getSalePayload();
  if (!payload.store_id || payload.items.some((item) => !item.variant_id || !item.unit_price || item.quantity <= 0)) {
    setSaleFormStatus("Selecione a loja e preencha todos os itens da venda.", "error");
    return;
  }

  try {
    const response = await apiFetch("/sales/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": getOperationIdempotencyKey("pendingSaleIdempotencyKey"),
      },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      setSaleFormStatus(data.detail || "Nao foi possivel concluir a venda da loja.", "error");
      return;
    }

    state.selectedSaleId = data.id;
    state.pendingSaleIdempotencyKey = null;
    elements.saleForm.reset();
    elements.saleItems.innerHTML = "";
    elements.saleItems.appendChild(createSaleItemRow());
    renderSaleSummary();
    setSaleFormStatus(`Venda ${data.id} registrada com sucesso no fluxo da loja.`, "success");
    await loadDashboard();
  } catch {
    setSaleFormStatus("Falha de comunicacao ao registrar a venda da loja.", "error");
  }
}

async function handleCreateCount(event) {
  event.preventDefault();
  if (!state.token) {
    setCountStatus("Entre com sua sessao antes de abrir uma contagem.", "error");
    return;
  }
  if (!elements.countStore.value || !elements.countVariant.value) {
    setCountStatus("Selecione a loja e a variante antes de iniciar a contagem.", "error");
    return;
  }

  try {
    let countId = state.activeCountId;
    if (!countId) {
      const createResponse = await apiFetch("/counts/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          store_id: elements.countStore.value,
          scope: elements.countScope.value.trim() || "cycle",
          reason: elements.countReason.value.trim() || null,
        }),
      });
      const created = await createResponse.json();
      if (!createResponse.ok) {
        setCountStatus(created.detail || "Nao foi possivel abrir a contagem de estoque.", "error");
        return;
      }
      countId = created.id;
      state.activeCountId = countId;
    }

    const itemResponse = await apiFetch(`/counts/${countId}/items`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        variant_id: elements.countVariant.value,
        counted_quantity: Number(elements.countQuantity.value),
      }),
    });
    const updated = await itemResponse.json();
    if (!itemResponse.ok) {
      setCountStatus(updated.detail || "Nao foi possivel registrar o item na contagem.", "error");
      return;
    }

    const item = updated.items.find((entry) => entry.variant_id === elements.countVariant.value);
    setCountStatus(
      `Item registrado. Diferenca apurada: ${item ? item.difference_quantity : 0}.`,
      "success"
    );
    await loadDashboard();
  } catch {
    setCountStatus("Falha de comunicacao ao registrar a contagem de estoque.", "error");
  }
}

async function closeActiveCount() {
  if (!state.activeCountId) {
    setCountStatus("Nao ha contagem aberta para encerrar neste momento.", "error");
    return;
  }

  try {
    const response = await apiFetch(`/counts/${state.activeCountId}/close`, {
      method: "POST",
    });
    const data = await response.json();
    if (!response.ok) {
      setCountStatus(data.detail || "Nao foi possivel fechar a contagem de estoque.", "error");
      return;
    }

    state.activeCountId = null;
    setCountStatus(`Contagem ${data.id} fechada com sucesso no estoque.`, "success");
    await loadDashboard();
  } catch {
    setCountStatus("Falha de comunicacao ao fechar a contagem de estoque.", "error");
  }
}

async function cancelSelectedSale() {
  if (!state.selectedSaleId) {
    return;
  }

  try {
    const response = await apiFetch(`/sales/${state.selectedSaleId}/cancel`, {
      method: "POST",
    });
    const data = await response.json();

    if (!response.ok) {
      setSalesStatus(data.detail || "Nao foi possivel cancelar a venda.", "error");
      return;
    }

    setSalesStatus(`Venda ${data.id} cancelada com sucesso no fluxo comercial.`, "success");
    await loadDashboard();
  } catch {
    setSalesStatus("Falha de comunicacao ao cancelar a venda.", "error");
  }
}

async function handleAdjustment(event) {
  event.preventDefault();
  if (!state.token) {
    setAdjustmentStatus("Entre com sua sessao antes de aplicar um ajuste.", "error");
    return;
  }

  try {
    const response = await apiFetch("/inventory/adjustment", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        store_id: elements.adjustmentStore.value,
        variant_id: elements.adjustmentVariant.value,
        new_quantity: Number(elements.adjustmentQuantity.value),
        reason: elements.adjustmentReason.value.trim(),
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      setAdjustmentStatus(data.detail || "Nao foi possivel aplicar o ajuste de saldo.", "error");
      return;
    }

    setAdjustmentStatus(`Ajuste concluido. Saldo atualizado para ${data.on_hand_qty} unidades.`, "success");
    await loadDashboard();
  } catch {
    setAdjustmentStatus("Falha de comunicacao ao aplicar o ajuste de saldo.", "error");
  }
}

async function handleEntry(event) {
  event.preventDefault();
  if (!state.token) {
    setEntryStatus("Entre com sua sessao antes de registrar um recebimento.", "error");
    return;
  }

  const payload = getEntryPayload();
  if (!payload.store_id || payload.items.some((item) => !item.variant_id || item.quantity <= 0)) {
    setEntryStatus("Selecione a loja e preencha todos os itens do recebimento.", "error");
    return;
  }

  try {
    const response = await apiFetch("/inventory/entries", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": getOperationIdempotencyKey("pendingEntryIdempotencyKey"),
      },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      setEntryStatus(data.detail || "Nao foi possivel registrar o recebimento de estoque.", "error");
      return;
    }

    const totalUnits = payload.items.reduce((sum, item) => sum + Number(item.quantity || 0), 0);
    state.pendingEntryIdempotencyKey = null;
    setEntryStatus(`Recebimento em lote concluido com ${payload.items.length} variantes e ${totalUnits} unidades registradas.`, "success");
    elements.entryForm.reset();
    elements.entryItems.innerHTML = "";
    elements.entryItems.appendChild(createEntryItemRow());
    renderEntryPreview();
    await loadDashboard();
  } catch {
    setEntryStatus("Falha de comunicacao ao registrar o recebimento de estoque.", "error");
  }
}

async function saveEntryDraft() {
  if (!state.token) {
    setEntryStatus("Entre com sua sessao antes de salvar um rascunho.", "error");
    return;
  }

  const payload = getEntryPayload();
  if (!payload.store_id || payload.items.some((item) => !item.variant_id || item.quantity <= 0)) {
    setEntryStatus("Selecione a loja e preencha todos os itens do rascunho.", "error");
    return;
  }

  try {
    const isEditing = Boolean(state.editingReceiptId);
    const endpoint = isEditing
      ? `/inventory/receipts/${encodeURIComponent(state.editingReceiptId)}/draft`
      : "/inventory/receipts/draft";
    const response = await apiFetch(endpoint, {
      method: isEditing ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      setEntryStatus(data.detail || "Nao foi possivel salvar o rascunho de recebimento.", "error");
      return;
    }

    resetEntryFormState();
    setEntryStatus(
      `${isEditing ? "Rascunho atualizado" : "Rascunho salvo"} com identificador ${data.receipt_id} e ${data.item_count} itens.`,
      "success"
    );
    await loadDashboard();
  } catch {
    setEntryStatus("Falha de comunicacao ao salvar o rascunho de recebimento.", "error");
  }
}

async function returnSelectedSaleItem(variantId, quantity) {
  if (!state.selectedSaleId || !variantId || quantity <= 0) {
    setSalesStatus("Selecione um item e informe uma quantidade valida para devolucao.", "error");
    return;
  }

  try {
    const response = await apiFetch(`/sales/${state.selectedSaleId}/return`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        items: [{ variant_id: variantId, quantity }],
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      setSalesStatus(data.detail || "Nao foi possivel registrar a devolucao parcial.", "error");
      return;
    }

    setSalesStatus(`Devolucao parcial registrada com sucesso na venda ${data.id}.`, "success");
    await loadDashboard();
  } catch {
    setSalesStatus("Falha de comunicacao ao registrar a devolucao parcial.", "error");
  }
}

async function loadDashboard() {
  if (!state.token) {
    hydrateHelperOptions(demoData.stores, demoData.variants, demoData.products);
    setBalances(demoData.balances);
    refreshTransferVariantOptions();
    refreshAdjustmentVariantOptions();
    refreshEntryVariantOptions();
    refreshCountVariantOptions();
    renderTransferPreview();
    renderAdjustmentPreview();
    renderEntryPreview();
    renderCountPreview();
    refreshSaleItemsOptions();
    renderDashboardSummary(demoData.dashboard);
    renderDailySales(demoData.dashboard.daily_sales);
    renderTopVariants(demoData.dashboard.top_variants);
    state.salesTotal = demoData.sales.length;
    state.movementsTotal = demoData.movements.length;
    const demoSalesPage = demoData.sales.slice(
      state.salesPage * state.salesPageSize,
      (state.salesPage + 1) * state.salesPageSize
    );
    const demoMovementsPage = demoData.movements.slice(
      state.movementsPage * state.movementsPageSize,
      (state.movementsPage + 1) * state.movementsPageSize
    );
    renderExecutiveStrip(demoData.dashboard, demoData.sales, demoData.counts);
    renderSalesList(demoSalesPage);
    renderSaleDetail(demoData.sales.find((item) => item.id === state.selectedSaleId) || demoSalesPage[0] || null);
    renderCountsList(demoData.counts);
    renderDemoOperationContext();

    renderList(elements.productsList, elements.productsCount, demoData.products, (item) => `
      <div class="list-item">
        <strong>${item.name}</strong>
        <span>Marca: ${item.brand || "-"}</span>
        <span>Status: ${item.is_active ? "ativo" : "inativo"}</span>
      </div>
    `);

    renderList(elements.variantsList, elements.variantsCount, demoData.variants, (item) => `
      <div class="list-item">
        <strong>${item.sku}</strong>
        <span>Barcode: ${item.barcode || "-"}</span>
        <span>Venda: ${formatCurrency(item.sale_price)}</span>
      </div>
    `);

    renderList(elements.balancesList, elements.balancesCount, demoData.balances, (item) => `
      <div class="list-item">
        <strong>${demoData.variants.find((variant) => variant.id === item.variant_id)?.sku || item.variant_id}</strong>
        <span>${demoData.products.find((product) => product.id === demoData.variants.find((variant) => variant.id === item.variant_id)?.product_id)?.name || "Produto"}</span>
        <span>Loja: ${demoData.stores.find((store) => store.id === item.store_id)?.name || item.store_id}</span>
        <span>Disponivel: ${item.on_hand_qty}</span>
      </div>
    `);

    renderMovementsList(demoMovementsPage);
    state.receiptsPage = 0;
    state.draftReceiptsPage = 0;
    state.selectedReceiptId = state.selectedReceiptId || demoData.receipts[0]?.receipt_id || null;
    renderReceiptReferenceSuggestions(demoData.receiptReferences);
    renderReceiptsList(demoData.receipts, demoData.receipts.length, state.receiptsPageSize, 0);
    renderReceiptDetail(demoData.receipts.find((item) => item.receipt_id === state.selectedReceiptId) || demoData.receipts[0] || null);
    renderDraftReceiptsQueue(demoData.receipts.filter((item) => item.status === "draft"), demoData.receipts.filter((item) => item.status === "draft").length);
    renderReceiptReport(buildDemoReceiptReport(), buildDemoReceiptReport().length, state.receiptReportPageSize, 0);

    setSalesStatus("Visual demonstrativo ativo. Entre para operar dados reais.", "muted");
    setSaleFormStatus("Modo demonstrativo: faca login para registrar vendas reais.", "muted");
    setCountStatus("Modo demonstrativo: faca login para iniciar contagens reais.", "muted");
    setTransferStatus("Modo demonstrativo: faca login para movimentar estoque real.", "muted");
    setEntryStatus("Modo demonstrativo: faca login para registrar recebimentos reais.", "muted");
    return;
  }

  const productParams = new URLSearchParams();
  const variantParams = new URLSearchParams();
  const movementParams = buildMovementQueryParams(true);
  const dashboardParams = new URLSearchParams({
    days: elements.dashboardDays.value,
    top_limit: elements.dashboardTopLimit.value,
  });
  const salesParams = new URLSearchParams({
    limit: String(state.salesPageSize),
    offset: String(state.salesPage * state.salesPageSize),
  });
  const balancesParams = new URLSearchParams();
  const countsParams = new URLSearchParams();
  const selectedStore = selectedStoreId();

  if (elements.productQuery.value.trim()) {
    productParams.set("q", elements.productQuery.value.trim());
  }
  if (elements.skuQuery.value.trim()) {
    variantParams.set("sku", elements.skuQuery.value.trim());
  }
  if (elements.barcodeQuery.value.trim()) {
    variantParams.set("barcode", elements.barcodeQuery.value.trim());
  }
  if (elements.salesStatusQuery.value.trim()) {
    salesParams.set("status", elements.salesStatusQuery.value.trim());
  }
  if (elements.salesVariantQuery.value.trim()) {
    salesParams.set("q", elements.salesVariantQuery.value.trim());
  }
  if (elements.salesDateFrom.value) {
    salesParams.set("sold_from", elements.salesDateFrom.value);
  }
  if (elements.salesDateTo.value) {
    salesParams.set("sold_to", elements.salesDateTo.value);
  }
  if (selectedStore) {
    dashboardParams.set("store_id", selectedStore);
    salesParams.set("store_id", selectedStore);
    balancesParams.set("store_id", selectedStore);
    countsParams.set("store_id", selectedStore);
  }

  try {
    const receiptReferencesParams = new URLSearchParams();
    if (selectedStore) {
      receiptReferencesParams.set("store_id", selectedStore);
    }
    receiptReferencesParams.set("limit", "12");

    const receiptsParams = new URLSearchParams();
    if (selectedStore) {
      receiptsParams.set("store_id", selectedStore);
    }
    receiptsParams.set("limit", String(state.receiptsPageSize));
    receiptsParams.set("offset", String(state.receiptsPage * state.receiptsPageSize));
    if (elements.movementSupplierQuery.value.trim() || elements.movementDocumentQuery.value.trim()) {
      receiptsParams.set("q", elements.movementSupplierQuery.value.trim() || elements.movementDocumentQuery.value.trim());
    }
    if (elements.receiptStatusQuery.value.trim()) {
      receiptsParams.set("status", elements.receiptStatusQuery.value.trim());
    }
    if (elements.movementDateFrom.value) {
      receiptsParams.set("created_from", elements.movementDateFrom.value);
    }
    if (elements.movementDateTo.value) {
      receiptsParams.set("created_to", elements.movementDateTo.value);
    }

    const draftReceiptsParams = new URLSearchParams();
    if (selectedStore) {
      draftReceiptsParams.set("store_id", selectedStore);
    }
    draftReceiptsParams.set("status", "draft");
    draftReceiptsParams.set("limit", String(state.draftReceiptsPageSize));
    draftReceiptsParams.set("offset", String(state.draftReceiptsPage * state.draftReceiptsPageSize));
    if (state.draftReceiptsSensitiveOnly) {
      draftReceiptsParams.set("requires_approval", "true");
    }
    if (state.draftReceiptsQuery.trim()) {
      draftReceiptsParams.set("q", state.draftReceiptsQuery.trim());
    }
    if (elements.movementDateFrom.value) {
      draftReceiptsParams.set("created_from", elements.movementDateFrom.value);
    }
    if (elements.movementDateTo.value) {
      draftReceiptsParams.set("created_to", elements.movementDateTo.value);
    }

    const receiptReportParams = new URLSearchParams();
    const [reportSortBy, reportDirection] = elements.receiptReportSort.value.split("_");
    if (selectedStore) {
      receiptReportParams.set("store_id", selectedStore);
    }
    if (elements.receiptReportDateFrom.value) {
      receiptReportParams.set("created_from", elements.receiptReportDateFrom.value);
    }
    if (elements.receiptReportDateTo.value) {
      receiptReportParams.set("created_to", elements.receiptReportDateTo.value);
    }
    if (state.receiptReportQuery.trim()) {
      receiptReportParams.set("q", state.receiptReportQuery.trim());
    }
    receiptReportParams.set("limit", String(state.receiptReportPageSize));
    receiptReportParams.set("offset", String(state.receiptReportPage * state.receiptReportPageSize));
    receiptReportParams.set("sort_by", reportSortBy || "receipts");
    receiptReportParams.set("direction", reportDirection || "desc");

    const supplierRiskTargetsParams = new URLSearchParams();
    const supplierRiskHistoryParams = new URLSearchParams();
    if (selectedStore) {
      supplierRiskTargetsParams.set("store_id", selectedStore);
      supplierRiskHistoryParams.set("store_id", selectedStore);
    }
    if (state.supplierRiskDateFrom) {
      supplierRiskHistoryParams.set("created_from", state.supplierRiskDateFrom);
    }
    if (state.supplierRiskDateTo) {
      supplierRiskHistoryParams.set("created_to", state.supplierRiskDateTo);
    }

    const [meRes, dashboardRes, productsRes, variantsRes, balancesRes, movementsRes, salesRes, storesRes, countsRes, receiptReferencesRes, receiptsRes, draftReceiptsRes, receiptReportRes, supplierRiskTargetsRes, supplierRiskHistoryRes] = await Promise.all([
      apiFetch("/auth/me"),
      apiFetch(`/dashboard/?${dashboardParams}`),
      apiFetch(`/products/${productParams.toString() ? `?${productParams}` : ""}`),
      apiFetch(`/variants/${variantParams.toString() ? `?${variantParams}` : ""}`),
      apiFetch(`/inventory/balances${balancesParams.toString() ? `?${balancesParams}` : ""}`),
      apiFetch(`/inventory/movements${movementParams.toString() ? `?${movementParams}` : ""}`),
      apiFetch(`/sales/${salesParams.toString() ? `?${salesParams}` : ""}`),
      apiFetch("/stores/"),
      apiFetch(`/counts/${countsParams.toString() ? `?${countsParams}` : ""}`),
      apiFetch(`/inventory/receipt-references${receiptReferencesParams.toString() ? `?${receiptReferencesParams}` : ""}`),
      apiFetch(`/inventory/receipts${receiptsParams.toString() ? `?${receiptsParams}` : ""}`),
      apiFetch(`/inventory/receipts${draftReceiptsParams.toString() ? `?${draftReceiptsParams}` : ""}`),
      apiFetch(`/inventory/receipts-report${receiptReportParams.toString() ? `?${receiptReportParams}` : ""}`),
      apiFetch(`/inventory/supplier-risk-targets${supplierRiskTargetsParams.toString() ? `?${supplierRiskTargetsParams}` : ""}`),
      apiFetch(`/inventory/supplier-risk-history${supplierRiskHistoryParams.toString() ? `?${supplierRiskHistoryParams}` : ""}`),
    ]);

    if ([meRes, dashboardRes, productsRes, variantsRes, balancesRes, movementsRes, salesRes, storesRes, countsRes, receiptReferencesRes, receiptsRes, draftReceiptsRes, receiptReportRes, supplierRiskTargetsRes, supplierRiskHistoryRes].some((res) => res.status === 401)) {
      setStatus("Sua sessao expirou. Faca login novamente.", "error");
      clearSession();
      return;
    }

    const [currentUser, dashboard, products, variants, balances, movements, sales, stores, counts, receiptReferences, receipts, draftReceipts, receiptReport, supplierRiskTargets, supplierRiskHistory] = await Promise.all([
      meRes.json(),
      dashboardRes.json(),
      productsRes.json(),
      variantsRes.json(),
      balancesRes.json(),
      movementsRes.json(),
      salesRes.json(),
      storesRes.json(),
      countsRes.json(),
      receiptReferencesRes.json(),
      receiptsRes.json(),
      draftReceiptsRes.json(),
      receiptReportRes.json(),
      supplierRiskTargetsRes.json(),
      supplierRiskHistoryRes.json(),
    ]);

    state.currentUser = currentUser;

    let adminUsers = [];
    if (currentUser?.role === "admin") {
      const usersRes = await apiFetch("/users/");
      if (usersRes.status === 401) {
        setStatus("Sua sessao expirou. Faca login novamente.", "error");
        clearSession();
        return;
      }
      adminUsers = usersRes.ok ? await usersRes.json() : [];
    }
    state.adminUsers = adminUsers;

    hydrateHelperOptions(stores, variants, products);
    setBalances(balances);
    refreshTransferVariantOptions();
    refreshAdjustmentVariantOptions();
    refreshEntryVariantOptions();
    refreshCountVariantOptions();
    renderTransferPreview();
    renderAdjustmentPreview();
    renderEntryPreview();
    renderCountPreview();
    refreshSaleItemsOptions();

    renderDashboardSummary(dashboard);
    renderDailySales(dashboard.daily_sales || []);
    renderTopVariants(dashboard.top_variants || []);
    state.salesTotal = sales.total || 0;
    state.movementsTotal = movements.total || 0;
    state.receipts = receipts.items || [];
    state.receiptsTotal = receipts.total || 0;
    state.supplierRiskTargets = supplierRiskTargets || [];
    state.supplierRiskHistory = supplierRiskHistory.items || [];
    renderExecutiveStrip(dashboard, sales.items || [], counts);
    renderOperationContext(dashboard, counts);
    renderSalesList(sales.items || []);
    renderSaleDetail((sales.items || []).find((item) => item.id === state.selectedSaleId) || sales.items?.[0] || null);
    renderCountsList(counts);

    renderList(elements.productsList, elements.productsCount, products, (item) => `
      <div class="list-item">
        <strong>${item.name}</strong>
        <span>Marca: ${item.brand || "-"}</span>
        <span>Status: ${item.is_active ? "ativo" : "inativo"}</span>
      </div>
    `);

    renderList(elements.variantsList, elements.variantsCount, variants, (item) => `
      <div class="list-item">
        <strong>${item.sku}</strong>
        <span>Barcode: ${item.barcode || "-"}</span>
        <span>Venda: R$ ${item.sale_price}</span>
      </div>
    `);

    renderList(elements.balancesList, elements.balancesCount, balances, (item) => `
      <div class="list-item">
        <strong>${state.variants.find((variant) => variant.id === item.variant_id)?.sku || item.variant_id}</strong>
        <span>${getProductName(state.variants.find((variant) => variant.id === item.variant_id)?.product_id)}</span>
        <span>Loja: ${state.stores.find((store) => store.id === item.store_id)?.name || item.store_id}</span>
        <span>Disponivel: ${item.on_hand_qty}</span>
      </div>
    `);

    renderMovementsList(movements.items || []);
    renderReceiptReferenceSuggestions(receiptReferences || []);
    renderReceiptsList(receipts.items || [], receipts.total || 0, receipts.limit || state.receiptsPageSize, receipts.offset || 0);
    renderDraftReceiptsQueue(draftReceipts.items || [], draftReceipts.total || 0);
    renderReceiptReport(
      receiptReport.items || [],
      receiptReport.total || 0,
      receiptReport.limit || state.receiptReportPageSize,
      receiptReport.offset || 0,
    );
    renderAdminPanel();
    await loadReceiptDetail();
  } catch {
    setStatus("Nao foi possivel carregar o painel.", "error");
  }
}

async function handleLogin(event) {
  event.preventDefault();
  const body = new URLSearchParams({
    username: elements.email.value,
    password: elements.password.value,
  });

  try {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });

    if (!response.ok) {
      setStatus("Nao foi possivel iniciar a sessao. Revise email e senha.", "error");
      return;
    }

    const data = await response.json();
    state.token = data.access_token;
    state.currentUser = data.user;
    localStorage.setItem("stock_token", state.token);
    setSessionStatus();
    setStatus(`Sessao iniciada com sucesso para ${data.user.email}.`, "success");
    loadDashboard();
  } catch {
    setStatus("Falha de comunicacao ao iniciar a sessao.", "error");
  }
}

async function handleTransfer(event) {
  event.preventDefault();

  if (!state.token) {
    setTransferStatus("Entre com sua sessao antes de transferir estoque.", "error");
    return;
  }

  const payload = {
    source_store_id: elements.transferSourceStore.value.trim(),
    destination_store_id: elements.transferDestinationStore.value.trim(),
    variant_id: elements.transferVariant.value.trim(),
    quantity: Number(elements.transferQuantity.value),
    reason: elements.transferReason.value.trim() || null,
  };

  try {
    const response = await apiFetch("/inventory/transfer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await response.json();

    if (!response.ok) {
      setTransferStatus(data.detail || "Nao foi possivel concluir a transferencia entre lojas.", "error");
      return;
    }

    setTransferStatus(
      `Transferencia entre lojas concluida. Origem: ${data.source_balance.on_hand_qty} | Destino: ${data.destination_balance.on_hand_qty}.`,
      "success"
    );
    elements.transferForm.reset();
    loadDashboard();
  } catch {
    setTransferStatus("Falha de comunicacao ao transferir estoque entre lojas.", "error");
  }
}

async function handleCreateAdminUser(event) {
  event.preventDefault();

  if (!state.token || !isAdminUser()) {
    setAdminUserStatus("Entre com um perfil admin para criar usuarios.", "error");
    return;
  }

  const payload = {
    name: elements.adminUserName.value.trim(),
    email: elements.adminUserEmail.value.trim(),
    password: elements.adminUserPassword.value,
    role: elements.adminUserRole.value,
    is_active: true,
    store_id: elements.adminUserStore.value || null,
  };

  try {
    const response = await apiFetch("/users/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      setAdminUserStatus(data.detail || "Nao foi possivel criar o usuario.", "error");
      return;
    }
    elements.adminUserForm.reset();
    elements.adminUserRole.value = "operator";
    syncAdminUserStoreOptions();
    setAdminUserStatus(`Usuario ${data.email} criado com sucesso.`, "success");
    loadDashboard();
  } catch {
    setAdminUserStatus("Falha de comunicacao ao criar o usuario.", "error");
  }
}

async function handleCreateAdminStore(event) {
  event.preventDefault();

  if (!state.token || !isAdminUser()) {
    setAdminStoreStatus("Entre com um perfil admin para criar lojas.", "error");
    return;
  }

  const payload = {
    name: elements.adminStoreName.value.trim(),
    timezone: elements.adminStoreTimezone.value.trim() || "America/Sao_Paulo",
    is_active: elements.adminStoreActive.checked,
  };

  try {
    const response = await apiFetch("/stores/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      setAdminStoreStatus(data.detail || "Nao foi possivel criar a loja.", "error");
      return;
    }
    elements.adminStoreForm.reset();
    elements.adminStoreTimezone.value = "America/Sao_Paulo";
    elements.adminStoreActive.checked = true;
    setAdminStoreStatus(`Loja ${data.name} criada com sucesso.`, "success");
    loadDashboard();
  } catch {
    setAdminStoreStatus("Falha de comunicacao ao criar a loja.", "error");
  }
}

function clearSession() {
  state.token = "";
  state.currentUser = null;
  state.adminUsers = [];
  state.selectedSaleId = null;
  state.activeCountId = null;
  localStorage.removeItem("stock_token");
  setSessionStatus();
  renderList(elements.productsList, elements.productsCount, [], () => "");
  renderList(elements.variantsList, elements.variantsCount, [], () => "");
  renderList(elements.balancesList, elements.balancesCount, [], () => "");
  renderList(elements.movementsList, elements.movementsCount, [], () => "");
  renderCountsList([]);
  elements.dashboardSummary.innerHTML = "";
  renderDailySales([]);
  renderTopVariants([]);
  setSalesStatus("Cancelamento disponivel para perfis com permissao operacional na API.", "muted");
  setSaleFormStatus("Monte os itens, revise o saldo e conclua a venda quando a conferencia estiver pronta.", "muted");
  setCountStatus("Abra uma contagem, registre os itens auditados e feche a execucao ao concluir a revisao.", "muted");
  setEntryStatus("Use para entradas manuais, recebimentos de fornecedor e regularizacoes operacionais.", "muted");
  elements.operationContext.className = "inline-card empty-state";
  elements.operationContext.innerHTML = "Selecione uma loja no painel para ver o contexto operacional consolidado desta sessao.";
  elements.saleSummary.className = "inline-card empty-state";
  elements.saleSummary.innerHTML = "Selecione loja e itens para revisar subtotal, desconto e alertas de saldo antes de concluir.";
  renderAdminPanel();
}

function scrollToTarget(targetId) {
  const target = document.getElementById(targetId);
  target?.scrollIntoView({ behavior: "smooth", block: "start" });
}

elements.loginForm.addEventListener("submit", handleLogin);
elements.adminUserForm?.addEventListener("submit", handleCreateAdminUser);
elements.adminStoreForm?.addEventListener("submit", handleCreateAdminStore);
elements.transferForm.addEventListener("submit", handleTransfer);
elements.adjustmentForm.addEventListener("submit", handleAdjustment);
elements.entryForm.addEventListener("submit", handleEntry);
elements.saleForm.addEventListener("submit", handleCreateSale);
elements.countForm.addEventListener("submit", handleCreateCount);
elements.addEntryItemButton.addEventListener("click", () => {
  elements.entryItems.appendChild(createEntryItemRow());
  renderEntryPreview();
});
elements.addSaleItemButton.addEventListener("click", () => {
  elements.saleItems.appendChild(createSaleItemRow());
  renderSaleSummary();
});
elements.saleStore.addEventListener("change", refreshSaleItemsOptions);
elements.saleStore.addEventListener("change", () => savePreference(preferenceKeys.saleStore, elements.saleStore.value));
elements.saleDiscount.addEventListener("input", renderSaleSummary);
elements.transferSourceStore.addEventListener("change", () => {
  savePreference(preferenceKeys.transferSourceStore, elements.transferSourceStore.value);
  refreshTransferVariantOptions();
  renderTransferPreview();
});
elements.transferDestinationStore.addEventListener("change", () => {
  savePreference(preferenceKeys.transferDestinationStore, elements.transferDestinationStore.value);
  renderTransferPreview();
});
elements.transferVariant.addEventListener("change", renderTransferPreview);
elements.adjustmentStore.addEventListener("change", () => {
  refreshAdjustmentVariantOptions();
  renderAdjustmentPreview();
});
elements.adjustmentVariant.addEventListener("change", renderAdjustmentPreview);
elements.adjustmentQuantity.addEventListener("input", renderAdjustmentPreview);
elements.entryStore.addEventListener("change", () => {
  refreshEntryVariantOptions();
  renderEntryPreview();
});
elements.countStore.addEventListener("change", () => {
  refreshCountVariantOptions();
  renderCountPreview();
});
elements.countStore.addEventListener("change", () => savePreference(preferenceKeys.countStore, elements.countStore.value));
elements.countVariant.addEventListener("change", renderCountPreview);
elements.countQuantity.addEventListener("input", renderCountPreview);
elements.closeCountButton.addEventListener("click", closeActiveCount);
elements.refreshButton.addEventListener("click", loadDashboard);
elements.storeFilter.addEventListener("change", () => {
  savePreference(preferenceKeys.storeFilter, elements.storeFilter.value);
  state.salesPage = 0;
  state.movementsPage = 0;
  state.receiptsPage = 0;
  state.receiptReportPage = 0;
  loadDashboard();
});
elements.useCurrentStoreSaleButton.addEventListener("click", () => {
  applyCurrentStoreTo(elements.saleStore, preferenceKeys.saleStore);
  refreshSaleItemsOptions();
  setSaleFormStatus("Loja atual aplicada ao formulario de venda.", "success");
});
elements.useCurrentStoreTransferButton.addEventListener("click", () => {
  applyCurrentStoreTo(elements.transferSourceStore, preferenceKeys.transferSourceStore);
  refreshTransferVariantOptions();
  renderTransferPreview();
  setTransferStatus("Loja atual aplicada como origem da transferencia.", "success");
});
elements.swapTransferStoresButton.addEventListener("click", () => {
  const source = elements.transferSourceStore.value;
  elements.transferSourceStore.value = elements.transferDestinationStore.value;
  elements.transferDestinationStore.value = source;
  savePreference(preferenceKeys.transferSourceStore, elements.transferSourceStore.value);
  savePreference(preferenceKeys.transferDestinationStore, elements.transferDestinationStore.value);
  refreshTransferVariantOptions();
  renderTransferPreview();
  setTransferStatus("Origem e destino invertidos na transferencia.", "success");
});
elements.useCurrentStoreCountButton.addEventListener("click", () => {
  applyCurrentStoreTo(elements.countStore, preferenceKeys.countStore);
  refreshCountVariantOptions();
  renderCountPreview();
  setCountStatus("Loja atual aplicada ao formulario de contagem.", "success");
});
elements.salesVariantQuery.addEventListener("input", () => {
  persistFilterPreferences();
  refreshSaleItemsOptions();
});
elements.salesStatusQuery.addEventListener("change", () => {
  persistFilterPreferences();
  state.salesPage = 0;
  loadDashboard();
});
[
  elements.salesDateFrom,
  elements.salesDateTo,
].forEach((input) => {
  input.addEventListener("change", () => {
    persistFilterPreferences();
    state.salesPage = 0;
    loadDashboard();
  });
});
elements.dashboardDays.addEventListener("change", () => {
  persistFilterPreferences();
  loadDashboard();
});
elements.dashboardTopLimit.addEventListener("change", () => {
  persistFilterPreferences();
  loadDashboard();
});
elements.salesPrevPage.addEventListener("click", () => {
  state.salesPage = Math.max(0, state.salesPage - 1);
  loadDashboard();
});
elements.salesNextPage.addEventListener("click", () => {
  if ((state.salesPage + 1) * state.salesPageSize < state.salesTotal) {
    state.salesPage += 1;
    loadDashboard();
  }
});
elements.movementsPrevPage.addEventListener("click", () => {
  state.movementsPage = Math.max(0, state.movementsPage - 1);
  loadDashboard();
});
elements.movementsNextPage.addEventListener("click", () => {
  if ((state.movementsPage + 1) * state.movementsPageSize < state.movementsTotal) {
    state.movementsPage += 1;
    loadDashboard();
  }
});
elements.exportMovementsButton.addEventListener("click", () => {
  exportMovementsCsv();
});
elements.exportReceiptButton.addEventListener("click", () => {
  exportSelectedReceiptCsv();
});
elements.loadReceiptIntoEntryButton.addEventListener("click", () => {
  loadSelectedReceiptIntoEntryForm();
});
elements.printReceiptButton.addEventListener("click", () => {
  printSelectedReceiptSummary();
});
elements.draftReceiptsQuery.addEventListener("input", () => {
  state.draftReceiptsQuery = elements.draftReceiptsQuery.value;
  persistFilterPreferences();
  state.draftReceiptsPage = 0;
  loadDashboard();
});
elements.draftReceiptsSensitiveOnly.addEventListener("change", () => {
  state.draftReceiptsSensitiveOnly = elements.draftReceiptsSensitiveOnly.checked;
  if (!state.draftReceiptsSensitiveOnly) {
    state.draftReceiptsCriticalOnly = false;
  }
  persistFilterPreferences();
  state.draftReceiptsPage = 0;
  loadDashboard();
});
elements.showCriticalDraftsButton.addEventListener("click", () => {
  state.draftReceiptsCriticalOnly = !state.draftReceiptsCriticalOnly;
  if (state.draftReceiptsCriticalOnly) {
    state.draftReceiptsSensitiveOnly = true;
    elements.draftReceiptsSensitiveOnly.checked = true;
  }
  persistFilterPreferences();
  state.draftReceiptsPage = 0;
  loadDashboard();
});
elements.bulkApproveDraftsButton.addEventListener("click", () => {
  bulkApproveSelectedDrafts();
});
elements.draftReceiptsSort.addEventListener("change", () => {
  persistFilterPreferences();
  state.draftReceiptsPage = 0;
  renderDraftReceiptsQueue(state.draftReceipts, state.draftReceiptsTotal);
});
elements.draftsPrevPage.addEventListener("click", () => {
  state.draftReceiptsPage = Math.max(0, state.draftReceiptsPage - 1);
  loadDashboard();
});
elements.draftsNextPage.addEventListener("click", () => {
  state.draftReceiptsPage += 1;
  loadDashboard();
});
elements.receiptsPrevPage.addEventListener("click", () => {
  state.receiptsPage = Math.max(0, state.receiptsPage - 1);
  loadDashboard();
});
elements.receiptsNextPage.addEventListener("click", () => {
  if ((state.receiptsPage + 1) * state.receiptsPageSize < state.receiptsTotal) {
    state.receiptsPage += 1;
    loadDashboard();
  }
});
elements.bulkPostDraftsButton.addEventListener("click", () => {
  bulkPostSelectedDrafts();
});
elements.bulkDiscardDraftsButton.addEventListener("click", () => {
  bulkDiscardSelectedDrafts();
});
elements.receiptReportSort.addEventListener("change", () => {
  persistFilterPreferences();
  state.receiptReportPage = 0;
  loadDashboard();
});
elements.receiptReportQuery.addEventListener("input", () => {
  state.receiptReportQuery = elements.receiptReportQuery.value;
  persistFilterPreferences();
  state.receiptReportPage = 0;
  loadDashboard();
});
[
  elements.receiptReportDateFrom,
  elements.receiptReportDateTo,
].forEach((input) => {
  input.addEventListener("change", () => {
    state.receiptReportDateFrom = elements.receiptReportDateFrom.value;
    state.receiptReportDateTo = elements.receiptReportDateTo.value;
    persistFilterPreferences();
    state.receiptReportPage = 0;
    loadDashboard();
  });
});
elements.receiptReportSensitiveOnly.addEventListener("change", () => {
  state.receiptReportSensitiveOnly = elements.receiptReportSensitiveOnly.checked;
  persistFilterPreferences();
  renderReceiptReport(
    state.receiptReportRaw,
    state.receiptReportTotal,
    state.receiptReportPageSize,
    state.receiptReportPage * state.receiptReportPageSize,
  );
});
elements.receiptReportPrevPage.addEventListener("click", () => {
  state.receiptReportPage = Math.max(0, state.receiptReportPage - 1);
  loadDashboard();
});
elements.receiptReportNextPage.addEventListener("click", () => {
  if ((state.receiptReportPage + 1) * state.receiptReportPageSize < state.receiptReportTotal) {
    state.receiptReportPage += 1;
    loadDashboard();
  }
});
elements.printReceiptReportButton.addEventListener("click", () => {
  printReceiptReportSummary();
});
elements.exportReceiptReportButton.addEventListener("click", () => {
  exportReceiptReportCsv();
});
elements.receiptAuditFilter.addEventListener("change", () => {
  state.receiptAuditFilter = elements.receiptAuditFilter.value;
  const detail = state.receiptDetailsById.get(state.selectedReceiptId);
  renderReceiptDetail(detail || null);
});
elements.saveEntryDraftButton.addEventListener("click", () => {
  saveEntryDraft();
});
elements.cancelEntryEditButton.addEventListener("click", () => {
  resetEntryFormState();
  setEntryStatus("Edicao do rascunho cancelada e formulario liberado para um novo recebimento.", "muted");
});
[
  elements.productQuery,
  elements.skuQuery,
  elements.barcodeQuery,
  elements.movementTypeQuery,
  elements.movementSupplierQuery,
  elements.movementDocumentQuery,
  elements.receiptStatusQuery,
].forEach((input) => {
  input.addEventListener("input", () => {
    persistFilterPreferences();
    if (
      input === elements.productQuery
      || input === elements.skuQuery
      || input === elements.barcodeQuery
    ) {
      return;
    }
    if (
      input === elements.movementTypeQuery
      || input === elements.movementSupplierQuery
      || input === elements.movementDocumentQuery
    ) {
      state.movementsPage = 0;
      if (input === elements.movementSupplierQuery || input === elements.movementDocumentQuery) {
        state.receiptsPage = 0;
        state.receiptReportPage = 0;
      }
    }
    loadDashboard();
  });
});
elements.receiptStatusQuery.addEventListener("change", () => {
  persistFilterPreferences();
  state.receiptsPage = 0;
  loadDashboard();
});
[
  elements.movementDateFrom,
  elements.movementDateTo,
].forEach((input) => {
  input.addEventListener("change", () => {
    persistFilterPreferences();
    state.movementsPage = 0;
    state.receiptsPage = 0;
    state.receiptReportPage = 0;
    loadDashboard();
  });
});
elements.logoutButton.addEventListener("click", () => {
  clearSession();
  setStatus("Sessao local encerrada neste navegador.", "muted");
  setTransferStatus("Transferencias reais exigem perfil admin ou manager com acesso as duas lojas.", "muted");
});

elements.workflowTabs.forEach((button) => {
  button.addEventListener("click", () => {
    setActiveWorkspace(button.dataset.workspace);
  });
});

document.querySelectorAll("[data-load]").forEach((button) => {
  button.addEventListener("click", () => {
    loadDashboard();
    if (button.dataset.target) {
      setTimeout(() => scrollToTarget(button.dataset.target), 50);
    }
  });
});

document.querySelectorAll("[data-target]").forEach((button) => {
  button.addEventListener("click", () => {
    if (button.dataset.target) {
      setTimeout(() => scrollToTarget(button.dataset.target), 50);
    }
  });
});

elements.runScenarioButton.addEventListener("click", runScenario);
elements.runReplenishmentButton.addEventListener("click", runReplenishment);
elements.runSupplierRiskButton.addEventListener("click", refreshSupplierRisk);
elements.saveSupplierDeliveryButton.addEventListener("click", saveSupplierDelivery);
elements.replenishmentList.addEventListener("click", (event) => {
  const button = event.target.closest(".replenishment-decision");
  if (button) decideReplenishment(button);
});

restorePreferences();
setActiveWorkspace(state.activeWorkspace);
setSessionStatus();
elements.entryItems.appendChild(createEntryItemRow());
elements.saleItems.appendChild(createSaleItemRow());
loadHealth();
if (state.token) {
  setStatus("Sessao restaurada neste navegador.", "success");
}
loadDashboard();

