/**
 * Verve - Main Application JavaScript
 * 
 * This file initializes the application modules based on the current page.
 * Modules are imported dynamically to keep code organized and maintainable.
 */

import { SidebarManager } from './modules/sidebar.js';
import { FlashcardManager } from './modules/flashcard.js';
import { StatsManager } from './modules/stats.js';


/**
 * Application initialization
 */
document.addEventListener("DOMContentLoaded", () => {
    // Initialize sidebar on all pages
    new SidebarManager();

    // Determine current page and initialize appropriate module
    const currentPath = window.location.pathname;

    if (currentPath.startsWith("/set/")) {
        initializeLearningPage(currentPath);
    } else if (currentPath.startsWith("/stats/")) {
        initializeStatsPage(currentPath);
    }

    // Initialize search bar on home page
    initializeSearchBar();

    // Expose global functions for HTML event handlers
    setupGlobalFunctions();
});


/**
 * Initialize the learning/flashcard page
 * @param {string} path - Current URL path
 */
function initializeLearningPage(path) {
    // Path format: /set/<id>
    const setId = path.split("/")[2];
    if (setId) {
        new FlashcardManager(setId);
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
        new StatsManager(setId);
    }
}


/**
 * Initialize the search bar for filtering sets on the home page
 */
function initializeSearchBar() {
    const searchInput = document.getElementById('setSearchInput');
    if (!searchInput) return;

    searchInput.addEventListener('input', function () {
        const searchTerm = this.value.toLowerCase().trim();
        const setCards = document.querySelectorAll('.set-card');
        const createNewCard = document.querySelector('.create-new-card');

        setCards.forEach(card => {
            // Get the set name from the h3 inside the card
            const setNameElement = card.querySelector('h3');
            if (!setNameElement) return;

            const setName = setNameElement.textContent.toLowerCase();

            if (setName.includes(searchTerm)) {
                card.style.display = '';
            } else {
                card.style.display = 'none';
            }
        });

        // Hide create new card when searching, show when search is empty
        if (createNewCard) {
            if (searchTerm) {
                createNewCard.style.display = 'none';
            } else {
                createNewCard.style.display = '';
            }
        }
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
                window.location.reload();
            } else {
                alert('Error: ' + (data.message || 'Failed to create set'));
            }
        } catch (error) {
            console.error('Error creating set:', error);
            alert('An error occurred while creating the set.');
        }
    };

    // Delete Set Handler
    window.deleteVocabSet = async function (setId, setName) {
        window.showConfirmationModal({
            title: "Delete Set",
            message: `Are you sure you want to delete the set "${setName}"? This cannot be undone.`,
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
                        alert('Error: ' + (data.message || 'Failed to delete set'));
                    }
                } catch (error) {
                    console.error('Error deleting set:', error);
                    alert('An error occurred while deleting the set.');
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
