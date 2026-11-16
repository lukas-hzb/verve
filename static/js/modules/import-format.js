import { createCardPreview } from './card-editor.js';
import { parseDelimitedRows } from './delimited-text.js';

const separatorCodes = { n: '\n', t: '\t', r: '\r' };
const decodeSeparator = value => value.replace(/\\([ntr])/g, (_, code) => separatorCodes[code]);

function setupImportEditor(form) {
    const layout = form.closest('.card-editor-layout');
    const preview = createCardPreview(layout);
    const upload = form.elements.file;
    const text = form.elements.text_content;
    const settings = form.querySelector('.import-box');
    const contentFormat = form.elements.content_format;
    const navigation = layout.querySelector('[data-preview-navigation]');
    const steps = [...navigation.querySelectorAll('[data-preview-step]')];
    const position = navigation.querySelector('[data-preview-position]');
    const check = layout.querySelector('[data-preview-check]');
    const checkButton = check?.querySelector('[data-check-import]');
    const summary = check?.querySelector('[data-import-summary]');
    let revision = 0;
    let cards = [];
    let cardIndex = 0;
    let message;
    const tabs = [...form.querySelectorAll('.import-tab')];
    const filename = form.querySelector('[data-import-filename]');
    let fileRead = 0;
    let fileContent = '';
    let fileError = '';
    let reading = false;

    function separator(name, isVerve) {
        const select = form.elements[name];
        const custom = form.elements['custom_' + name];
        const needsCustom = !isVerve && select.value === 'custom';
        select.disabled = isVerve;
        custom.hidden = custom.disabled = !needsCustom;
        custom.required = needsCustom;
        return decodeSeparator(needsCustom ? custom.value : select.value);
    }

    function update() {
        revision++;
        if (summary) summary.hidden = true;
        const isText = form.elements.import_type.value === 'text';
        const file = isText ? null : upload.files[0];
        const isVerve = Boolean(file?.name.toLowerCase().endsWith('.verve'));
        settings.hidden = isVerve;
        const fieldSeparator = separator('field_separator', isVerve);
        const cardSeparator = separator('card_separator', isVerve);
        const content = isText ? text.value : fileContent;
        text.placeholder = fieldSeparator && cardSeparator
            ? ['Dog' + fieldSeparator + 'Hund', 'Cat' + fieldSeparator + 'Katze'].join(cardSeparator)
            : '';

        cards = [];
        cardIndex = 0;
        message = '';
        contentFormat.disabled = isVerve;
        if (!isText && reading) message = 'Reading file…';
        else if (!isText && fileError) message = fileError;
        else if (!isText && !file) message = 'No file selected.';
        else if (!content.trim()) message = isText ? 'No text entered.' : 'The file is empty.';
        else if (isVerve) {
            try {
                const backup = JSON.parse(content);
                if (backup.format !== 'verve' || ![1, 2].includes(backup.version) || !Array.isArray(backup.cards)) throw new Error();
                cards = backup.cards.map(card => ({
                    text: [card.front, card.back],
                    formats: [card.front_format || 'plain', card.back_format || 'plain'],
                }));
                if (!cards.every(card => card.text.every(value => typeof value === 'string' && value.trim()))) throw new Error();
            } catch {
                cards = [];
                message = 'Could not preview this Verve file.';
            }
        } else if (!fieldSeparator || !cardSeparator) message = 'Enter both separators to see a preview.';
        else {
            cards = parseDelimitedRows(content, cardSeparator, fieldSeparator, {
                preserveWhitespace: contentFormat.value === 'markdown',
            }).filter(parts => parts[0]?.trim() && parts[1]?.trim())
                .map(parts => ({ text: parts.slice(0, 2), formats: [contentFormat.value, contentFormat.value] }));
        }
        showPreview();
    }

    function showPreview() {
        const card = cards[cardIndex];
        if (check) check.hidden = !card;
        navigation.hidden = cards.length <= 1;
        position.textContent = cards.length ? (cardIndex + 1) + ' / ' + cards.length : '';
        for (const step of steps) {
            const target = cardIndex + Number(step.dataset.previewStep);
            step.disabled = target < 0 || target >= cards.length;
        }
        if (card) {
            preview(card.text[0], card.text[1], undefined, card.formats);
        } else {
            preview('', '', message || 'No complete cards found. Check the separators and fill in both sides.');
        }
    }

    for (const step of steps) {
        step.addEventListener('click', () => {
            cardIndex += Number(step.dataset.previewStep);
            showPreview();
        });
    }

    checkButton?.addEventListener('click', async () => {
        const requestedRevision = revision;
        checkButton.disabled = true;
        summary.hidden = true;
        try {
            const url = new URL(form.action);
            url.searchParams.set('preview', '1');
            const response = await fetch(url, { method: 'POST', body: new FormData(form) });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            summary.textContent = [result.added + ' new', result.updated + ' to update',
                result.ambiguous + ' conflicting'].join(' · ');
        } catch (error) {
            summary.textContent = error.message || 'Could not check the import.';
        } finally {
            checkButton.disabled = false;
            summary.hidden = requestedRevision !== revision;
        }
    });

    function switchSource(isText) {
        form.elements.import_type.value = isText ? 'text' : 'file';
        form.querySelector('#file-section').hidden = isText;
        form.querySelector('#text-section').hidden = !isText;
        upload.required = !isText;
        upload.disabled = isText;
        text.required = isText;
        text.disabled = !isText;
        for (const tab of tabs) {
            const active = (tab.id === 'tab-text') === isText;
            tab.classList.toggle('active', active);
            tab.setAttribute('aria-pressed', String(active));
        }
        update();
    }

    upload.addEventListener('change', async () => {
        const file = upload.files[0];
        const currentRead = ++fileRead;
        filename.textContent = file?.name || '';
        reading = Boolean(file);
        fileError = fileContent = '';
        update();
        if (!file) return;
        try {
            const content = new TextDecoder('utf-8', { fatal: true }).decode(await file.arrayBuffer());
            if (currentRead === fileRead) fileContent = content;
        } catch {
            if (currentRead === fileRead) fileError = 'Could not read the file. Use UTF-8 encoding.';
        } finally {
            if (currentRead === fileRead) {
                reading = false;
                update();
            }
        }
    });
    for (const tab of tabs) tab.addEventListener('click', () => switchSource(tab.id === 'tab-text'));
    text.addEventListener('input', update);
    settings.addEventListener('input', update);
    switchSource(false);
}

const importForm = document.querySelector('#importForm[data-csrf-url]');
if (importForm) {
    setupImportEditor(importForm);
    const submitButton = importForm.querySelector('button[type="submit"]');
    const error = importForm.querySelector('[data-import-error]');
    let refreshing = false;
    let submittingWithFreshToken = false;

    importForm.addEventListener('submit', async event => {
        if (submittingWithFreshToken) return;
        event.preventDefault();
        if (refreshing) return;

        refreshing = true;
        submitButton.disabled = true;
        error.hidden = true;
        try {
            // Forms can outlive the Flask session even while the user is signed in.
            const response = await fetch(importForm.dataset.csrfUrl, {
                cache: 'no-store',
                mode: 'same-origin',
            });
            if (response.status === 401) {
                error.textContent = 'Sign in to Verve in another tab, then try importing again.';
                error.hidden = false;
                return;
            }
            if (!response.ok) throw new Error('Could not refresh the import token');
            const { csrf_token: token } = await response.json();
            if (typeof token !== 'string' || !token) throw new Error('Missing import token');
            if (!importForm.getClientRects().length) return;

            importForm.elements.csrf_token.value = token;
            submittingWithFreshToken = true;
            importForm.requestSubmit();
        } catch {
            error.textContent = 'Could not prepare the import. Please try again.';
            error.hidden = false;
        } finally {
            submittingWithFreshToken = false;
            refreshing = false;
            submitButton.disabled = false;
        }
    });
}
