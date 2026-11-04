import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

test('home search finds contained sets, normalizes names, and restores the grid on clear', () => {
    const input = new EventTarget();
    const card = (name, contents = []) => ({
        style: {}, dataset: {containedSetNames: JSON.stringify(contents)},
        querySelector: () => ({textContent: name}),
    });
    const folder = card('Languages', ['Cursus_Grundwortschatz', 'Everyday Words']);
    const direct = card('Flaggen der Welt');
    const create = {style: {}};
    const grid = {
        querySelectorAll: () => [folder, direct],
        querySelector: () => create,
    };
    const document = {
        getElementById: id => ({setSearchInput: input, setsGrid: grid})[id],
        addEventListener() {},
        querySelectorAll() { throw new Error('Home search must not filter cards inside folder popups'); },
    };
    const source = readFileSync(new URL('../static/js/app.js', import.meta.url), 'utf8').replace(/^import .*;$/gm, '');
    runInNewContext(source + '\ninitializeSearchBar();', {document});
    const search = term => { input.value = term; input.dispatchEvent(new Event('input')); };
    search('  CURSUS GRUNDWORTSCHATZ  ');
    assert.equal(folder.style.display, '');
    assert.equal(direct.style.display, 'none');
    assert.equal(create.style.display, 'none');
    search('Languages');
    assert.equal(folder.style.display, '');
    search('flaggen');
    assert.equal(folder.style.display, 'none');
    assert.equal(direct.style.display, '');
    search('not present');
    assert.equal(folder.style.display, 'none');
    assert.equal(direct.style.display, 'none');
    search('');
    assert.equal(folder.style.display, '');
    assert.equal(direct.style.display, '');
    assert.equal(create.style.display, '');
});
