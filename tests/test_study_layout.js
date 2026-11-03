import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';

test('Safari viewport height changes preserve the initial card position', () => {
    let width = 358;
    let headingHeight = 142;
    let observerCallback;
    let resize;
    let writes = 0;
    const properties = new Map();
    const above = {
        get offsetHeight() { return headingHeight; },
        getBoundingClientRect: () => ({ bottom: 56 + headingHeight - window.scrollY }),
    };
    const actions = { offsetHeight: 56, getBoundingClientRect: () => ({ height: 56 }) };
    const toolbar = { getBoundingClientRect: () => ({ top: window.innerHeight - 56 }) };
    const progress = { before() {}, getBoundingClientRect: () => ({ height: 33 }) };
    const group = { prepend() {} };
    const page = {
        getBoundingClientRect: () => ({ width }),
        querySelector: selector => ({
            '.study-above-card': above, '.study-actions': actions,
            '.study-progress': progress, '.study-card-and-actions': group,
        })[selector],
        style: { setProperty: (name, value) => { properties.set(name, value); writes++; } },
    };
    const window = {
        innerHeight: 759,
        scrollY: 0,
        matchMedia: () => ({ matches: true, addEventListener() {} }),
        addEventListener: (name, callback) => { if (name === 'resize') resize = callback; },
    };
    const document = {
        addEventListener() {},
        createComment: () => ({ after() {} }),
        querySelector: selector => selector === '.study-page' ? page : toolbar,
    };
    const source = readFileSync(new URL('../static/js/app.js', import.meta.url), 'utf8')
        .replace(/^import .*;$/gm, '');
    runInNewContext(source + '\ninitializeStudyCardPosition();', {
        window, document,
        ResizeObserver: class {
            constructor(callback) { observerCallback = callback; }
            observe() {}
        },
    });
    const initial = new Map(properties);
    assert.equal(writes, 2);

    // Safari hides/reveals browser chrome during the same scroll gesture.
    window.scrollY = 30;
    window.innerHeight = 820;
    resize();
    observerCallback();
    window.innerHeight = 700;
    resize();
    observerCallback();
    assert.equal(writes, 2);
    assert.deepEqual(properties, initial);

    // A rotation or a reflow of the heading still updates the initial layout.
    width = 398;
    resize();
    assert.equal(writes, 4);
    headingHeight = 170;
    observerCallback();
    assert.equal(writes, 6);
});
