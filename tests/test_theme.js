import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const script = readFileSync(new URL('../static/js/theme.js', import.meta.url), 'utf8');

function fixture({ saved = null, dark = false, blocked = false } = {}) {
    const listeners = new Map();
    const on = (target, name, listener) => listeners.set(`${target}:${name}`, listener);
    const root = { dataset: {} };
    const toggle = {
        attributes: {}, text: {},
        setAttribute(name, value) { this.attributes[name] = value; },
        querySelector() { return this.text; },
        addEventListener(name, listener) { on('toggle', name, listener); },
    };
    const select = { addEventListener(name, listener) { on('select', name, listener); } };
    const system = { matches: dark, addEventListener(name, listener) { on('system', name, listener); } };
    const context = {
        localStorage: {
            getItem() { if (blocked) throw new Error('Storage unavailable'); return saved; },
            setItem(key, value) { if (blocked) throw new Error('Storage unavailable'); saved = value; },
        },
        window: { matchMedia: () => system, addEventListener(name, listener) { on('window', name, listener); } },
        document: {
            documentElement: root,
            querySelectorAll: selector => selector === '[data-theme-toggle]' ? [toggle] : [select],
            addEventListener(name, listener) { on('document', name, listener); },
        },
    };
    vm.runInNewContext(script, context);
    const fire = (target, name, event = {}) => listeners.get(`${target}:${name}`)(event);
    return { root, toggle, select, system, fire, saved: () => saved, saveExternally: value => { saved = value; } };
}

test('the saved preference is applied before DOMContentLoaded', () => {
    const f = fixture({ saved: 'dark' });
    assert.equal(f.root.dataset.theme, 'dark');
    f.fire('document', 'DOMContentLoaded');
    assert.equal(f.select.value, 'dark');
    assert.equal(f.toggle.attributes['aria-label'], 'Switch to Light Mode');
});

test('system mode follows device changes while an explicit preference does not', () => {
    const f = fixture();
    f.fire('document', 'DOMContentLoaded');
    f.system.matches = true;
    f.fire('system', 'change');
    assert.equal(f.root.dataset.theme, 'dark');
    f.select.value = 'light';
    f.fire('select', 'change');
    f.fire('system', 'change');
    assert.equal(f.root.dataset.theme, 'light');
    assert.equal(f.saved(), 'light');
});

test('the toggle persists the new theme and updates its accessible action', () => {
    const f = fixture();
    f.fire('document', 'DOMContentLoaded');
    f.fire('toggle', 'click');
    assert.equal(f.root.dataset.theme, 'dark');
    assert.equal(f.saved(), 'dark');
    assert.equal(f.toggle.attributes['aria-label'], 'Switch to Light Mode');
});

test('theme changes in another tab and restored pages stay synchronized', () => {
    const f = fixture({ saved: 'light' });
    f.fire('document', 'DOMContentLoaded');
    f.saveExternally('dark');
    f.fire('window', 'storage', { key: 'verve-theme' });
    assert.equal(f.root.dataset.theme, 'dark');
    f.saveExternally('light');
    f.fire('window', 'pageshow');
    assert.equal(f.root.dataset.theme, 'light');
});

test('unavailable storage does not break switching themes', () => {
    const f = fixture({ blocked: true });
    f.fire('document', 'DOMContentLoaded');
    f.fire('toggle', 'click');
    assert.equal(f.root.dataset.theme, 'dark');
    f.fire('window', 'pageshow');
    assert.equal(f.root.dataset.theme, 'dark');
});

test('an invalid stored preference falls back to the device setting', () => {
    const f = fixture({ saved: 'unknown', dark: true });
    assert.equal(f.root.dataset.theme, 'dark');
    f.fire('document', 'DOMContentLoaded');
    assert.equal(f.select.value, 'system');
});
