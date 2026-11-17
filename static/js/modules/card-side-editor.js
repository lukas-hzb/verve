import { mountMarkdownEditor, plainToMarkdown } from '../card-markdown.js';
import { formatCardText, parseCardImage, renderCardContent } from './card-text.js';
import { connectAnchoredMenu } from './anchored-menu.js';

const examples = {
    front: {
        text: 'What is active recall?',
        markdown: '**What is active recall?**',
    },
    back: {
        text: 'Try to recall the answer from memory before you check.',
        markdown: [
            '## Active recall',
            '**Recall** the answer *from memory*.',
            '',
            '1. Cover the answer.',
            '2. Say it aloud.',
            '',
            '[Learn more](https://example.com)',
        ].join('\n'),
    },
};

export function initializeCardSide(panel) {
    const source = panel.querySelector('textarea');
    const format = panel.querySelector('input[type="hidden"]');
    const surface = panel.querySelector('[data-rich-input]');
    const placeholder = surface.querySelector('[data-rich-placeholder]');
    const example = examples[source.name];
    const toggle = panel.querySelector('[data-source-toggle]');
    const tools = panel.querySelector('[data-format-tools]');
    const toolsTrigger = panel.querySelector('[data-tools-trigger]');
    const mobile = window.matchMedia('(max-width: 768px)');
    const picker = panel.querySelector('[data-color-picker]');
    const colorTrigger = tools.querySelector('.card-color-trigger');
    const colorButtons = picker.querySelectorAll('[data-card-color]');
    const headingPicker = panel.querySelector('[data-heading-picker]');
    const linkPicker = panel.querySelector('[data-link-picker]');
    const linkInput = linkPicker.querySelector('input');
    const linkError = linkPicker.querySelector('[data-link-error]');
    const removeLink = linkPicker.querySelector('[data-remove-link]');
    const enable = panel.querySelector('[data-enable-markdown]');
    let editor;

    renderCardContent(placeholder, example.markdown, { format: 'markdown' });
    for (const menu of [tools, picker, headingPicker, linkPicker]) connectAnchoredMenu(menu);
    // Keep the editor selection and mobile keyboard when using formatting controls.
    for (const button of panel.querySelectorAll('.card-side-toolbar button:not([data-source-toggle]):not([data-enable-markdown])')) {
        button.addEventListener('pointerdown', event => {
            if (event.button === 0) event.preventDefault();
        });
        button.addEventListener('mousedown', event => event.preventDefault());
    }

    function closeTools() {
        if (tools.matches(':popover-open')) tools.hidePopover();
    }

    function updateToolsPresentation() {
        closeTools();
        tools.toggleAttribute('popover', mobile.matches);
        tools.classList.toggle('anchored-menu', mobile.matches);
        toolsTrigger.hidden = !mobile.matches || tools.hidden;
        toolsTrigger.inert = tools.inert;
    }

    mobile.addEventListener('change', updateToolsPresentation);

    function showColor(level) {
        if (level) colorTrigger.dataset.level = level;
        else delete colorTrigger.dataset.level;
        for (const button of colorButtons) {
            if (button.dataset.cardColor) button.setAttribute('aria-pressed', String(button.dataset.cardColor === level));
        }
    }

    function setMode(showSource = false) {
        const markdown = format.value === 'markdown';
        const rich = markdown && !showSource;
        closeTools();
        for (const menu of tools.querySelectorAll(':popover-open')) menu.hidePopover();
        editor?.destroy();
        editor = null;
        source.hidden = rich;
        source.required = !rich;
        surface.hidden = !rich;
        source.wrap = showSource ? 'off' : 'soft';
        source.placeholder = showSource ? example.markdown : example.text;
        placeholder.hidden = !rich || source.value !== '';
        enable.hidden = markdown;
        toggle.hidden = !markdown;
        tools.hidden = !markdown;
        tools.inert = !rich;
        updateToolsPresentation();
        toggle.setAttribute('aria-pressed', String(showSource));
        toggle.title = showSource ? 'Switch to visual editor' : 'Switch to Markdown source';
        if (rich) {
            editor = mountMarkdownEditor(surface, source.value, {
                'aria-labelledby': source.id + '-label',
                'aria-placeholder': example.text,
            }, value => {
                source.value = value;
                placeholder.hidden = value !== '';
                source.dispatchEvent(new Event('input', { bubbles: true }));
            }, showColor);
        }
    }

    toggle.addEventListener('click', () => setMode(toggle.getAttribute('aria-pressed') !== 'true'));
    enable.addEventListener('click', () => {
        source.value = plainToMarkdown(formatCardText(source.value), parseCardImage);
        format.value = 'markdown';
        setMode();
        source.dispatchEvent(new Event('input', { bubbles: true }));
    });
    for (const button of panel.querySelectorAll('[data-markdown-command]')) {
        button.addEventListener('click', () => {
            closeTools();
            editor?.run(button.dataset.markdownCommand);
        });
    }

    for (const button of colorButtons) {
        button.addEventListener('click', () => {
            picker.hidePopover();
            closeTools();
            editor?.color(button.dataset.cardColor);
        });
    }

    for (const button of headingPicker.querySelectorAll('[data-heading-level]')) {
        button.addEventListener('click', () => {
            headingPicker.hidePopover();
            closeTools();
            editor?.heading(Number(button.dataset.headingLevel));
        });
    }

    function clearLinkError() {
        linkError.hidden = true;
        linkInput.removeAttribute('aria-invalid');
    }

    function applyLink() {
        const href = linkInput.value.trim();
        if (href && editor?.setLink(href)) {
            linkPicker.hidePopover();
            closeTools();
        } else {
            linkError.hidden = false;
            linkInput.setAttribute('aria-invalid', 'true');
            linkInput.focus();
        }
    }

    linkPicker.addEventListener('toggle', event => {
        if (event.newState !== 'open' || !editor) return;
        const href = editor.linkHref();
        linkInput.value = href;
        removeLink.hidden = !href;
        clearLinkError();
        linkInput.focus({ preventScroll: true });
        linkInput.select();
    });
    linkInput.addEventListener('input', clearLinkError);
    linkInput.addEventListener('keydown', event => {
        if (event.key !== 'Enter') return;
        event.preventDefault();
        applyLink();
    });
    linkPicker.querySelector('[data-apply-link]').addEventListener('click', applyLink);
    removeLink.addEventListener('click', () => {
        editor?.setLink('');
        linkPicker.hidePopover();
        closeTools();
    });

    return (card = {}) => {
        source.value = card[source.name] ?? '';
        format.value = card[format.name] || panel.dataset.defaultFormat;
        setMode();
    };
}
