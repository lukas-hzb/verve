import { DOMSerializer, Fragment, Schema, Slice } from 'prosemirror-model';
import { EditorState } from 'prosemirror-state';
import { EditorView } from 'prosemirror-view';
import { defaultMarkdownParser, defaultMarkdownSerializer, MarkdownParser, MarkdownSerializer, schema as baseSchema } from 'prosemirror-markdown';
import { baseKeymap, chainCommands, setBlockType, toggleMark } from 'prosemirror-commands';
import { keymap } from 'prosemirror-keymap';
import { history, redo, undo } from 'prosemirror-history';
import { liftListItem, sinkListItem, splitListItem, wrapInList } from 'prosemirror-schema-list';

const schema = new Schema({
    nodes: baseSchema.spec.nodes,
    marks: baseSchema.spec.marks.addBefore('code', 'level_color', {
        attrs: { level: { validate: 'string' } },
        parseDOM: [{
            tag: 'mark[data-level]',
            getAttrs: element => /^[1-5]$/.test(element.dataset.level) ? { level: element.dataset.level } : false,
        }],
        toDOM: mark => ['mark', { 'data-level': mark.attrs.level }, 0],
    }),
});

const tokenizer = defaultMarkdownParser.tokenizer;
// Recognize only Verve's paired color markers, while leaving arbitrary HTML disabled.
tokenizer.inline.ruler.before('html_inline', 'level_color', (state, silent) => {
    if (state.src[state.pos] !== '<') return false;
    const opening = /^<mark data-level="([1-5])">/.exec(state.src.slice(state.pos, state.pos + 21));
    if (!opening) return false;
    const start = state.pos + opening[0].length;
    const end = state.src.indexOf('</mark>', start);
    if (end <= start || end + 7 > state.posMax) return false;
    if (!silent) {
        state.push('level_color_open', 'mark', 1).attrSet('data-level', opening[1]);
        const max = state.posMax;
        state.pos = start;
        state.posMax = end;
        tokenizer.inline.tokenize(state);
        state.posMax = max;
        state.push('level_color_close', 'mark', -1);
    }
    state.pos = end + 7;
    return true;
});

const parser = new MarkdownParser(schema, tokenizer, {
    ...defaultMarkdownParser.tokens,
    softbreak: { node: 'hard_break' },
    level_color: { mark: 'level_color', getAttrs: token => ({ level: token.attrGet('data-level') }) },
});

const serializer = new MarkdownSerializer(defaultMarkdownSerializer.nodes, {
    ...defaultMarkdownSerializer.marks,
    level_color: {
        open: (_state, mark) => '<mark data-level="' + mark.attrs.level + '">',
        close: '</mark>',
        mixable: true,
    },
});

const linkProtocols = ['http:', 'https:', 'mailto:'];

function safeUrl(value, protocols) {
    try {
        const url = new URL(value);
        return protocols.includes(url.protocol) && !url.username && !url.password;
    } catch {
        return false;
    }
}

// Apply the same URL restrictions to pasted HTML and parsed Markdown.
function safeContent(fragment) {
    const children = [];
    fragment.forEach(node => {
        if (node.type === schema.nodes.image && !safeUrl(node.attrs.src, ['https:'])) {
            if (node.attrs.alt) children.push(schema.text(node.attrs.alt));
            return;
        }
        const marks = node.marks.filter(mark => mark.type !== schema.marks.link
            || safeUrl(mark.attrs.href, linkProtocols));
        children.push(node.copy(safeContent(node.content)).mark(marks));
    });
    return Fragment.fromArray(children);
}

function parse(source) {
    const doc = parser.parse(source);
    return doc.copy(safeContent(doc.content));
}

export function renderMarkdown(element, source, { lazy = false } = {}) {
    const fragment = DOMSerializer.fromSchema(schema).serializeFragment(parse(source).content);
    fragment.querySelectorAll('a[href]').forEach(link => {
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
    });
    fragment.querySelectorAll('img').forEach(image => {
        image.referrerPolicy = 'no-referrer';
        image.loading = lazy ? 'lazy' : 'eager';
        image.decoding = 'async';
    });
    element.replaceChildren(fragment);
}

export function plainToMarkdown(text, parseImage) {
    const blocks = text.split(/\n{2,}/).map(paragraph => {
        const lines = paragraph.split('\n');
        const content = [];
        lines.forEach((line, index) => {
            if (index) content.push(schema.nodes.hard_break.create());
            const image = parseImage(line);
            if (image) content.push(schema.nodes.image.create({ src: image.url, alt: image.alt }));
            else if (line) content.push(schema.text(line));
        });
        return schema.nodes.paragraph.create(null, content);
    });
    return defaultMarkdownSerializer.serialize(schema.nodes.doc.create(null, blocks));
}

function listCommand(type) {
    return (state, dispatch) => {
        const { $from } = state.selection;
        for (let depth = $from.depth; depth > 0; depth--) {
            const list = $from.node(depth);
            if (list.type !== schema.nodes.bullet_list && list.type !== schema.nodes.ordered_list) continue;
            if (list.type === type) return liftListItem(schema.nodes.list_item)(state, dispatch);
            if (dispatch) dispatch(state.tr.setNodeMarkup($from.before(depth), type, { tight: list.attrs.tight }).scrollIntoView());
            return true;
        }
        return wrapInList(type)(state, dispatch);
    };
}

const commands = {
    bold: toggleMark(schema.marks.strong),
    italic: toggleMark(schema.marks.em),
    bullets: listCommand(schema.nodes.bullet_list),
    numbered: listCommand(schema.nodes.ordered_list),
    indent: sinkListItem(schema.nodes.list_item),
    outdent: liftListItem(schema.nodes.list_item),
};

function selectedMarkRange(selection, type, expectedMark) {
    const { $from, $to } = selection;
    if (!$from.sameParent($to)) return null;
    let previousMark = null;
    let start = 0;
    let result = null;
    $from.parent.forEach((node, offset) => {
        const mark = type.isInSet(node.marks);
        if (!mark || !previousMark || !mark.eq(previousMark)) start = offset;
        previousMark = mark;
        const end = offset + node.nodeSize;
        if (mark && (!expectedMark || mark.eq(expectedMark)) && start <= $from.parentOffset && end >= $to.parentOffset) {
            result = { mark, from: $from.start() + start, to: $from.start() + end };
        }
    });
    return result;
}

function selectedColor({ doc, selection, storedMarks }) {
    const type = schema.marks.level_color;
    if (selection.empty) return type.isInSet(storedMarks ?? selection.$from.marks())?.attrs.level;

    let level;
    let mixed = false;
    for (const { $from, $to } of selection.ranges) {
        doc.nodesBetween($from.pos, $to.pos, node => {
            if (mixed) return false;
            if (!node.isInline || node.type === schema.nodes.hard_break) return;
            const next = type.isInSet(node.marks)?.attrs.level ?? null;
            if (level === undefined) level = next;
            else if (level !== next) mixed = true;
        });
    }
    return mixed ? undefined : level;
}

export function mountMarkdownEditor(container, source, attributes, onChange, onColorChange) {
    const view = new EditorView(container, {
        state: EditorState.create({
            doc: parse(source),
            plugins: [history(), keymap({
                'Mod-b': commands.bold,
                'Mod-i': commands.italic,
                'Mod-z': undo,
                'Mod-Shift-z': redo,
                Tab: commands.indent,
                'Shift-Tab': commands.outdent,
                'Mod-[': commands.outdent,
                'Mod-]': commands.indent,
                Enter: chainCommands(splitListItem(schema.nodes.list_item), baseKeymap.Enter),
            }), keymap(baseKeymap)],
        }),
        attributes: { ...attributes, role: 'textbox', 'aria-multiline': 'true' },
        transformPasted: slice => new Slice(safeContent(slice.content), slice.openStart, slice.openEnd),
        dispatchTransaction(transaction) {
            this.updateState(this.state.apply(transaction));
            if (transaction.docChanged) onChange(serializer.serialize(this.state.doc));
            if (transaction.docChanged || transaction.selectionSet || transaction.storedMarksSet) {
                onColorChange(selectedColor(this.state));
            }
        },
    });
    onColorChange(selectedColor(view.state));
    return {
        destroy: () => view.destroy(),
        run(command) {
            commands[command](view.state, view.dispatch);
            view.focus();
        },
        heading(level) {
            const type = level ? schema.nodes.heading : schema.nodes.paragraph;
            setBlockType(type, level ? { level } : null)(view.state, view.dispatch);
            view.focus();
        },
        linkHref() {
            return selectedMarkRange(view.state.selection, schema.marks.link)?.mark.attrs.href || '';
        },
        setLink(value) {
            if (value && !safeUrl(value, linkProtocols)) return false;
            const href = value ? new URL(value).href : '';
            const { selection, tr } = view.state;
            const type = schema.marks.link;
            const existing = selectedMarkRange(selection, type);
            const { from, to } = existing ?? selection;
            if (href && from === to) {
                tr.replaceSelectionWith(schema.text(href, [type.create({ href })]), false);
            } else if (from !== to) {
                tr.removeMark(from, to, type);
                if (href) tr.addMark(from, to, type.create({ ...existing?.mark.attrs, href }));
            }
            if (selection.empty) tr.removeStoredMark(type);
            view.dispatch(tr);
            view.focus();
            return true;
        },
        color(level) {
            const mark = schema.marks.level_color;
            const { selection, tr } = view.state;
            const active = selectedColor(view.state);
            const color = level && level !== active ? mark.create({ level }) : null;
            if (selection.empty) {
                if (!level && active) {
                    const range = selectedMarkRange(selection, mark, mark.create({ level: active }));
                    if (range) tr.removeMark(range.from, range.to, mark);
                }
                tr.removeStoredMark(mark);
                if (color) tr.addStoredMark(color);
            } else {
                selection.ranges.forEach(({ $from, $to }) => {
                    tr.removeMark($from.pos, $to.pos, mark);
                    if (color) tr.addMark($from.pos, $to.pos, color);
                });
            }
            view.dispatch(tr);
            view.focus();
        },
    };
}
