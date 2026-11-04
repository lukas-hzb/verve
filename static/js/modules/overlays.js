/** Keep overlays on their originating page without background scrolling or touch focus rings. */
export function initializeOverlays() {
    const root = document.documentElement;
    const panels = [...document.querySelectorAll('dialog, .popup-overlay, .study-mode-info-panel[popover]')];
    let locked = false;
    let scrollX = 0;
    let scrollY = 0;

    const syncScrollLock = () => {
        const open = panels.some(panel => panel.matches('dialog[open], .popup-overlay.active, :popover-open'));
        if (open === locked) return;
        locked = open;
        if (open) {
            scrollX = window.scrollX;
            scrollY = window.scrollY;
            root.style.setProperty('--overlay-scroll-top', `${-scrollY}px`);
            root.classList.add('overlay-scroll-locked');
        } else {
            root.classList.remove('overlay-scroll-locked');
            root.style.removeProperty('--overlay-scroll-top');
            window.scrollTo(scrollX, scrollY);
        }
    };
    const observer = new MutationObserver(syncScrollLock);
    panels.forEach(panel => {
        observer.observe(panel, {attributes: true, attributeFilter: ['open', 'class']});
        panel.addEventListener('toggle', syncScrollLock);
    });
    syncScrollLock();

    // Safari can restore :focus-visible to a tapped card after its dialog closes.
    document.addEventListener('pointerdown', () => { root.dataset.inputMethod = 'pointer'; }, true);
    document.addEventListener('keydown', event => {
        if (['Tab', 'Enter', ' ', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) {
            root.dataset.inputMethod = 'keyboard';
        }
    }, true);
}
