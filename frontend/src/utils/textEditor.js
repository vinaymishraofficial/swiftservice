/** TextEditor toolbar items that do NOT use async Vue components (InsertLink etc.).
 * Those async chunks crash this app with: can't access property "ce", … is null
 */
export const SAFE_TEXT_EDITOR_BUTTONS = [
	"Bold",
	"Italic",
	"Strikethrough",
	"Separator",
	"Bullet List",
	"Numbered List",
	"Separator",
	"Undo",
	"Redo",
];
