import { renderCardContent } from './card-text.js';
import { initializeCardSide } from './card-side-editor.js';
import { fitCardText, prepareCardTextLayout } from './card-text-layout.js';

export function createCardPreview(layout) {
    const faces = layout.querySelector('.card-preview-faces');
    const panels = [...faces.querySelectorAll('.preview-card')].map(face => ({
        face,
        content: face.querySelector('.preview-card-scroll'),
        text: face.querySelector('.preview-card-text'),
    }));
    const [{ face: frontCard }, { face: backCard }] = panels;
    const flip = layout.querySelector('[data-preview-flip]');
    const layoutOptions = backCard.querySelector('.preview-alignment');
    const previous = new Map();

    function fitVisibleFace() {
        const panel = panels.find(({ face }) => !face.hidden);
        if (panel.face.clientWidth) fitCardText(prepareCardTextLayout(panel));
    }

    function showBack(show) {
        frontCard.hidden = show;
        backCard.hidden = !show;
        flip.textContent = show ? 'Show Front' : 'Show Back';
    }
    flip.addEventListener('click', () => {
        showBack(backCard.hidden);
        fitVisibleFace();
    });
    function setBackLayout(setting, value) {
        backCard.setAttribute('data-' + setting.replaceAll('_', '-'), value);
        const group = layoutOptions.querySelector(`[data-layout-setting="${setting}"]`);
        for (const option of group.querySelectorAll('[data-layout-value]')) {
            option.setAttribute('aria-pressed', String(option.dataset.layoutValue === value));
        }
        if (!backCard.hidden) fitVisibleFace();
    }
    layoutOptions.addEventListener('click', event => {
        const button = event.target.closest('[data-layout-value]');
        if (!button) return;
        setBackLayout(button.closest('[data-layout-setting]').dataset.layoutSetting, button.dataset.layoutValue);
    });
    document.addEventListener('set-text-layout-changed', event => {
        const { setting, value } = event.detail;
        setBackLayout(setting, value);
    });
    new ResizeObserver(fitVisibleFace).observe(faces);
    faces.addEventListener('load', fitVisibleFace, true);
    faces.addEventListener('error', fitVisibleFace, true);
    document.fonts.ready.then(fitVisibleFace);

    return (frontText = '', backText = '', emptyMessage = 'No text yet', formats = []) => {
        if (!frontText.trim() && !backText.trim() && !backCard.hidden) showBack(false);
        const cardText = [frontText, backText];
        panels.forEach(({ text: element, content }, index) => {
            const format = formats[index];
            const text = format === 'markdown' ? cardText[index] : cardText[index].trim();
            const hasText = Boolean(text.trim());
            const displayText = hasText ? text : emptyMessage;
            const last = previous.get(element);
            if (last?.displayText === displayText && last.format === format && last.hasText === hasText) return;
            previous.set(element, { displayText, format, hasText });
            if (hasText) {
                delete element.dataset.empty;
                renderCardContent(element, text, { spacedLineBreaks: true, format });
            } else {
                element.classList.remove('card-markdown');
                element.dataset.empty = '';
                element.textContent = displayText;
            }
            content.scrollTop = 0;
        });
        fitVisibleFace();
    };
}

for (const form of document.querySelectorAll('#addCardForm, #editCardForm')) {
    const loadSides = [...form.querySelectorAll('[data-card-side-editor]')].map(initializeCardSide);
    const preview = createCardPreview(form.closest('.card-editor-layout'));
    const update = () => preview(form.elements.front.value, form.elements.back.value, undefined, [
        form.elements.front_format.value,
        form.elements.back_format.value,
    ]);
    function loadCard(card) {
        loadSides.forEach(loadSide => loadSide(card));
        update();
    }
    form.addEventListener('input', update);
    form.addEventListener('load-card-editor', event => loadCard(event.detail));
    form.addEventListener('reset', () => queueMicrotask(() => loadCard()));
    loadCard();
}

const editDialog = document.getElementById('editCardModal');
if (editDialog) {
    const form = editDialog.querySelector('form');
    const fields = form.querySelector('.card-editor-fields');
    const save = form.querySelector('#editCardSave');
    const error = form.querySelector('#editCardError');
    let editing;
    let saving = false;

    function close() {
        if (saving || !editing) return;
        editDialog.classList.remove('active');
        editing.trigger?.focus({ preventScroll: true });
        editing = null;
    }

    editDialog.addEventListener('edit-card', event => {
        if (editing) return;
        editing = event.detail;
        form.dispatchEvent(new CustomEvent('load-card-editor', { detail: editing.card }));
        error.hidden = true;
        editDialog.classList.add('active');
        form.querySelector(':is(textarea, [contenteditable="true"]):not([hidden])').focus({ preventScroll: true });
    });
    editDialog.querySelectorAll('[data-close-card-editor]').forEach(button => button.addEventListener('click', close));
    editDialog.addEventListener('click', event => { if (event.target === editDialog) close(); });

    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (saving || !editing) return;
        const { card, setId, onSaved } = editing;
        const draft = Object.fromEntries(new FormData(form));
        error.hidden = true;
        saving = save.disabled = fields.inert = true;
        save.textContent = 'Saving…';
        let updatedCard;
        try {
            const response = await fetch(`/api/set/${encodeURIComponent(setId)}/card/${encodeURIComponent(card.id)}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(draft),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Saving the Card failed.');
            updatedCard = data.card;
        } catch (failure) {
            error.textContent = failure.message || 'Saving the Card failed. Please try again.';
            error.hidden = false;
        } finally {
            saving = save.disabled = fields.inert = false;
            save.textContent = 'Save';
        }
        if (updatedCard) {
            close();
            onSaved?.(updatedCard);
        }
    });

    document.addEventListener('keydown', event => {
        if (!editing) return;
        if (event.key === 'Escape') {
            event.preventDefault();
            close();
        } else if (event.key === 'Tab') {
            const controls = [...editDialog.querySelectorAll('button:not(:disabled), input:not([type="hidden"]):not(:disabled), textarea, [contenteditable="true"]')]
                .filter(control => !control.closest('[inert]') && control.getClientRects().length);
            const first = controls[0];
            const last = controls.at(-1);
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        }
    });
}
