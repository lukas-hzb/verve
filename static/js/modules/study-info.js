/** Keep info popovers attached to their trigger in the top layer. */
export function initializeStudyInfo() {
    document.querySelectorAll('.study-mode-info-panel[popover]').forEach(panel => {
        attachInfoPopover(panel);
    });
}

function attachInfoPopover(panel) {
    const triggers = document.querySelectorAll(`[popovertarget="${panel.id}"]`);
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
