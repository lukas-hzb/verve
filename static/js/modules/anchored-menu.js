/** Keep a top-layer popover aligned with its trigger, including inside scrolling dialogs. */
export function connectAnchoredMenu(menu) {
    const trigger = document.querySelector(`[popovertarget="${menu.id}"]`);
    const viewport = window.visualViewport;
    const gap = 6;
    const edge = 8;
    let listeners;
    let resize;
    let frame;

    function position() {
        if (!menu.matches(':popover-open')) return;
        const left = (viewport?.offsetLeft ?? 0) + edge;
        const top = (viewport?.offsetTop ?? 0) + edge;
        const right = left + (viewport?.width ?? document.documentElement.clientWidth) - 2 * edge;
        const bottom = top + (viewport?.height ?? document.documentElement.clientHeight) - 2 * edge;
        const anchor = trigger.getBoundingClientRect();
        if (!anchor.width || !anchor.height || anchor.bottom < top || anchor.top > bottom) {
            menu.hidePopover();
            return;
        }

        menu.style.maxWidth = `${right - left}px`;
        const desiredHeight = menu.scrollHeight + menu.offsetHeight - menu.clientHeight;
        const below = Math.max(0, bottom - anchor.bottom - gap);
        const above = Math.max(0, anchor.top - top - gap);
        const openAbove = desiredHeight > below && above > below;
        menu.style.maxHeight = `${openAbove ? above : below}px`;

        const { width, height } = menu.getBoundingClientRect();
        const alignEnd = trigger.dataset.menuAlign === 'end';
        const rtl = getComputedStyle(trigger).direction === 'rtl';
        const x = alignEnd !== rtl ? anchor.right - width : anchor.left;
        const y = openAbove ? anchor.top - gap - height : anchor.bottom + gap;
        menu.style.left = `${Math.max(left, Math.min(x, right - width))}px`;
        menu.style.top = `${Math.max(top, Math.min(y, bottom - height))}px`;
    }

    function schedulePosition() {
        cancelAnimationFrame(frame);
        frame = requestAnimationFrame(position);
    }

    menu.addEventListener('beforetoggle', event => {
        if (event.newState === 'closed') {
            listeners?.abort();
            resize?.disconnect();
            cancelAnimationFrame(frame);
            return;
        }
        listeners = new AbortController();
        const { signal } = listeners;
        window.addEventListener('resize', schedulePosition, { signal, passive: true });
        window.addEventListener('scroll', schedulePosition, { signal, capture: true, passive: true });
        viewport?.addEventListener('resize', schedulePosition, { signal });
        viewport?.addEventListener('scroll', schedulePosition, { signal });
        // Escape dismisses this menu before any surrounding dialog handles the key.
        window.addEventListener('keydown', event => {
            if (event.key !== 'Escape' || event.defaultPrevented || menu.querySelector(':popover-open')) return;
            event.preventDefault();
            event.stopPropagation();
            menu.hidePopover();
            trigger.focus({ preventScroll: true });
        }, { signal, capture: true });
        resize = new ResizeObserver(schedulePosition);
        resize.observe(trigger);
        resize.observe(menu);
        schedulePosition();
    });
}
