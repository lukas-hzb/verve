/** One native settings dialog for desktop and mobile. */
const dialog = document.getElementById('set-settings-dialog');
const trigger = document.getElementById('openSetSettings');
if (dialog && trigger) {
    const alignment = dialog.querySelector('#set-text-alignment');
    const alignmentStatus = dialog.querySelector('#set-text-alignment-status');
    let savedAlignment = alignment?.value;
    alignment?.addEventListener('change', async () => {
        const value = alignment.value;
        alignment.disabled = true;
        alignmentStatus.textContent = '';
        try {
            const response = await fetch(alignment.dataset.url, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text_alignment: value }),
            });
            if (!response.ok) throw new Error('Could not save Alignment');
            savedAlignment = value;
        } catch {
            alignment.value = savedAlignment;
            alignmentStatus.textContent = 'Could not save Alignment. Please try again.';
        } finally {
            alignment.disabled = false;
        }
    });
    trigger.addEventListener('click', () => {
        dialog.removeAttribute('data-handoff');
        dialog.showModal();
    });
    dialog.querySelector('[data-close-settings]').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', event => {
        const bounds = dialog.getBoundingClientRect();
        if (event.target === dialog && (event.clientX < bounds.left || event.clientX > bounds.right
            || event.clientY < bounds.top || event.clientY > bounds.bottom)) dialog.close();
    });
    const actions = {
        rename: ['renameModal', () => window.openRenameModal()],
        add: ['addCardModal', () => window.openAddCardModal()],
        import: ['importModal', () => window.openImportModal()],
    };
    // Close the top-layer dialog before opening an existing action popup.
    // Export keeps its own click handler, which runs after this capture listener.
    dialog.addEventListener('click', event => {
        const option = event.target.closest('[data-settings-action]');
        if (!option) return;
        dialog.setAttribute('data-handoff', '');
        dialog.close();
        const action = actions[option.dataset.settingsAction];
        if (action) {
            action[1]();
            // Focus a neutral button: focusing a select can open its native picker on iOS.
            document.getElementById(action[0]).querySelector('button')?.focus({ preventScroll: true });
        }
    }, true);
    Object.values(actions).forEach(([id]) => {
        const popup = document.getElementById(id);
        let wasOpen = false;
        new MutationObserver(() => {
            const open = popup.classList.contains('active');
            if (wasOpen && !open) trigger.focus();
            wasOpen = open;
        }).observe(popup, { attributes: true, attributeFilter: ['class'] });
    });
    document.addEventListener('keydown', event => {
        const popup = Object.values(actions).map(([id]) => document.getElementById(id))
            .find(element => element.classList.contains('active'));
        if (!popup) return;
        if (event.key === 'Escape') {
            event.preventDefault();
            popup.classList.remove('active');
        } else if (event.key === 'Tab') {
            const controls = [...popup.querySelectorAll('button, input, textarea, select, a[href]')]
                .filter(control => !control.disabled && control.getClientRects().length);
            const first = controls[0], last = controls[controls.length - 1];
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault(); last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault(); first.focus();
            }
        }
    });
}
