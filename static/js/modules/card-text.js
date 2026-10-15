/** Interpret escaped newlines without changing the stored card text. */
export function formatCardText(text) {
    return text.replace(/\\r\\n|\\n|\\r/g, '\n');
}
