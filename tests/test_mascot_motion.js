import test from 'node:test';
import assert from 'node:assert/strict';
import { FlashcardManager } from '../static/js/modules/flashcard.js';
import { initializeWelcomeMascot } from '../static/js/modules/mascot.js';

function mascotFixture() {
    const classes = new Set();
    const mascot = new EventTarget();
    mascot.dataset = { pose: 'peek' };
    mascot.image = new EventTarget();
    mascot.querySelector = () => mascot.image;
    mascot.starts = 0;
    mascot.classList = {
        contains: (name) => classes.has(name),
        add: (name) => { classes.add(name); mascot.starts++; },
        remove: (name) => classes.delete(name),
    };
    return mascot;
}

function motionPreference(t, reduced = false) {
    const previous = globalThis.window;
    globalThis.window = { matchMedia: () => ({ matches: reduced }) };
    t.after(() => { globalThis.window = previous; });
}

function managerFixture(mascot) {
    return Object.assign(Object.create(FlashcardManager.prototype), {
        mascot, mascotReacting: false, mascotNextPose: null,
    });
}

test('rapid study reactions preserve the current motion and pose', (t) => {
    motionPreference(t);
    const mascot = mascotFixture();
    const manager = managerFixture(mascot);
    manager.setMascotPose('celebrate', true);
    manager.setMascotPose('peek', true);
    assert.equal(mascot.starts, 1);
    assert.equal(mascot.dataset.pose, 'celebrate');
    assert.equal(mascot.classList.contains('mascot-reacting'), true);
    manager.finishMascotReaction();
    assert.equal(mascot.dataset.pose, 'peek');
    assert.equal(mascot.classList.contains('mascot-reacting'), false);
});

test('a new resting pose is applied only after the motion completes', (t) => {
    motionPreference(t);
    const mascot = mascotFixture();
    const manager = managerFixture(mascot);
    manager.setMascotPose('peek', true);
    manager.setMascotPose('celebrate');
    assert.equal(mascot.dataset.pose, 'peek');
    assert.equal(manager.mascotReacting, true);
    manager.finishMascotReaction();
    assert.equal(mascot.dataset.pose, 'celebrate');
    assert.equal(manager.mascotReacting, false);
});

test('reduced motion does not start or lock a study reaction', (t) => {
    motionPreference(t, true);
    const mascot = mascotFixture();
    const manager = managerFixture(mascot);
    manager.setMascotPose('celebrate', true);
    assert.equal(mascot.starts, 0);
    assert.equal(manager.mascotReacting, false);
});

function welcomeFixture(t, reduced = false) {
    motionPreference(t, reduced);
    const mascot = mascotFixture();
    const previous = globalThis.document;
    globalThis.document = { querySelector: () => mascot };
    t.after(() => { globalThis.document = previous; });
    initializeWelcomeMascot();
    const enter = (pointerType = 'mouse') => mascot.dispatchEvent(Object.assign(new Event('pointerenter'), {
        pointerType,
    }));
    const finish = () => mascot.image.dispatchEvent(Object.assign(new Event('animationiteration'), {
        animationName: 'mascot-greet',
    }));
    return { mascot, enter, finish };
}

test('re-entry queues a complete greeting without interrupting the current one', (t) => {
    const { mascot, enter, finish } = welcomeFixture(t);
    enter();
    mascot.dispatchEvent(new Event('pointerleave'));
    enter();
    assert.equal(mascot.starts, 1);
    assert.equal(mascot.classList.contains('mascot-reacting'), true);
    finish();
    assert.equal(mascot.classList.contains('mascot-reacting'), true);
    assert.equal(mascot.starts, 1);
    finish();
    assert.equal(mascot.classList.contains('mascot-reacting'), false);
});

test('every new hover starts immediately after the previous greeting completes', (t) => {
    const { mascot, enter, finish } = welcomeFixture(t);
    enter();
    finish();
    enter();
    assert.equal(mascot.starts, 2);
    assert.equal(mascot.classList.contains('mascot-reacting'), true);
    finish();
    assert.equal(mascot.classList.contains('mascot-reacting'), false);
});

test('each rapid hover receives a full cycle and unrelated animations are ignored', (t) => {
    const { mascot, enter, finish } = welcomeFixture(t);
    enter();
    enter();
    enter();
    mascot.image.dispatchEvent(Object.assign(new Event('animationiteration'), {
        animationName: 'mascot-contact',
    }));
    finish();
    finish();
    assert.equal(mascot.starts, 1);
    assert.equal(mascot.classList.contains('mascot-reacting'), true);
    finish();
    assert.equal(mascot.classList.contains('mascot-reacting'), false);
});

test('touch taps greet while touch entry does not', (t) => {
    const { mascot, enter, finish } = welcomeFixture(t);
    enter('touch');
    assert.equal(mascot.starts, 0);
    mascot.dispatchEvent(Object.assign(new Event('pointerup'), { pointerType: 'touch' }));
    assert.equal(mascot.starts, 1);
    finish();
    assert.equal(mascot.classList.contains('mascot-reacting'), false);
});

test('reduced motion does not start or queue welcome greetings', (t) => {
    const { mascot, enter } = welcomeFixture(t, true);
    enter();
    enter();
    assert.equal(mascot.starts, 0);
});
