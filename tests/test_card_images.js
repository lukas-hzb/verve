import test from 'node:test';
import assert from 'node:assert/strict';
import { parseCardImage, renderCardContent } from '../static/js/modules/card-text.js';
import { FlashcardManager } from '../static/js/modules/flashcard.js';

test('only HTTPS image lines are rendered; text and unsafe URLs stay text', () => {
    assert.equal(parseCardImage('https://flagcdn.com/de.svg').url, 'https://flagcdn.com/de.svg');
    assert.equal(parseCardImage(' ![Map](https://example.com/image?id=1) ').alt, 'Map');
    for (const value of ['http://example.com/a.png', 'javascript:alert(1)', 'data:image/svg+xml,x',
        'https://user:password@example.com/a.png', '<img src=x onerror=alert(1)>',
        'See https://example.com/a.png', 'https://example.com/page']) {
        assert.equal(parseCardImage(value), null, value);
    }
});

function installCardDom(t) {
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
    return Node;
}

test('mixed card content uses images and literal text, with an error fallback', t => {
    const Node = installCardDom(t);
    const element = new Node('p');
    renderCardContent(element, 'https://flagcdn.com/de.svg\\n\\n<img src=x onerror=alert(1)>');
    const wrapper = element.children[0];
    const img = wrapper.children[0];
    assert.equal(img.tag, 'img');
    assert.equal(img.src, 'https://flagcdn.com/de.svg');
    assert.equal(img.referrerPolicy, 'no-referrer');
    assert.equal(img.alt, 'Card Image');
    assert.equal(element.textContent, '\n\n<img src=x onerror=alert(1)>');
    img.events.error();
    assert.equal(wrapper.textContent, 'Image unavailable');
    renderCardContent(element, 'Next card');
    assert.equal(element.textContent, 'Next card');
    assert.equal(element.children.length, 1);
});

test('study cards space explicit breaks while preserving the original text', t => {
    const Node = installCardDom(t);
    const manager = Object.assign(Object.create(FlashcardManager.prototype), {
        cardFront: new Node('p'), cardBack: new Node('p'), cardLevels: [],
        updateCompletionAction() {}, flashcard: { classList: { toggle() {} } },
    });
    const card = { front: 'First\\n\\nSecond', back: 'Answer\r\n<img src=x onerror=alert(1)>', level: 1 };
    manager.updateCardContent(card);
    assert.equal(manager.cardFront.textContent, 'First\n\nSecond');
    assert.equal(manager.cardBack.textContent, 'Answer\n<img src=x onerror=alert(1)>');
    const lines = element => element.children.filter(child => child.className === 'card-text-line')
        .map(line => line.textContent);
    assert.deepEqual(lines(manager.cardFront), ['First', '', 'Second']);
    assert.deepEqual(lines(manager.cardBack), ['Answer', '<img src=x onerror=alert(1)>']);
    assert.equal(card.front, 'First\\n\\nSecond');
    manager.updateCardContent({ front: 'First\\r\\nSecond', back: 'Plain answer', level: 1 });
    assert.deepEqual(lines(manager.cardFront), ['First', 'Second']);
    assert.deepEqual(manager.cardBack.children, ['Plain answer']);
});
