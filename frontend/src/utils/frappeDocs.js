/**
 * Thin helpers that call Frappe Desk / core endpoints.
 * Do not reinvent print/import/export — use DocType + framework APIs.
 */

/**
 * Same as Desk `frm.print_doc()` → route `print/{doctype}/{name}`.
 * Opens the standard ERPNext print page (format picker, letterhead, PDF).
 */
export function openPrintView(doctype, name) {
	if (!doctype || !name) return;
	window.open(
		`/app/print/${encodeURIComponent(doctype)}/${encodeURIComponent(name)}`,
		"_blank",
	);
}

/** Download PDF via frappe.utils.print_format.download_pdf (Standard format). */
export function downloadPdf(doctype, name, printFormat = "Standard") {
	if (!doctype || !name) return;
	const q = new URLSearchParams({
		doctype,
		name,
		format: printFormat,
		no_letterhead: "0",
	});
	window.open(`/api/method/frappe.utils.print_format.download_pdf?${q.toString()}`, "_blank");
}

/**
 * List export via frappe.desk.reportview.export_query (same as Desk / FCRM).
 * @param {{ doctype: string, fields: string[], filters?: object, order_by?: string, page_length?: number, selected_items?: string[], file_format_type?: 'Excel'|'CSV', title?: string }} opts
 */
export function exportQuery(opts) {
	const {
		doctype,
		fields,
		filters = {},
		order_by = "modified desc",
		page_length = 20,
		selected_items = [],
		file_format_type = "Excel",
		title,
	} = opts;

	const params = new URLSearchParams({
		file_format_type,
		title: title || doctype,
		doctype,
		fields: JSON.stringify(fields),
		filters: JSON.stringify(filters),
		order_by,
		page_length: String(page_length),
		start: "0",
		view: "Report",
		with_comment_count: "1",
	});

	if (selected_items?.length) {
		params.set("selected_items", JSON.stringify(selected_items));
	}

	window.location.href = `/api/method/frappe.desk.reportview.export_query?${params.toString()}`;
}
