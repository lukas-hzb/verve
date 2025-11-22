/**
 * Flashcard Module
 * Handles flashcard learning functionality including flip, feedback, and undo
 */

export class FlashcardManager {
    constructor(setId) {
        this.setId = setId;
        this.cards = [];
        this.currentCardIndex = 0;
        this.undoHistory = [];
        this.isPracticeMode = false;
        this.areControlsDisabled = false;

        // DOM elements
        this.cardFront = document.getElementById("card-front");
        this.cardBack = document.getElementById("card-back");
        this.flashcard = document.getElementById("flashcard");
        this.cardContainer = document.querySelector('.card-container');
        this.cardLevel = document.getElementById("card-level");
        this.flipBtn = document.getElementById("flip-btn");
        this.feedbackBtns = document.getElementById("feedback-btns");
        this.knownBtn = document.getElementById("known-btn");
        this.notKnownBtn = document.getElementById("not-known-btn");
        this.prevCardBtn = document.getElementById("back-btn");
        this.shuffleBtn = document.getElementById("shuffle-btn");
        this.practiceModeCheckbox = document.getElementById("practice-mode-checkbox");

        // Constants
        this.LEVEL_COLORS = {
            1: 'var(--level-1)',
            2: 'var(--level-2)',
            3: 'var(--level-3)',
            4: 'var(--level-4)',
            5: 'var(--level-5)'
        };

        this.ANIMATION_DURATION = 500; // milliseconds

        this.init();
    }

    async init() {
        this.attachEventListeners();
        this.attachKeyboardListeners();
        await this.fetchAndLoadCards();
    }

    attachEventListeners() {
        this.flipBtn?.addEventListener("click", () => {
            this.flipCard();
            this.flipBtn.blur();
        });
        this.knownBtn?.addEventListener("click", () => {
            this.handleFeedback(5);
            this.knownBtn.blur();
        });
        this.notKnownBtn?.addEventListener("click", () => {
            this.handleFeedback(2);
            this.notKnownBtn.blur();
        });
        this.prevCardBtn?.addEventListener("click", () => {
            this.undoLastCard();
            this.prevCardBtn.blur();
        });
        this.shuffleBtn?.addEventListener("click", () => {
            this.shuffleCards();
            this.shuffleBtn.blur();
        });
        this.practiceModeCheckbox?.addEventListener("change", (e) => this.togglePracticeMode(e.target.checked));
    }

    attachKeyboardListeners() {
        document.addEventListener('keydown', (event) => {
            // Ignore if user is typing in an input field
            if (document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'BUTTON') {
                return;
            }

            if (this.areControlsDisabled) return;

            const isFlipped = this.flashcard.classList.contains("flipped");

            if (event.code === 'Space' && !isFlipped && this.flipBtn.style.display !== 'none') {
                event.preventDefault();
                this.flipCard();
            } else if (isFlipped) {
                if (event.code === 'KeyA') { // 'a' for Didn't Know
                    event.preventDefault();
                    this.handleFeedback(2);
                } else if (event.code === 'KeyD') { // 'd' for Knew It
                    event.preventDefault();
                    this.handleFeedback(5);
                }
            }
        });
    }

    async fetchAndLoadCards() {
        const url = this.isPracticeMode
            ? `/api/set/${this.setId}/all`
            : `/api/set/${this.setId}`;

        try {
            const response = await fetch(url);
            this.cards = await response.json();

            this.undoHistory = [];
            this.updateBackButtonState();
            this.currentCardIndex = 0;

            if (this.isPracticeMode) {
                this.shuffleArray(this.cards);
            }

            if (this.cards.length > 0) {
                this.loadCard(0, true);
            } else {
                this.showEmptyMessage();
            }
        } catch (error) {
            console.error("Error fetching cards:", error);
            this.showErrorMessage("Failed to load cards");
        }
    }

    showEmptyMessage() {
        this.cardFront.textContent = this.isPracticeMode
            ? "This set is empty."
            : "No cards due for review!";
        this.cardBack.textContent = "";
        this.flipBtn.style.display = "none";
        this.feedbackBtns.style.display = "none";
        this.cardLevel.style.display = "none";
    }

    showErrorMessage(message) {
        this.cardFront.textContent = message;
        this.cardBack.textContent = "";
        this.flipBtn.style.display = "none";
        this.feedbackBtns.style.display = "none";
        this.cardLevel.style.display = "none";
    }

    updateCardContent(card) {
        this.cardFront.textContent = card.front;
        this.cardBack.textContent = card.back;
        this.cardLevel.textContent = `Level ${card.level}`;
        this.cardLevel.style.backgroundColor = this.LEVEL_COLORS[card.level] || '#ccc';
        this.cardLevel.style.display = this.isPracticeMode ? 'none' : 'block';
    }

    loadCard(index, isFirstLoad = false) {
        if (index < 0 || index >= this.cards.length) return;

        this.currentCardIndex = index;
        const card = this.cards[this.currentCardIndex];

        // Remove all animation classes
        this.cardContainer.classList.remove('swipe-out-right', 'swipe-out-left', 'load-in');

        if (isFirstLoad) {
            this.updateCardContent(card);
        }

        // Trigger reflow to restart animation
        void this.cardContainer.offsetHeight;
        this.cardContainer.classList.add('load-in');

        this.feedbackBtns.style.display = "none";
        this.flipBtn.style.display = "inline-flex";
    }

    flipCard() {
        if (this.flipBtn.style.display !== 'none') {
            this.flashcard.classList.add("flipped");
            this.flipBtn.style.display = "none";
            this.feedbackBtns.style.display = "flex";
        }
    }

    async handleFeedback(quality) {
        if (this.areControlsDisabled) return;

        const animationClass = quality === 5 ? 'swipe-out-right' : 'swipe-out-left';
        this.cardContainer.classList.add(animationClass);
        this.disableControls();

        setTimeout(async () => {
            const originalCard = { ...this.cards[this.currentCardIndex] };
            this.undoHistory.push(originalCard);
            this.updateBackButtonState();

            // Update card on server (only in learning mode)
            if (!this.isPracticeMode) {
                try {
                    await fetch("/api/update_card", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            set_id: this.setId,
                            card_front: originalCard.front,
                            quality: quality
                        })
                    });
                } catch (error) {
                    console.error("Error updating card:", error);
                }
            }

            // Move to next card or show completion
            if (this.currentCardIndex + 1 < this.cards.length) {
                this.prepareNextCard();
            } else {
                this.showCompletionMessage();
            }

            this.enableControls();
        }, this.ANIMATION_DURATION);
    }

    prepareNextCard() {
        const nextCardIndex = this.currentCardIndex + 1;
        const nextCard = this.cards[nextCardIndex];

        // Flip card back to front without animation while invisible
        this.flashcard.style.transition = 'none';
        this.flashcard.classList.remove('flipped');
        void this.flashcard.offsetHeight; // Force reflow
        this.flashcard.style.transition = ''; // Re-enable animation

        // Update content now that it's safely on the front face
        this.updateCardContent(nextCard);
        this.loadCard(nextCardIndex);
    }

    showCompletionMessage() {
        this.cardContainer.classList.remove('swipe-out-right', 'swipe-out-left');
        this.flashcard.classList.remove("flipped");
        this.cardFront.textContent = "All cards reviewed!";
        this.cardBack.textContent = "";
        this.feedbackBtns.style.display = "none";
        this.cardLevel.style.display = "none";
        this.flipBtn.style.display = 'none';

        void this.cardContainer.offsetHeight;
        this.cardContainer.classList.add('load-in');
    }

    async undoLastCard() {
        if (this.undoHistory.length === 0) return;

        const cardToRestore = this.undoHistory.pop();
        this.updateBackButtonState();
        const cardIndexInSet = this.cards.findIndex(c => c.front === cardToRestore.front);

        if (cardIndexInSet !== -1) {
            this.cards[cardIndexInSet] = cardToRestore;
            this.updateCardContent(cardToRestore);
            this.loadCard(cardIndexInSet);

            // Restore on server (only in learning mode)
            if (!this.isPracticeMode) {
                try {
                    await fetch("/api/restore_card", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            set_id: this.setId,
                            card_front: cardToRestore.front,
                            level: cardToRestore.level,
                            next_review: cardToRestore.next_review
                        })
                    });
                } catch (error) {
                    console.error("Error restoring card:", error);
                }
            }
        }
    }

    shuffleCards() {
        this.shuffleArray(this.cards);
        this.undoHistory = [];
        this.updateBackButtonState();
        this.loadCard(0, true);
    }

    togglePracticeMode(enabled) {
        this.isPracticeMode = enabled;
        this.fetchAndLoadCards();
    }

    /**
     * Fisher-Yates shuffle algorithm
     */
    shuffleArray(array) {
        for (let i = array.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [array[i], array[j]] = [array[j], array[i]];
        }
    }

    updateBackButtonState() {
        if (this.prevCardBtn) {
            this.prevCardBtn.disabled = this.undoHistory.length === 0 || this.areControlsDisabled;
        }
    }

    disableControls() {
        this.areControlsDisabled = true;
        if (this.flipBtn) this.flipBtn.disabled = true;
        if (this.knownBtn) this.knownBtn.disabled = true;
        if (this.notKnownBtn) this.notKnownBtn.disabled = true;
        if (this.prevCardBtn) this.prevCardBtn.disabled = true;
        if (this.shuffleBtn) this.shuffleBtn.disabled = true;
        if (this.practiceModeCheckbox) this.practiceModeCheckbox.disabled = true;
    }

    enableControls() {
        this.areControlsDisabled = false;
        if (this.flipBtn) this.flipBtn.disabled = false;
        if (this.knownBtn) this.knownBtn.disabled = false;
        if (this.notKnownBtn) this.notKnownBtn.disabled = false;
        // Back button state depends on history
        this.updateBackButtonState();
        if (this.shuffleBtn) this.shuffleBtn.disabled = false;
        if (this.practiceModeCheckbox) this.practiceModeCheckbox.disabled = false;
    }
}

