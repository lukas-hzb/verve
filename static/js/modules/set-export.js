/** Configure and download a complete vocabulary set without leaving its overview. */
const modal = document.getElementById('exportModal');
const form = document.getElementById('exportForm');
const trigger = document.getElementById('openExportModal');

if (modal && form && trigger) {
    const format = document.getElementById('export-format');
    const field = document.getElementById('export-field');
    const card = document.getElementById('export-card');
    const customField = document.getElementById('export-custom-field');
    const customCard = document.getElementById('export-custom-card');
    const error = document.getElementById('export-error');
    const download = document.getElementById('export-download');
    let activeRequest;

    const separator = (select, custom) => (select.value === 'custom' ? custom.value : select.value)
        .replace(/\\n/g, '\n').replace(/\\t/g, '\t').replace(/\\r/g, '\r');
    const setBusy = busy => {
        download.disabled = busy;
        form.setAttribute('aria-busy', String(busy));
        download.lastChild.textContent = busy ? ' Preparing…' : ' Download';
    };
    const close = () => {
        activeRequest?.abort();
        activeRequest = null;
        setBusy(false);
        modal.classList.remove('active');
        (document.getElementById('openSetSettings') || trigger).focus();
    };
    const update = () => {
        customField.hidden = field.disabled || field.value !== 'custom';
        customCard.hidden = card.disabled || card.value !== 'custom';
        customField.required = !customField.hidden;
        customCard.required = !customCard.hidden;
        document.getElementById('export-separators').hidden = format.value === 'verve';
        error.hidden = true;
    };

    trigger.addEventListener('click', () => {
        update();
        modal.classList.add('active');
        modal.querySelector('[data-close-export]').focus({ preventScroll: true });
    });
    modal.querySelectorAll('[data-close-export]').forEach(button => button.addEventListener('click', close));
    modal.addEventListener('click', event => { if (event.target === modal) close(); });
    document.addEventListener('keydown', event => {
        if (!modal.classList.contains('active')) return;
        if (event.key === 'Escape') {
            event.preventDefault();
            close();
        } else if (event.key === 'Tab') {
            const controls = [...modal.querySelectorAll('button, select, input')]
                .filter(element => !element.disabled && element.getClientRects().length);
            const first = controls[0];
            const last = controls[controls.length - 1];
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        }
    });
    format.addEventListener('change', () => {
        field.value = format.value === 'csv' ? ',' : '\\t';
        field.disabled = format.value === 'tsv';
        card.value = '\\n';
        card.disabled = format.value !== 'txt';
        update();
    });
    [field, card].forEach(select => select.addEventListener('change', update));
    [customField, customCard].forEach(input => input.addEventListener('input', update));

    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (activeRequest || !form.reportValidity()) return;
        const controller = new AbortController();
        activeRequest = controller;
        setBusy(true);
        error.hidden = true;
        const url = new URL(form.action);
        url.search = new URLSearchParams({
            format: format.value,
            field_separator: separator(field, customField),
            card_separator: separator(card, customCard),
        });
        try {
            const response = await fetch(url, { signal: controller.signal });
            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.message || 'The Export could not be created. Please try again.');
            }
            if (!response.headers.get('content-disposition')?.includes('attachment')) {
                throw new Error('Please reload the Page and sign in again before exporting.');
            }
            const blob = await response.blob();
            if (controller.signal.aborted) return;
            const objectURL = URL.createObjectURL(blob);
            const link = document.createElement('a');
            const filename = response.headers.get('content-disposition').match(/filename="([^"]+)"|filename=([^;]+)/);
            link.href = objectURL;
            link.download = filename?.[1] || filename?.[2] || `cards.${format.value}`;
            document.body.append(link);
            link.click();
            link.remove();
            setTimeout(() => URL.revokeObjectURL(objectURL), 1000);
            close();
        } catch (exception) {
            if (!controller.signal.aborted) {
                error.textContent = exception.message || 'The Export could not be created. Please try again.';
                error.hidden = false;
            }
        } finally {
            if (activeRequest === controller) {
                activeRequest = null;
                setBusy(false);
            }
        }
    });
    update();
}
