export function prepareCardTextLayout({ face, content, text, hasActions = false }) {
    const scrollTop = content.scrollTop;
    content.classList.add('measuring-text');
    content.classList.remove('short-text');
    text.style.removeProperty('--fitted-card-font-size');
    const minimum = face.dataset.textScaling === 'minimum';
    const topAligned = face.dataset.textVerticalAlignment === 'top';
    content.classList.toggle('top-aligned', topAligned);
    if (minimum) text.style.setProperty('--fitted-card-font-size', '0px');
    const topSpace = parseFloat(getComputedStyle(content).top);
    return { face, content, text, scrollTop, topSpace, hasActions, minimum, topAligned };
}

export function fitCardText({ face, content, text, scrollTop, topSpace, hasActions, minimum, topAligned }) {
    const textStyle = getComputedStyle(text);
    const defaultSize = parseFloat(textStyle.fontSize);
    const lineHeight = parseFloat(textStyle.lineHeight);
    const nextLine = text.querySelector('.card-text-line + .card-text-line');
    const lineGap = nextLine ? parseFloat(getComputedStyle(nextLine).marginBlockStart) : 0;
    const short = text.textContent.trim() && !text.querySelector('img')
        && text.offsetHeight <= lineHeight * 2 + lineGap + 1
        && face.clientHeight - text.offsetHeight >= topSpace * 2
        && !hasActions && !topAligned;
    content.classList.toggle('short-text', Boolean(short));

    if (!minimum && !hasActions && content.clientHeight > 0 && content.scrollHeight > content.clientHeight) {
        const setSize = size => text.style.setProperty('--fitted-card-font-size', `${size}px`);
        // CSS clamps the measurement to the readable minimum.
        setSize(0);
        let min = parseFloat(textStyle.fontSize);
        let max = defaultSize;
        if (content.scrollHeight <= content.clientHeight) {
            while (max - min > 0.25) {
                const size = (min + max) / 2;
                setSize(size);
                if (content.scrollHeight <= content.clientHeight) min = size;
                else max = size;
            }
            setSize(min);
        }
    }
    content.classList.remove('measuring-text');
    content.scrollTop = scrollTop;
}
