/** Parse the same quoted rows accepted by the CSV/TSV importer. */
export function parseDelimitedRows(content, cardSeparator, fieldSeparator, { preserveWhitespace = false } = {}) {
    content = content.replace(/^\uFEFF/, '');
    if (cardSeparator !== '\n' || fieldSeparator.length !== 1 || /[\r\n"]/.test(fieldSeparator)) {
        if ([cardSeparator, fieldSeparator].some(separator => separator.includes('\n') && !separator.includes('\r'))) {
            content = content.replace(/\r\n/g, '\n');
        }
        const rows = cardSeparator === '\n' ? content.split(/\r\n|\r|\n/) : content.split(cardSeparator);
        return rows.filter(row => row.trim()).map(row => (preserveWhitespace ? row : row.trim()).split(fieldSeparator));
    }
    const rows = [];
    let row = [], field = '', quoted = false;
    for (let i = 0; i < content.length; i++) {
        const char = content[i];
        if (quoted) {
            if (char === '"' && content[i + 1] === '"') { field += '"'; i++; }
            else if (char === '"') quoted = false;
            else field += char;
        } else if (char === '"' && !field) quoted = true;
        else if (char === fieldSeparator) { row.push(field); field = ''; }
        else if (char === '\n' || char === '\r') {
            row.push(field);
            rows.push(row);
            row = []; field = '';
            if (char === '\r' && content[i + 1] === '\n') i++;
        } else field += char;
    }
    if (field || row.length) rows.push([...row, field]);
    return rows;
}
