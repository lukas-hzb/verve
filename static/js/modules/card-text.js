/** Interpret escaped newlines without changing the stored card text. */
export function formatCardText(text) {
    return text.replace(/\\r\\n|\\n|\\r/g, '\n');
}

/** Accept direct HTTPS images or Markdown image lines; never interpret HTML. */
export function parseCardImage(line) {
    const markdown = line.trim().match(/^!\[([^\]]*)\]\((https:\/\/\S+)\)$/i);
    const source = markdown ? markdown[2] : line.trim();
    try {
        const url = new URL(source);
        if (url.protocol !== 'https:' || url.username || url.password) return null;
        if (!markdown && !/\.(avif|gif|jpe?g|png|svg|webp)$/i.test(url.pathname)) return null;
        return { url: url.href, alt: markdown?.[1] || 'Card Image' };
    } catch {
        return null;
    }
}

export function renderCardContent(element, text, { lazy = false, spacedLineBreaks = false } = {}) {
    const formatted = formatCardText(text);
    const lines = formatted.split(spacedLineBreaks ? /\r\n?|\n/ : '\n');
    const separateLines = spacedLineBreaks && lines.length > 1;
    const images = lines.map(parseCardImage);
    if (!separateLines && !images.some(Boolean)) {
        element.textContent = formatted;
        return;
    }
    const fragment = document.createDocumentFragment();
    lines.forEach((line, index) => {
        if (index) fragment.append(document.createTextNode('\n'));
        const target = separateLines ? document.createElement('span') : fragment;
        if (separateLines) {
            target.className = 'card-text-line';
            fragment.append(target);
        }
        const image = images[index];
        if (!image) {
            target.append(document.createTextNode(line));
            return;
        }
        const wrapper = document.createElement('span');
        wrapper.className = 'card-media';
        const img = document.createElement('img');
        img.alt = image.alt;
        img.referrerPolicy = 'no-referrer';
        img.decoding = 'async';
        img.loading = lazy ? 'lazy' : 'eager';
        img.addEventListener('error', () => {
            wrapper.textContent = 'Image unavailable';
            wrapper.classList.add('card-media-error');
        }, { once: true });
        img.src = image.url;
        wrapper.append(img);
        target.append(wrapper);
    });
    element.replaceChildren(fragment);
}
