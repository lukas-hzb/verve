import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { buildSync } from 'esbuild';

const source = readFileSync(new URL('../frontend/card-markdown.js', import.meta.url), 'utf8');
const { outputFiles } = buildSync({
    stdin: {
        contents: source + '\nimport { TextSelection } from "prosemirror-state";\nexport { parse, serializer, commands, EditorState, TextSelection };',
        resolveDir: new URL('../frontend/', import.meta.url).pathname,
    },
    bundle: true,
    platform: 'node',
    format: 'esm',
    write: false,
});
const { parse, serializer, commands, EditorState, TextSelection } =
    await import('data:text/javascript;base64,' + Buffer.from(outputFiles[0].text).toString('base64'));

function atText(markdown, text) {
    const doc = parse(markdown);
    let position;
    doc.descendants((node, offset) => {
        if (node.isText && node.text === text) position = offset + node.text.length;
    });
    assert.notEqual(position, undefined);
    return EditorState.create({ doc, selection: TextSelection.create(doc, position) });
}

function apply(state, command) {
    let updated;
    assert.equal(command(state, transaction => { updated = state.apply(transaction); }), true);
    return updated;
}

test('nested numbered and bullet lists retain their structure through Markdown serialization', () => {
    const original = parse('1. Parent\n   - Child\n     1. Grandchild\n   - Second child\n2. Next');
    const reloaded = parse(serializer.serialize(original));
    assert.deepEqual(reloaded.toJSON(), original.toJSON());
    assert.equal(reloaded.firstChild.firstChild.lastChild.type.name, 'bullet_list');
    assert.equal(reloaded.firstChild.firstChild.lastChild.firstChild.lastChild.type.name, 'ordered_list');
});

test('indent followed by bullet conversion keeps the outer numbered list', () => {
    let state = atText('1. Parent\n2. Child\n3. Next', 'Child');
    state = apply(state, commands.indent);
    state = apply(state, commands.bullets);
    const outer = state.doc.firstChild;
    assert.equal(outer.type.name, 'ordered_list');
    assert.equal(outer.childCount, 2);
    assert.equal(outer.firstChild.firstChild.textContent, 'Parent');
    assert.equal(outer.firstChild.lastChild.type.name, 'bullet_list');
    assert.equal(outer.firstChild.lastChild.textContent, 'Child');
    assert.equal(outer.lastChild.textContent, 'Next');
    const saved = serializer.serialize(state.doc);
    const reloaded = parse(saved);
    assert.equal(reloaded.firstChild.firstChild.lastChild.type.name, 'bullet_list');
    assert.equal(reloaded.textContent, state.doc.textContent);
    assert.equal(serializer.serialize(reloaded), saved);
});

test('outdent moves a bullet back to the numbered parent level', () => {
    let state = atText('1. Parent\n   - Child\n2. Next', 'Child');
    state = apply(state, commands.outdent);
    assert.equal(state.doc.firstChild.type.name, 'ordered_list');
    assert.deepEqual(
        Array.from({ length: state.doc.firstChild.childCount }, (_, index) => state.doc.firstChild.child(index).textContent),
        ['Parent', 'Child', 'Next'],
    );
});

test('toggling an existing list lifts its item and preserves the text', () => {
    const state = apply(atText('- Example', 'Example'), commands.bullets);
    assert.equal(state.doc.firstChild.type.name, 'paragraph');
    assert.equal(state.doc.textContent, 'Example');
});
