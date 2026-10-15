import test from 'node:test';
import assert from 'node:assert/strict';
import { parseCardImage, renderCardContent } from '../static/js/modules/card-text.js';

test('only HTTPS image lines are rendered; text and unsafe URLs stay text', () => {
    assert.equal(parseCardImage('https://flagcdn.com/de.svg').url, 'https://flagcdn.com/de.svg');
    assert.equal(parseCardImage(' ![Map](https://example.com/image?id=1) ').alt, 'Map');
    for (const value of ['http://example.com/a.png', 'javascript:alert(1)', 'data:image/svg+xml,x',
        'https://user:password@example.com/a.png', '<img src=x onerror=alert(1)>',
        'See https://example.com/a.png', 'https://example.com/page']) {
        assert.equal(parseCardImage(value), null, value);
    }
});

test('mixed card content uses images and literal text, with an error fallback', t => {
    class Node {
        children = [];
        events = {};
        classes = new Set();
        classList = { add: value => this.classes.add(value) };
        constructor(tag) { this.tag = tag; }
        append(...nodes) { this.children.push(...nodes); }
        replaceChildren(fragment) { this.children = fragment.children; }
        set textContent(value) { this.children = [value]; }
        get textContent() { return this.children.map(node => typeof node === 'string' ? node : node.textContent).join(''); }
        addEventListener(event, handler) { this.events[event] = handler; }
    }
    const previous = globalThis.document;
    globalThis.document = {
        createDocumentFragment: () => new Node('fragment'),
        createElement: tag => new Node(tag),
        createTextNode: text => text,
    };
    t.after(() => { globalThis.document = previous; });
    const element = new Node('p');
    renderCardContent(element, 'https://flagcdn.com/de.svg\\n\\n<img src=x onerror=alert(1)>');
    const wrapper = element.children[0];
    const img = wrapper.children[0];
    assert.equal(img.tag, 'img');
    assert.equal(img.src, 'https://flagcdn.com/de.svg');
    assert.equal(img.referrerPolicy, 'no-referrer');
    assert.equal(img.alt, 'Card image');
    assert.equal(element.textContent, '\n\n<img src=x onerror=alert(1)>');
    img.events.error();
    assert.equal(wrapper.textContent, 'Image unavailable');
    renderCardContent(element, 'Next card');
    assert.equal(element.textContent, 'Next card');
    assert.equal(element.children.length, 1);
});
