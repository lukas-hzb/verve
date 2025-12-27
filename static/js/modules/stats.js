/**
 * Statistics Module
 * Handles statistics display and visualization
 */

export class StatsManager {
    constructor(setId) {
        this.setId = setId;

        // DOM elements
        this.totalCardsEl = document.getElementById("total-cards");
        this.levelProgressEl = document.getElementById("level-progress");
        this.resetSetBtn = document.getElementById("reset-set-btn");
        this.masteryStatValueEl = document.getElementById("mastery-stat-value");
        this.masteryStatIconWrapperEl = document.getElementById("mastery-stat-icon-wrapper");

        // Constants
        this.LEVEL_COLORS = {
            1: 'var(--level-1)',
            2: 'var(--level-2)',
            3: 'var(--level-3)',
            4: 'var(--level-4)',
            5: 'var(--level-5)'
        };

        this.MAX_LEVEL_DISPLAY = 5;

        this.init();
    }

    async init() {
        this.attachEventListeners();
        await this.fetchAndDisplayStats();
    }

    attachEventListeners() {
        this.resetSetBtn?.addEventListener("click", () => this.confirmAndResetSet());
    }

    async fetchAndDisplayStats() {
        try {
            const response = await fetch(`/api/stats/${this.setId}`);
            const stats = await response.json();

            this.displayStats(stats);
        } catch (error) {
            console.error("Error fetching statistics:", error);
            this.showError("Failed to load statistics");
        }
    }

    displayStats(stats) {
        // Display total cards
        this.totalCardsEl.textContent = stats.total_cards;

        // Calculate and display Mastery (Level 5)
        const masteryCount = stats.level_counts[this.MAX_LEVEL_DISPLAY] || 0;
        const masteryPercentage = stats.total_cards > 0
            ? (masteryCount / stats.total_cards) * 100
            : 0;

        if (this.masteryStatValueEl) {
            this.masteryStatValueEl.textContent = `${Math.round(masteryPercentage)}%`;
        }

        if (this.masteryStatIconWrapperEl) {
            // Set color to Level 5 color (Accent 5) to match the last level
            this.masteryStatIconWrapperEl.style.setProperty('--icon-color', 'var(--color-accent-5)');
        }

        // Clear previous progress bars
        this.levelProgressEl.innerHTML = "";
        this.levelProgressEl.className = "card-progress"; // Add container class

        // Create progress bars for each level
        for (let level = 1; level <= this.MAX_LEVEL_DISPLAY; level++) {
            const count = stats.level_counts[level] || 0;
            const percentage = stats.total_cards > 0
                ? (count / stats.total_cards) * 100
                : 0;

            this.createProgressBar(level, count, percentage);
        }
    }

    createProgressBar(level, count, percentage) {
        const progressItem = document.createElement("div");
        progressItem.className = "card-progress-item";

        // Map level to accent class (assuming 1-5 maps to accent-1 to accent-5)
        const accentClass = `bg-accent-${level}`;

        progressItem.innerHTML = `
            <span class="card-progress-label">Level ${level} (${count} cards)</span>
            <div class="card-progress-bar-container">
                <div class="card-progress-bar ${accentClass}" style="width: ${percentage}%;">
                    <span class="card-progress-value">${Math.round(percentage)}%</span>
                </div>
            </div>
        `;
        this.levelProgressEl.appendChild(progressItem);
    }

    confirmAndResetSet() {
        window.showConfirmationModal({
            title: "Reset Set",
            message: "Are you sure you want to reset this set? All cards will be moved to Level 1.",
            confirmText: "Reset",
            confirmClass: "btn-danger",
            onConfirm: async () => {
                try {
                    const response = await fetch(`/api/reset_set/${this.setId}`, {
                        method: "POST"
                    });

                    if (response.ok) {
                        // Refresh statistics after reset
                        await this.fetchAndDisplayStats();
                    } else {
                        this.showError("Failed to reset set");
                    }
                } catch (error) {
                    console.error("Error resetting set:", error);
                    this.showError("Failed to reset set");
                }
            }
        });
    }

    showError(message) {
        this.totalCardsEl.textContent = message;
        this.levelProgressEl.innerHTML = "";
    }
}
