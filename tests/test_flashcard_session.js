import test from 'node:test';
import assert from 'node:assert/strict';
import { FlashcardManager } from '../static/js/modules/flashcard.js';

test('card display preserves paragraphs and interprets escaped newlines on both sides', () => {
    const m = Object.assign(Object.create(FlashcardManager.prototype), {
        cardFront: {}, cardBack: {}, cardLevels: [], updateCompletionAction() {},
    });
    const card = { front: 'First\\n\\nSecond', back: 'Answer\n\n<img src=x onerror=alert(1)>', level: 1 };
    m.updateCardContent(card);
    assert.equal(m.cardFront.textContent, 'First\n\nSecond');
    assert.equal(m.cardBack.textContent, 'Answer\n\n<img src=x onerror=alert(1)>');
    assert.equal(card.front, 'First\\n\\nSecond');
    m.updateCardContent({ front: 'First\\r\\nSecond', back: 'Plain answer', level: 1 });
    assert.equal(m.cardFront.textContent, 'First\nSecond');
    assert.equal(m.cardBack.textContent, 'Plain answer');
});

test('Space overrides focused buttons without interfering with typing or dialogs', t => {
    const previous = globalThis.document;
    let onKeydown;
    let overlayOpen = false;
    let typing = false;
    let blurred = 0;
    globalThis.document = {
        querySelector: () => overlayOpen,
        activeElement: {
            matches: selector => selector === 'input, textarea, select' ? typing : !typing,
            isContentEditable: false,
            blur() { blurred++; },
        },
        addEventListener: (name, handler) => { if (name === 'keydown') onKeydown = handler; },
    };
    t.after(() => { globalThis.document = previous; });
    let flips = 0;
    let flipped = false;
    const m = Object.assign(Object.create(FlashcardManager.prototype), {
        flashcard: { classList: { contains: () => flipped } },
        flipBtn: { style: { display: '' } },
        flipCard() { flips++; },
    });
    m.attachKeyboardListeners();
    const pressSpace = (repeat = false) => {
        let prevented = false;
        onKeydown({ code: 'Space', repeat, preventDefault() { prevented = true; } });
        return prevented;
    };
    assert.equal(pressSpace(), true);
    assert.equal(flips, 1);
    assert.equal(blurred, 1);
    assert.equal(pressSpace(true), true);
    assert.equal(flips, 1);
    flipped = true;
    assert.equal(pressSpace(), true);
    assert.equal(flips, 1);
    typing = true;
    const beforeTyping = blurred;
    assert.equal(pressSpace(), false);
    assert.equal(blurred, beforeTyping);
    typing = false;
    overlayOpen = true;
    assert.equal(pressSpace(), false);
});

function manager(t) {
    const values = new Map();
    const previous = globalThis.localStorage;
    globalThis.localStorage = {
        getItem: key => values.get(key) ?? null,
        setItem: (key, value) => values.set(key, value),
        removeItem: key => values.delete(key),
    };
    t.after(() => { globalThis.localStorage = previous; });
    return Object.assign(Object.create(FlashcardManager.prototype), {
        setId: 'set', learningStorageKey: 'learning', practiceStorageKey: 'practice', modeStorageKey: 'mode',
        isPracticeMode: false, isWrongAnswersMode: false, cards: [{id:'1',front:'a'}],
        currentCardIndex: 0, undoHistory: [], sessionStats: {correct:0,wrong:0,total:1},
        syncQueue: [], updateModeUI() {}, updateUI() {}, showLoading() {}, updateBackButtonState() {},
        disableControls() { this.areControlsDisabled = true; },
        enableControls() { this.areControlsDisabled = false; },
        async fetchAndLoadCards() {
            this.cards = [{id:'2',front:'b'}]; this.currentCardIndex = 0;
            this.undoHistory = []; this.sessionStats = {correct:0,wrong:0,total:1}; this.saveSession();
        },
    });
}

test('completed practice rounds offer the appropriate next round', t => {
    const m = manager(t);
    m.completion = {hidden: true};
    m.completionText = {};
    m.continuePracticeLabel = {};
    m.updateCompletionAction(true);
    assert.equal(m.completion.hidden, true);
    m.isPracticeMode = true;
    m.updateCompletionAction(true);
    assert.equal(m.completion.hidden, false);
    assert.equal(m.continuePracticeLabel.textContent, 'Practice Again');
    m.isWrongAnswersMode = true;
    m.sessionStats.wrong = 1;
    m.updateCompletionAction(true);
    assert.equal(m.continuePracticeLabel.textContent, 'Review Remaining Mistakes');
    m.sessionStats.wrong = 0;
    m.updateCompletionAction(true);
    assert.equal(m.continuePracticeLabel.textContent, 'Practice All Cards');
    m.updateCompletionAction();
    assert.equal(m.completion.hidden, true);
});

test('continuing a round synchronizes answers before fetching its cards', async t => {
    const m = manager(t);
    const steps = [];
    m.showLoading = () => steps.push('loading');
    m.processSyncQueue = async () => steps.push('sync');
    m.fetchAndLoadCards = async () => steps.push('fetch');
    await m.restartRound();
    assert.deepEqual(steps, ['loading', 'sync', 'fetch']);
    assert.equal(m.areControlsDisabled, false);
});

test('overview modes preserve three independent rounds and undo histories', t => {
    const m = manager(t);
    m.currentCardIndex = 1; m.sessionStats.correct = 1; m.undoHistory = [{card:m.cards[0],quality:5}];
    m.saveSession();
    m.isPracticeMode = true;
    m.cards = [{id:'2',front:'practice'}]; m.currentCardIndex = 0;
    m.sessionStats = {correct:0,wrong:0,total:1}; m.undoHistory = []; m.saveSession();
    m.isWrongAnswersMode = true;
    assert.equal(m.loadSession(), false); // Never resurrect the old Level 1 filter.
    m.cards = [{id:'3',front:'mistake'}]; m.saveSession();
    m.isWrongAnswersMode = false; assert.equal(m.loadSession(), true);
    assert.equal(m.cards[0].front, 'practice'); assert.equal(m.currentCardIndex, 0);
    m.isPracticeMode = false; assert.equal(m.loadSession(), true);
    assert.equal(m.sessionStats.correct, 1); assert.equal(m.undoHistory.length, 1);
    m.isPracticeMode = true; m.isWrongAnswersMode = true;
    assert.equal(m.loadSession(), true); assert.equal(m.cards[0].front, 'mistake');
});

test('empty rounds clear stale progress and completed rounds retain their result', t => {
    const m = manager(t);
    m.progressText = {}; m.progressCorrect = {style:{}}; m.progressWrong = {style:{}};
    m.progressRemaining = {style:{}};
    m.sessionStats = {correct:2,wrong:1,total:3}; m.updateProgress();
    assert.match(m.progressText.textContent, /3 \/ 3 · Complete/);
    assert.ok(Math.abs(parseFloat(m.progressWrong.style.width) - 100/3) < 0.001);
    m.sessionStats = {correct:0,wrong:0,total:0}; m.updateProgress();
    assert.equal(m.progressText.textContent, '0 / 0');
    assert.equal(m.progressCorrect.style.width, '0%');
    assert.equal(m.progressWrong.style.width, '0%');
});

test('previous mistakes uses the last-answer filter and includes higher levels', async t => {
    const m = manager(t);
    delete m.fetchAndLoadCards;
    m.isPracticeMode = true; m.isWrongAnswersMode = true;
    const previous = globalThis.fetch;
    let url;
    globalThis.fetch = async requested => {
        url = requested;
        return {ok:true,json:async()=>({cards:[{id:'higher',front:'last wrong',level:4,last_answer_wrong:true}]})};
    };
    t.after(()=>{globalThis.fetch=previous;});
    await m.fetchAndLoadCards();
    assert.equal(url, '/api/set/set/cards?last_wrong_only=true');
    assert.equal(m.cards[0].level, 4);
});

test('queued practice and learning answers retain their own endpoints across mode changes', async t => {
    const m = manager(t);
    const previous = globalThis.fetch;
    const requests = [];
    let release;
    globalThis.fetch = async (url, options) => {
        requests.push({url,body:JSON.parse(options.body)});
        if (requests.length === 1) await new Promise(resolve=>{release=resolve;});
        return {ok:true};
    };
    t.after(()=>{globalThis.fetch=previous;});
    m.queueSync({cardFront:'learning',quality:2,retries:0});
    m.queuePracticeSync({cardFront:'practice',endpoint:'mark_correct',retries:0});
    release(); await m.processSyncQueue();
    assert.deepEqual(requests,[
        {url:'/api/set/set/rate',body:{card_front:'learning',quality:2}},
        {url:'/api/set/set/mark_correct',body:{card_front:'practice'}},
    ]);
    assert.equal(m.syncQueue.length,0);
});

test('extra practice submits answer markers without rating the learning level', t => {
    const m = manager(t);
    const previous = globalThis.setTimeout;
    globalThis.setTimeout = callback => callback();
    t.after(() => { globalThis.setTimeout = previous; });
    const calls = [];
    Object.assign(m, {
        cardContainer:{classList:{remove(){},add(){}}}, setMascotPose(){}, updateProgress(){},
        showCompletionMessage(){}, queueSync(item){calls.push(['rate',item.quality]);},
        queuePracticeSync(item){calls.push([item.endpoint]);},
    });
    for (const focus of [false, true]) {
        m.isPracticeMode = true; m.isWrongAnswersMode = focus; m.currentCardIndex = 0;
        m.handleFeedback(5);
    }
    assert.deepEqual(calls, [['mark_correct'], ['mark_correct']]);
});

test('practice shuffle does not overwrite the normal learning order', t => {
    const m = manager(t);
    const previous = globalThis.fetch;
    const requests = [];
    globalThis.fetch = async (...args) => {requests.push(args); return {ok:true};};
    t.after(() => {globalThis.fetch = previous;});
    m.cards = [{id:'1',front:'a',level:1},{id:'2',front:'b',level:1}];
    m.isPracticeMode = true; m.loadCard = () => {};
    m.shuffleCards();
    assert.equal(requests.length, 0);
    assert.equal(m.cards[0].front, 'b');
});
