/** A shared entry point for learning and both independent practice rounds. */
export function initializeStudyModePicker() {
    const dialog = document.getElementById('study-mode-picker');
    if (!dialog) return;
    const choices = [...dialog.querySelectorAll('[data-study-choice]')];
    const defaultLinks = choices.map(choice => choice.getAttribute('href'));
    const collection = dialog.querySelector('[data-study-collection]');
    const defaultCollection = collection?.textContent;
    let originDialog = null;
    let originTrigger = null;
    document.querySelectorAll('[data-study-mode-picker]').forEach(trigger => {
        trigger.addEventListener('click', event => {
            event.preventDefault();
            document.getElementById('study-mode-info')?.hidePopover();
            originDialog = trigger.closest('dialog');
            originTrigger = trigger;
            if (trigger.dataset.studyFolder) {
                const path = `/folder/${encodeURIComponent(trigger.dataset.studyFolder)}/learn`;
                choices.forEach(choice => {
                    const mode = choice.dataset.studyChoice;
                    choice.href = mode === 'learn' ? path : `${path}?mode=${mode}`;
                });
                if (collection) collection.textContent = 'Folder';
            } else {
                choices.forEach((choice, index) => { choice.href = defaultLinks[index]; });
                if (collection) collection.textContent = defaultCollection;
            }
            originDialog?.close();
            dialog.showModal();
        });
    });
    dialog.addEventListener('close', () => {
        if (originDialog?.isConnected && !originDialog.open) {
            originDialog.showModal();
            originTrigger?.focus();
        }
        originDialog = null;
        originTrigger = null;
    });
    dialog.querySelector('[data-close-study-picker]').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', event => {
        const bounds = dialog.getBoundingClientRect();
        if (event.target === dialog && (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom)) {
            dialog.close();
        }
    });
}
