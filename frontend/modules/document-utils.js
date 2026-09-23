/** Shared browser utilities for CSV downloads and printable documents. */

export function downloadBlob(filename, blob) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function downloadCsv(filename, rows) {
  const csv = rows
    .map((row) => row.map((value) => `"${String(value ?? "").replaceAll('"', '""')}"`).join(","))
    .join("\n");
  downloadBlob(filename, new Blob([csv], { type: "text/csv;charset=utf-8;" }));
}

export function buildCsvRows(headers, items, mapRow) {
  return [headers, ...items.map((item, index) => mapRow(item, index))];
}

export function openPrintDocument(content, options = {}) {
  const { width = 900, height = 700 } = options;
  const printWindow = window.open("", "_blank", `width=${width},height=${height}`);
  if (!printWindow) {
    return null;
  }
  printWindow.document.write(content);
  printWindow.document.close();
  printWindow.focus();
  printWindow.print();
  return printWindow;
}

export function buildPrintStyles(options = {}) {
  const {
    margin = 24,
    color = "#1a1a1a",
    headingMargin = "0 0 12px",
    tableMarginTop = 20,
    borderColor = "#ccc",
    headerBackground = "#f3f3f3",
    paragraphColor = "",
    listMarginTop = 10,
    listPaddingLeft = 20,
  } = options;
  const paragraphStyle = paragraphColor
    ? `p { margin: 4px 0; color: ${paragraphColor}; }`
    : "p { margin: 4px 0; }";
  return `
    body { font-family: Arial, sans-serif; margin: ${margin}px; color: ${color}; }
    h1 { margin: ${headingMargin}; }
    h2 { margin: 0 0 10px; }
    ${paragraphStyle}
    table { width: 100%; border-collapse: collapse; margin-top: ${tableMarginTop}px; }
    th, td { border: 1px solid ${borderColor}; padding: 10px; text-align: left; }
    th { background: ${headerBackground}; }
    ul { margin-top: ${listMarginTop}px; padding-left: ${listPaddingLeft}px; }
  `;
}

export function buildPrintHtmlDocument(title, body, styleOptions = {}) {
  return `
    <!DOCTYPE html>
    <html lang="pt-BR">
      <head>
        <meta charset="UTF-8">
        <title>${title}</title>
        <style>${buildPrintStyles(styleOptions)}</style>
      </head>
      <body>${body}</body>
    </html>
  `;
}
