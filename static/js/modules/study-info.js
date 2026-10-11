/** Keep the practice explanation attached to its trigger in the top layer. */
export function initializeStudyInfo() {
    const panel = document.getElementById('study-mode-info');
    const triggers = document.querySelectorAll('.study-mode-pill [popovertarget="study-mode-info"]');
    if (!panel || !triggers.length) return;
    let trigger = triggers[0];
    triggers.forEach(button => button.addEventListener('click', () => { trigger = button; }));

    let frame;
    const position = () => {
        if (!panel.matches(':popover-open')) return;
        const anchor = trigger.getBoundingClientRect();
        const box = panel.getBoundingClientRect();
        const edge = 12;
        const gap = 8;
        const below = window.innerHeight - anchor.bottom - gap - edge;
        const above = anchor.top - gap - edge;
        const preferBelow = below >= box.height || below >= above;
        const top = preferBelow ? anchor.bottom + gap : anchor.top - gap - box.height;
        const left = Math.max(edge, Math.min(anchor.left, window.innerWidth - box.width - edge));
        panel.style.left = `${left}px`;
        panel.style.top = `${Math.max(edge, Math.min(top, window.innerHeight - box.height - edge))}px`;
        // Follow scrolling, responsive layout and the sidebar's animated width.
        frame = requestAnimationFrame(position);
    };
    panel.addEventListener('beforetoggle', () => cancelAnimationFrame(frame));
    panel.addEventListener('toggle', event => {
        if (event.newState === 'open') position();
    });
}
