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

    // Initialize Feather icons
    if (typeof feather !== 'undefined') {
        feather.replace();
    }

    // Determine current page and initialize appropriate module
    const currentPath = window.location.pathname;

    if (currentPath.startsWith("/set/")) {
        initializeLearningPage(currentPath);
    } else if (currentPath.startsWith("/stats/")) {
        initializeStatsPage(currentPath);
    }

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
 * Setup global functions for UI interactions
 * These need to be on the window object because they are called from HTML attributes
 */
function setupGlobalFunctions() {
    // Modal functions
    window.openCreateSetModal = function () {
        const modal = document.getElementById('createSetModal');
        if (modal) {
            modal.style.display = 'block';
            document.getElementById('setName').focus();
        }
    };

    window.closeCreateSetModal = function () {
        const modal = document.getElementById('createSetModal');
        if (modal) {
            modal.style.display = 'none';
            document.getElementById('createSetForm').reset();
        }
    };

    // Close modal when clicking outside
    window.onclick = function (event) {
        const modal = document.getElementById('createSetModal');
        if (event.target == modal) {
            window.closeCreateSetModal();
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

        modal.style.display = 'block';
    };

    window.closeConfirmationModal = function () {
        const modal = document.getElementById('confirmationModal');
        if (modal) {
            modal.style.display = 'none';
        }
    };

    // Close confirmation modal when clicking outside
    const existingOnClick = window.onclick;
    window.onclick = function (event) {
        if (existingOnClick) existingOnClick(event);

        const modal = document.getElementById('confirmationModal');
        if (event.target == modal) {
            window.closeConfirmationModal();
        }
    };
}
