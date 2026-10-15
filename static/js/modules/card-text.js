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
        return { url: url.href, alt: markdown?.[1] || 'Card image' };
    } catch {
        return null;
    }
}

export function renderCardContent(element, text, { lazy = false } = {}) {
    const formatted = formatCardText(text);
    // Keep plain cards as text, including their original paragraph spacing.
    if (!formatted.split('\n').some(line => parseCardImage(line))) {
        element.textContent = formatted;
        return;
    }
    const fragment = document.createDocumentFragment();
    formatted.split('\n').forEach((line, index) => {
        if (index) fragment.append(document.createTextNode('\n'));
        const image = parseCardImage(line);
        if (!image) {
            fragment.append(document.createTextNode(line));
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
        fragment.append(wrapper);
    });
    element.replaceChildren(fragment);
}
