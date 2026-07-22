import { FileUploadHandler } from "frappe-ui";

function parseUploadError(err) {
	if (!err) return "Upload failed";
	if (typeof err === "string") return err;
	if (err.message && typeof err.message === "string" && !err._server_messages) {
		return err.message;
	}
	if (err._error_message) return err._error_message;
	if (err._server_messages) {
		try {
			const msgs = JSON.parse(err._server_messages);
			const text = msgs
				.map((m) => {
					try {
						return JSON.parse(m).message;
					} catch {
						return m;
					}
				})
				.filter(Boolean)
				.join("\n");
			if (text) return text;
		} catch {
			/* ignore */
		}
	}
	return err.message || "Upload failed";
}

/**
 * Upload a browser File and attach it to a document.
 * Returns the File doc dict from Frappe (`name`, `file_name`, `file_url`, …).
 */
export async function uploadDocFile(file, { doctype, docname, isPrivate = false } = {}) {
	if (!file) throw new Error("No file selected");
	if (!doctype || !docname) throw new Error("Document is required for upload");

	const handler = new FileUploadHandler();
	try {
		return await handler.upload(file, {
			doctype,
			docname,
			private: isPrivate,
			folder: "Home",
		});
	} catch (err) {
		throw new Error(parseUploadError(err));
	}
}
