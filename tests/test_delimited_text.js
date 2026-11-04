import test from 'node:test';
import assert from 'node:assert/strict';
import { parseDelimitedRows } from '../static/js/modules/delimited-text.js';

test('import preview keeps quoted separators, quotes and multiline fields together', () => {
    assert.deepEqual(parseDelimitedRows('\uFEFF"Grüße, ""hello""","first\r\nsecond"\r\nCat,Katze\r\n', '\n', ','),
        [['Grüße, "hello"', 'first\r\nsecond'], ['Cat', 'Katze']]);
});

test('TSV and custom TXT previews use their selected separators', () => {
    assert.deepEqual(parseDelimitedRows('Dog\tHund\r\nCat\tKatze', '\n', '\t'), [['Dog', 'Hund'], ['Cat', 'Katze']]);
    assert.deepEqual(parseDelimitedRows('Dog -> Hund || Cat -> Katze', ' || ', ' -> '), [['Dog', 'Hund'], ['Cat', 'Katze']]);
});
