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
    // Initialize sidebar on all pages
    new SidebarManager();
    initializeWelcomeMascot();
    initializeStudyInfo();
    initializeStudyModePicker();
    initializeStudyUtilityBar();
    initializeStudyCardPosition();
    initializeStudyCardTextAlignment();

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
        const height = Math.max(0, Math.min(bounds.width * 5 / 8,
            aboveSpace * 2, belowSpace * 2));
        page.style.setProperty('--study-card-height', `${height}px`);
        page.style.setProperty('--study-card-offset',
            `${Math.max(0, center - height / 2 - headingBottom - 12 - progressHeight - 20)}px`);
    };
    const observer = new ResizeObserver(positionCard);
    [page, above, progress, actions, toolbar].forEach(element => observer.observe(element));
    window.addEventListener('resize', positionCard);
    mobile.addEventListener('change', () => {
        previousLayout = '';
        positionCard();
    });
    positionCard();
}

function initializeStudyCardTextAlignment() {
    const flashcard = document.querySelector('.study-page .flashcard');
    if (!flashcard) return;
    const faces = [...flashcard.querySelectorAll('.flashcard-front, .flashcard-back')];
    const alignText = () => faces.forEach(face => {
        const content = face.querySelector('.flashcard-content');
        const text = content.querySelector('p');
        const lineHeight = parseFloat(getComputedStyle(text).lineHeight);
        const topSpace = parseFloat(getComputedStyle(face).getPropertyValue('--study-content-top'));
        const short = text.textContent.trim() && !text.querySelector('img')
            && text.offsetHeight <= lineHeight * 2 + 1
            && face.clientHeight - text.offsetHeight >= topSpace * 2
            && !content.querySelector('.study-completion:not([hidden]), .study-empty-action:not([hidden])');
        content.classList.toggle('short-text', Boolean(short));
    });
    const resize = new ResizeObserver(alignText);
    faces.forEach(face => {
        resize.observe(face);
        resize.observe(face.querySelector('.flashcard-content > p'));
    });
    new MutationObserver(alignText).observe(flashcard, {
        subtree: true, childList: true, characterData: true,
        attributes: true, attributeFilter: ['hidden'],
    });
    alignText();
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
