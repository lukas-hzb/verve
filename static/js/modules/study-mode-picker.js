/** A shared entry point for learning and both independent practice rounds. */
export function initializeStudyModePicker() {
    const dialog = document.getElementById('study-mode-picker');
    if (!dialog) return;
    document.querySelectorAll('[data-study-mode-picker]').forEach(trigger => {
        trigger.addEventListener('click', event => {
            event.preventDefault();
            document.getElementById('study-mode-info')?.hidePopover();
            dialog.showModal();
        });
    });
    dialog.querySelector('[data-close-study-picker]').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', event => {
        const bounds = dialog.getBoundingClientRect();
        if (event.target === dialog && (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom)) {
            dialog.close();
        }
    });
}
