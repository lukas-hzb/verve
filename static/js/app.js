import { initializeOverlays } from './modules/overlays.js';
import { initializeFolders } from './modules/folders.js';
/**
 * Verve - Main Application JavaScript
 * 
 * This file initializes the application modules based on the current page.
 * Modules are imported dynamically to keep code organized and maintainable.
 */

import { SidebarManager } from './modules/sidebar.js';
import { FlashcardManager } from './modules/flashcard.js';
import { StatsManager } from './modules/stats.js';
import { initializeWelcomeMascot } from './modules/mascot.js';
import { initializeStudyInfo } from './modules/study-info.js';
import { initializeStudyModePicker } from './modules/study-mode-picker.js';


/**
 * Application initialization
 */
document.addEventListener("DOMContentLoaded", () => {
    initializeOverlays();
    // Initialize sidebar on all pages
    new SidebarManager();
    initializeWelcomeMascot();
    initializeStudyInfo();
    initializeStudyModePicker();
    initializeStudyUtilityBar();
    const resizeStudyCard = initializeStudyCardPosition();
    initializeStudyCardTextLayout(resizeStudyCard);

    // Determine current page and initialize appropriate module
    initializeFolders();
    const currentPath = window.location.pathname;

    if (/^\/set\/[^/]+\/?$/.test(currentPath) || /^\/folder\/[^/]+\/learn\/?$/.test(currentPath)) {
        initializeLearningPage(currentPath);
    } else if (currentPath.startsWith("/stats/")) {
        initializeStatsPage(currentPath);
    }

    // Initialize search bar on home page
    initializeSearchBar();

    // Expose global functions for HTML event handlers
    setupGlobalFunctions();
});

function initializeStudyUtilityBar() {
    const toolbar = document.querySelector('.study-utility-bar');
    if (!toolbar) return;
    const anchor = document.createComment('Round Actions');
    toolbar.before(anchor);
    const mobile = window.matchMedia('(max-width: 768px)');
    const placeToolbar = () => {
        // Keep the fixed bar outside the page's container-query containing block.
        if (mobile.matches) document.body.append(toolbar);
        else anchor.after(toolbar);
    };
    placeToolbar();
    mobile.addEventListener('change', placeToolbar);
}

function initializeStudyCardPosition() {
    const page = document.querySelector('.study-page');
    if (!page) return;
    const above = page.querySelector('.study-above-card');
    const actions = page.querySelector('.study-actions');
    const toolbar = document.querySelector('.study-utility-bar');
    const progress = page.querySelector('.study-progress');
    const group = page.querySelector('.study-card-and-actions');
    const mobile = window.matchMedia('(max-width: 768px)');
    group.prepend(progress);
    let previousLayout = '';
    let baseHeight = 0;
    let baseOffset = 0;
    let maxCenteredHeight = 0;
    let requiredHeight = 0;
    let appliedHeight;
    let appliedOffset;
    const applySize = () => {
        // Grow equally in both directions to keep the card centered.
        const extraHeight = Math.max(0, Math.min(requiredHeight - baseHeight, maxCenteredHeight - baseHeight, 96));
        const height = baseHeight + extraHeight;
        const offset = baseOffset - extraHeight / 2;
        if (height === appliedHeight && offset === appliedOffset) return;
        appliedHeight = height;
        appliedOffset = offset;
        page.style.setProperty('--study-card-height', `${height}px`);
        page.style.setProperty('--study-card-offset', `${offset}px`);
    };
    const positionCard = () => {
        if (!mobile.matches) return;
        const bounds = page.getBoundingClientRect();
        // Safari resizes its viewport while scrolling its browser bars away.
        // Recenter only for a changed content layout or width, never height alone.
        const progressHeight = progress.getBoundingClientRect().height;
        const layout = [bounds.width, above.offsetHeight, progressHeight, actions.offsetHeight].join(':');
        if (layout === previousLayout) return;
        previousLayout = layout;
        const center = window.innerHeight / 2;
        // Use document coordinates so scrolling never pins the card to the viewport.
        const headingBottom = above.getBoundingClientRect().bottom + window.scrollY;
        const aboveSpace = center - headingBottom - 12 - progressHeight - 20;
        const belowSpace = toolbar.getBoundingClientRect().top - center
            - actions.getBoundingClientRect().height - 20 - 12;
        maxCenteredHeight = Math.max(0, 2 * Math.min(aboveSpace, belowSpace));
        baseHeight = Math.min(bounds.width * 5 / 8, maxCenteredHeight);
        baseOffset = Math.max(0, aboveSpace - baseHeight / 2);
        applySize();
    };
    const observer = new ResizeObserver(positionCard);
    [page, above, progress, actions, toolbar].forEach(element => observer.observe(element));
    window.addEventListener('resize', positionCard);
    mobile.addEventListener('change', () => {
        previousLayout = '';
        positionCard();
    });
    positionCard();
    return height => {
        requiredHeight = height;
        if (mobile.matches) applySize();
    };
}

function initializeStudyCardTextLayout(resizeStudyCard) {
    const flashcard = document.querySelector('.study-page .flashcard');
    if (!flashcard) return;
    const mobile = window.matchMedia('(max-width: 768px)');
    const panels = [...flashcard.querySelectorAll('.flashcard-front, .flashcard-back')].map(face => {
        const content = face.querySelector('.flashcard-content');
        return { face, content, text: content.querySelector('p') };
    });
    const fitText = ({ face, content, text, scrollTop, topSpace, hasActions }) => {
        const textStyle = getComputedStyle(text);
        const defaultSize = parseFloat(textStyle.fontSize);
        const lineHeight = parseFloat(textStyle.lineHeight);
        const nextLine = text.querySelector('.card-text-line + .card-text-line');
        const lineGap = nextLine ? parseFloat(getComputedStyle(nextLine).marginBlockStart) : 0;
        const short = text.textContent.trim() && !text.querySelector('img')
            && text.offsetHeight <= lineHeight * 2 + lineGap + 1
            && face.clientHeight - text.offsetHeight >= topSpace * 2
            && !hasActions;
        content.classList.toggle('short-text', Boolean(short));

        if (!hasActions && content.clientHeight > 0 && content.scrollHeight > content.clientHeight) {
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
    };
    const layoutText = () => {
        const layouts = panels.map(panel => {
            const { face, content, text } = panel;
            const scrollTop = content.scrollTop;
            const hasActions = content.querySelector('.study-completion:not([hidden]), .study-empty-action:not([hidden])');
            content.classList.add('measuring-text');
            content.classList.remove('short-text');
            text.style.removeProperty('--fitted-card-font-size');
            const topSpace = parseFloat(getComputedStyle(content).top);
            return { ...panel, scrollTop, topSpace, hasActions };
        });
        if (mobile.matches) {
            const requiredHeights = layouts.map(({ face, content, text, topSpace, hasActions }) => {
                if (hasActions || !text.offsetHeight) return 0;
                // Measure media independently of the current card height.
                content.classList.add('measuring-height');
                const height = text.offsetHeight + topSpace + parseFloat(getComputedStyle(content).paddingBottom)
                    + face.offsetHeight - face.clientHeight;
                content.classList.remove('measuring-height');
                return height;
            });
            resizeStudyCard(Math.max(...requiredHeights));
        }
        layouts.forEach(fitText);
    };
    const resize = new ResizeObserver(layoutText);
    panels.forEach(({ face }) => resize.observe(face));
    new MutationObserver(layoutText).observe(flashcard, {
        subtree: true, childList: true, characterData: true,
        attributes: true, attributeFilter: ['hidden'],
    });
    flashcard.addEventListener('load', layoutText, true);
    flashcard.addEventListener('error', layoutText, true);
    window.addEventListener('resize', layoutText);
    document.fonts.ready.then(layoutText);
    layoutText();
}


/**
 * Initialize the learning/flashcard page
 * @param {string} path - Current URL path
 */
function initializeLearningPage(path) {
    // Path format: /set/<id>
    const setId = path.split("/")[2];
    if (setId) {
        new FlashcardManager(setId, JSON.parse(document.getElementById('initial-page-data').textContent));
    }
}


/**
 * Initialize the statistics page
 * @param {string} path - Current URL path
 */
function initializeStatsPage(path) {
    // Path format: /stats/<id>
    const setId = path.split("/")[2];
    if (setId) {
        new StatsManager(setId, JSON.parse(document.getElementById('initial-page-data').textContent));
    }
}


/**
 * Initialize the search bar for filtering sets on the home page
 */
function initializeSearchBar() {
    const searchInput = document.getElementById('setSearchInput');
    const grid = document.getElementById('setsGrid');
    if (!searchInput || !grid) return;
    const normalize = value => value.replaceAll('_', ' ').toLowerCase();

    searchInput.addEventListener('input', function () {
        const searchTerm = normalize(this.value).trim();
        grid.querySelectorAll('.set-card').forEach(card => {
            const title = card.querySelector('h3');
            if (!title) return;
            const names = [title.textContent, ...JSON.parse(card.dataset.containedSetNames || '[]')];
            card.style.display = names.some(name => normalize(name).includes(searchTerm)) ? '' : 'none';
        });
        const createNewCard = grid.querySelector('.create-new-card');
        if (createNewCard) createNewCard.style.display = searchTerm ? 'none' : '';
    });
}

/**
 * Setup global functions for UI interactions
 * These need to be on the window object because they are called from HTML attributes
 */
function setupGlobalFunctions() {
    // Modal functions
    window.openCreateSetModal = function () {
        const modal = document.getElementById('createSetModal');
        if (modal) {
            modal.classList.add('active');
            document.getElementById('setName').focus();
        }
    };

    window.closeCreateSetModal = function () {
        const modal = document.getElementById('createSetModal');
        if (modal) {
            modal.classList.remove('active');
            document.getElementById('createSetForm').reset();
        }
    };

    // Close modal when clicking outside
    window.onclick = function (event) {
        const modal = document.getElementById('createSetModal');
        if (modal && event.target == modal) {
            window.closeCreateSetModal();
        }

        const confirmModal = document.getElementById('confirmationModal');
        if (confirmModal && event.target == confirmModal) {
            window.closeConfirmationModal();
        }
    };

    // Create Set Handler
    window.handleCreateSet = async function (event) {
        event.preventDefault();

        const nameInput = document.getElementById('setName');
        const name = nameInput.value.trim();

        if (!name) return;

        try {
            const response = await fetch('/api/vocab_sets', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ name: name })
            });

            const data = await response.json();

            if (data.status === 'success') {
                window.location.assign(`/set/${encodeURIComponent(data.id)}/overview`);
            } else {
                alert('Error: ' + (data.message || 'Failed to create Set'));
            }
        } catch (error) {
            console.error('Error creating Set:', error);
            alert('An Error occurred while creating the Set.');
        }
    };

    // Delete Set Handler
    window.deleteVocabSet = async function (setId, setName) {
        window.showConfirmationModal({
            title: "Delete Set",
            message: `Are you sure you want to delete the Set "${setName}"? This cannot be undone.`,
            confirmText: "Delete Set",
            confirmClass: "btn-danger",
            onConfirm: async () => {
                try {
                    const response = await fetch(`/api/vocab_sets/${setId}`, {
                        method: 'DELETE'
                    });

                    const data = await response.json();

                    if (data.status === 'success') {
                        window.location.reload();
                    } else {
                        alert('Error: ' + (data.message || 'Failed to delete Set'));
                    }
                } catch (error) {
                    console.error('Error deleting Set:', error);
                    alert('An Error occurred while deleting the Set.');
                }
            }
        });
    };

    // Generic Confirmation Modal
    window.showConfirmationModal = function (options) {
        const modal = document.getElementById('confirmationModal');
        const titleEl = document.getElementById('confirmationTitle');
        const messageEl = document.getElementById('confirmationMessage');
        const confirmBtn = document.getElementById('confirmationConfirmBtn');

        if (!modal || !titleEl || !messageEl || !confirmBtn) return;

        titleEl.textContent = options.title || 'Confirm Action';
        messageEl.textContent = options.message || 'Are you sure?';

        // Reset button state
        confirmBtn.className = 'btn ' + (options.confirmClass || 'btn-danger');
        confirmBtn.textContent = options.confirmText || 'Confirm';

        // Remove old event listeners
        const newBtn = confirmBtn.cloneNode(true);
        confirmBtn.parentNode.replaceChild(newBtn, confirmBtn);

        newBtn.onclick = function () {
            if (options.onConfirm) options.onConfirm();
            window.closeConfirmationModal();
        };

        modal.classList.add('active');
    };

    window.closeConfirmationModal = function () {
        const modal = document.getElementById('confirmationModal');
        if (modal) {
            modal.classList.remove('active');
        }
    };

    // Note: window.onclick already handles clicking outside (merged above)
}
