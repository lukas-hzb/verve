import { connectAnchoredMenu } from './anchored-menu.js';

const menu = document.getElementById('set-settings-menu');
const trigger = document.getElementById('openSetSettings');
if (menu && trigger) {
    connectAnchoredMenu(menu);
    const layoutOptions = menu.querySelector('.set-layout-options');
    const layoutStatus = layoutOptions?.querySelector('[role="status"]');
    layoutOptions?.addEventListener('click', async event => {
        const button = event.target.closest('[data-layout-value]');
        if (!button || button.getAttribute('aria-pressed') === 'true') return;
        const group = button.closest('[data-layout-setting]');
        if (group.hasAttribute('aria-busy')) return;
        const setting = group.dataset.layoutSetting;
        const value = button.dataset.layoutValue;
        group.setAttribute('aria-busy', 'true');
        layoutStatus.textContent = '';
        try {
            const response = await fetch(menu.dataset.layoutUrl, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ setting, value }),
            });
            if (!response.ok) throw new Error('Could not save text layout');
            for (const option of group.querySelectorAll('[data-layout-value]')) {
                option.setAttribute('aria-pressed', String(option === button));
            }
            document.dispatchEvent(new CustomEvent('set-text-layout-changed', { detail: { setting, value } }));
        } catch {
            layoutStatus.textContent = 'Could not save text layout. Please try again.';
        } finally {
            group.removeAttribute('aria-busy');
        }
    });
    const actions = {
        rename: ['renameModal', () => window.openRenameModal()],
        add: ['addCardModal', () => window.openAddCardModal()],
        import: ['importModal', () => window.openImportModal()],
    };
    // Close the menu before opening an existing action popup.
    // Export keeps its own click handler, which runs after this capture listener.
    menu.addEventListener('click', event => {
        const option = event.target.closest('[data-settings-action]');
        if (!option) return;
        menu.hidePopover();
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
            const controls = [...popup.querySelectorAll('button, input, textarea, select, a[href], [contenteditable="true"]')]
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
