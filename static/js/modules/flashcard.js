/**
 * Flashcard Module
 * Handles flashcard learning functionality including persistence, shuffle, and progress
 */

export class FlashcardManager {
    constructor(setId) {
        this.setId = setId;
        
        // Session
        this.cards = [];
        this.currentCardIndex = 0;
        this.sessionStats = { correct: 0, wrong: 0, total: 0 };
        this.undoHistory = [];
        
        // Mode
        this.isPracticeMode = false;
        this.isWrongAnswersMode = false;
        
        // Storage keys for session persistence (separate for each mode)
        this.learningStorageKey = `flashcardSession_LEARNING_${this.setId}`;
        this.practiceStorageKey = `flashcardSession_PRACTICE_${this.setId}`;
        
        // Sync queue for delayed API requests
        this.syncQueue = [];
        this.processingSync = false;
        
        // Other state
        this.areControlsDisabled = false;
        
        // DOM elements
        this.cardFront = document.getElementById("card-front");
        this.cardBack = document.getElementById("card-back");
        this.flashcard = document.getElementById("flashcard");
        this.cardContainer = document.getElementById('flashcard-wrapper') || document.querySelector('.card-container');
        this.cardLevel = document.getElementById("card-level");
        this.flipBtn = document.getElementById("flip-btn");
        this.feedbackBtns = document.getElementById("feedback-btns");
        this.knownBtn = document.getElementById("known-btn");
        this.notKnownBtn = document.getElementById("not-known-btn");
        this.prevCardBtn = document.getElementById("back-btn");
        this.shuffleBtn = document.getElementById("shuffle-btn");
        this.restartBtn = document.getElementById("restart-btn");
        this.practiceModeCheckbox = document.getElementById("practice-mode-checkbox");
        this.wrongAnswersCheckbox = document.getElementById("wrong-answers-checkbox");
        
        // Progress Elements
        this.progressText = document.getElementById("progress-text");
        this.progressCorrect = document.getElementById("progress-correct");
        this.progressWrong = document.getElementById("progress-wrong");
        this.progressRemaining = document.getElementById("progress-remaining");
        this.progressContainer = document.getElementById("progress-container");

        // Constants
        this.LEVEL_COLORS = {
            1: 'var(--level-1)',
            2: 'var(--level-2)',
            3: 'var(--level-3)',
            4: 'var(--level-4)',
            5: 'var(--level-5)'
        };

        this.ANIMATION_DURATION = 350; // milliseconds

        this.init();
    }

    async init() {
        this.attachEventListeners();
        this.attachKeyboardListeners();
        
        // Try loading session first
        if (!this.loadSession()) {
             await this.fetchAndLoadCards();
        } else {
             console.log("Session restored from local storage.");
             this.updateUI();
        }
    }

    getStorageKey() {
        return this.isPracticeMode ? this.practiceStorageKey : this.learningStorageKey;
    }

    saveSession() {
        const sessionData = {
            cards: this.cards,
            currentCardIndex: this.currentCardIndex,
            undoHistory: this.undoHistory,
            paddingStats: this.sessionStats,
            isPracticeMode: this.isPracticeMode,
            isWrongAnswersMode: this.isWrongAnswersMode,
            timestamp: Date.now()
        };
        localStorage.setItem(this.getStorageKey(), JSON.stringify(sessionData));
        this.updateProgress();
    }

    loadSession() {
        const saved = localStorage.getItem(this.getStorageKey());
        if (!saved) return false;

        try {
            const data = JSON.parse(saved);
            // Optional: Expiry check (e.g. 24 hours)? For now, keep it simple.
            
            this.cards = data.cards || [];
            this.currentCardIndex = data.currentCardIndex || 0;
            this.undoHistory = data.undoHistory || [];
            this.sessionStats = data.paddingStats || { correct: 0, wrong: 0, total: this.cards.length };
            // Mode is determined by checkbox state, not saved data
            this.isWrongAnswersMode = data.isWrongAnswersMode || false;
            
            // Restore UI toggles
            if(this.wrongAnswersCheckbox) this.wrongAnswersCheckbox.checked = this.isWrongAnswersMode;
            
            return true;
        } catch (e) {
            console.error("Failed to load session", e);
            return false;
        }
    }

    clearSession() {
        localStorage.removeItem(this.getStorageKey());
    }
    
    updateProgress() {
         // Calculate for both modes
         const total = this.sessionStats.total; // Use fixed total from session start
         if (total === 0) {
              if (this.progressText) this.progressText.textContent = "0 / 0";
              return;
         }
         
         // Calculate reviewed based on stats
         const reviewed = this.sessionStats.correct + this.sessionStats.wrong;
         const remaining = total - reviewed;
         
         // Update Text
         if (this.progressText) {
             this.progressText.textContent = `${reviewed} / ${total}`;
         }
         
         // Update Bars (percentage based on initial due cards count)
         if (this.progressCorrect) this.progressCorrect.style.width = `${(this.sessionStats.correct / total) * 100}%`;
         if (this.progressWrong) this.progressWrong.style.width = `${(this.sessionStats.wrong / total) * 100}%`;
         if (this.progressRemaining) this.progressRemaining.style.width = `${(remaining / total) * 100}%`;
    }
    
    updateProgressBarVisibility() {
        if (this.progressContainer) {
            this.progressContainer.style.display = 'block';
        }
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
            if (this.areControlsDisabled) return;
            this.undoLastCard();
            this.prevCardBtn.blur();
        });
        this.shuffleBtn?.addEventListener("click", () => {
            if (this.areControlsDisabled) return;
            this.shuffleCards();
            this.shuffleBtn.blur();
        });
        this.restartBtn?.addEventListener("click", () => {
             // Explicit restart clears session and refetches
             this.clearSession();
             this.fetchAndLoadCards();
             this.restartBtn.blur();
        });
        this.practiceModeCheckbox?.addEventListener("change", (e) => this.togglePracticeMode(e.target.checked));
        this.wrongAnswersCheckbox?.addEventListener("change", (e) => this.toggleWrongAnswersMode(e.target.checked));
    }

    attachKeyboardListeners() {
        document.addEventListener('keydown', (event) => {
            // Ignore if user is typing
            if (document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'BUTTON') {
                return;
            }

            if (this.areControlsDisabled) return;

            const isFlipped = this.flashcard.classList.contains("flipped");

            if (event.code === 'Space' && !isFlipped && this.flipBtn.style.display !== 'none') {
                event.preventDefault();
                this.flipCard();
            } else if (isFlipped) {
                if (event.code === 'KeyA') { 
                    event.preventDefault();
                    this.handleFeedback(2);
                } else if (event.code === 'KeyD') { 
                    event.preventDefault();
                    this.handleFeedback(5);
                }
            }
        });
    }

    async fetchAndLoadCards() {
        // Clear old session when fetching new
        this.clearSession();
        
        let url;
        if (this.isPracticeMode) {
            url = `/api/set/${this.setId}/cards`;
            if (this.isWrongAnswersMode) {
                url += '?wrong_only=true'; // Server-side filter for practice mode
            }
        } else {
            url = `/api/set/${this.setId}/due_cards`;
        }

        try {
            const response = await fetch(url);
            const data = await response.json();
            let loadedCards = data.cards || [];
            
            // Client-side filter for learning mode + wrong only
            if (this.isWrongAnswersMode && !this.isPracticeMode) {
                 loadedCards = loadedCards.filter(c => c.level === 1);
            }

            this.cards = loadedCards;
            this.undoHistory = [];
            this.updateBackButtonState();
            this.currentCardIndex = 0;
            
            // IMPORTANT: total represents due cards at session start (learning mode only)
            this.sessionStats = { correct: 0, wrong: 0, total: loadedCards.length };

            // Auto-shuffle removed to respect persisted order
            // if (this.isPracticeMode) {
            //    this.shuffleArray(this.cards);
            // }
            
            // Update progress bar visibility based on mode
            this.updateProgressBarVisibility();

            this.saveSession(); // Initial save
            this.updateUI();

        } catch (error) {
            console.error("Error fetching cards:", error);
            this.showErrorMessage("Failed to load cards");
        }
    }
    
    updateUI() {
        if (this.cards.length > 0 && this.currentCardIndex < this.cards.length) {
             this.loadCard(this.currentCardIndex, true);
        } else if (this.cards.length > 0 && this.currentCardIndex >= this.cards.length) {
             this.showCompletionMessage();
        } else {
             this.showEmptyMessage();
        }
        this.updateProgress();
    }

    showEmptyMessage() {
        this.cardFront.textContent = this.isWrongAnswersMode 
            ? "No wrong cards to review! Great job."
            : (this.isPracticeMode ? "This set is empty." : "No cards due for review!");
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
        this.cardBack.textContent = card.back; // Ensure Back is set
        this.cardLevel.textContent = `Level ${card.level}`;
        this.cardLevel.style.backgroundColor = this.LEVEL_COLORS[card.level] || '#ccc';
        this.cardLevel.style.display = this.isPracticeMode ? 'none' : 'block';
    }

    loadCard(index, isFirstLoad = false) {
        if (index < 0 || index >= this.cards.length) return;

        this.currentCardIndex = index;
        const card = this.cards[this.currentCardIndex];

        // Remove animations
        this.cardContainer.classList.remove('animate-swipe-right', 'animate-swipe-left', 'load-in');

        // Update content regardless of load type (fix for shuffle/undo not updating UI)
        this.updateCardContent(card);

        if (!isFirstLoad) {
            // Trigger reflow for animation
            void this.cardContainer.offsetHeight;
            this.cardContainer.classList.add('load-in');
        }
        
        // Ensure card is physically on front side
        this.flashcard.classList.remove("flipped");

        this.feedbackBtns.style.display = "none";
        this.flipBtn.style.display = "inline-flex";
        
        this.saveSession(); // Persist position
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
        
        // Double-tap prevention is handled by disableControls()

        const animationClass = quality === 5 ? 'animate-swipe-right' : 'animate-swipe-left';
        this.cardContainer.classList.remove('load-in');
        this.cardContainer.classList.add(animationClass);
        this.disableControls();
        
        // Update Stats
        if (quality === 5) this.sessionStats.correct++;
        else this.sessionStats.wrong++;
        this.updateProgress();

        setTimeout(() => {
            const originalCard = { ...this.cards[this.currentCardIndex] };
            this.undoHistory.push({ card: originalCard, quality: quality });
            this.updateBackButtonState();

            // Queue sync based on mode
            if (this.isPracticeMode) {
                // Practice mode: use mark_correct/mark_wrong endpoints
                const endpoint = quality >= 3 ? 'mark_correct' : 'mark_wrong';
                this.queuePracticeSync({
                    cardFront: originalCard.front,
                    endpoint: endpoint,
                    timestamp: Date.now(),
                    retries: 0
                });
            } else {
                // Learning mode: use rate endpoint
                this.queueSync({
                    cardFront: originalCard.front,
                    quality: quality,
                    timestamp: Date.now(),
                    retries: 0
                });
            }

            // Move to next
            if (this.currentCardIndex + 1 < this.cards.length) {
                this.prepareNextCard();
            } else {
                this.currentCardIndex++; // Advance index to indicate completion
                this.saveSession();
                this.showCompletionMessage();
            }

            this.enableControls();
        }, this.ANIMATION_DURATION);
    }

    prepareNextCard() {
        const nextCardIndex = this.currentCardIndex + 1;
        const nextCard = this.cards[nextCardIndex];

        // Silent flip back
        this.flashcard.style.transition = 'none';
        this.flashcard.classList.remove('flipped');
        void this.flashcard.offsetHeight;
        this.flashcard.style.transition = '';

        this.updateCardContent(nextCard);
        this.loadCard(nextCardIndex);
    }

    showCompletionMessage() {
        this.cardContainer.classList.remove('animate-swipe-right', 'animate-swipe-left');
        this.flashcard.classList.remove("flipped");
        this.cardFront.textContent = "All cards reviewed!";
        this.cardBack.textContent = "";
        this.feedbackBtns.style.display = "none";
        this.cardLevel.style.display = "none";
        this.flipBtn.style.display = 'none';
        this.progressText.textContent = "Complete";

        void this.cardContainer.offsetHeight;
        this.cardContainer.classList.add('load-in');
        
        // We do strictly NOT clear session here to allow user to see result
        // User must click Restart to clear.
    }

    async undoLastCard() {
        if (this.undoHistory.length === 0) return;

        const historyItem = this.undoHistory.pop();
        const cardToRestore = historyItem.card;
        const quality = historyItem.quality;
        this.updateBackButtonState();
        
        // Revert stats
        if (quality === 5) {
            this.sessionStats.correct = Math.max(0, this.sessionStats.correct - 1);
        } else {
            this.sessionStats.wrong = Math.max(0, this.sessionStats.wrong - 1);
        }
        this.updateProgress();
        
        // Find index
        const cardIndexInSet = this.cards.findIndex(c => c.front === cardToRestore.front);

        if (cardIndexInSet !== -1) {
            // Restore functionality:
            // 1. Reset card content
            this.cards[cardIndexInSet] = cardToRestore; // Reset local state
            this.loadCard(cardIndexInSet);

            // 2. Cancel Sync
            this.cancelPendingSync(cardToRestore.front);

            // 3. Server Restore (only learning mode)
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
        // Strategy: Shuffle ONLY the remaining cards (from current index onwards)
        // This preserves the history of what was already done.
        
        const reviewed = this.cards.slice(0, this.currentCardIndex);
        const remaining = this.cards.slice(this.currentCardIndex);
        
        if (remaining.length < 2) return; // Nothing to shuffle
        
        const currentCardId = remaining[0].id;
        
        // Group by Level to preserve "Fächer" priority (Leitner system)
        const byLevel = {};
        remaining.forEach(c => {
            const lvl = c.level || 1;
            if (!byLevel[lvl]) byLevel[lvl] = [];
            byLevel[lvl].push(c);
        });

        // Shuffle within each level group and flatten sorted by level
        let newRemaining = [];
        Object.keys(byLevel).sort((a,b) => a - b).forEach(lvl => {
             this.shuffleArray(byLevel[lvl]);
             newRemaining = newRemaining.concat(byLevel[lvl]);
        });
        
        // Ensure new current card is different if possible
        if (newRemaining.length > 1 && newRemaining[0].id === currentCardId) {
             // Find first card that is different (should be index 1 usually, but safer this way)
             const swapIndex = newRemaining.findIndex(c => c.id !== currentCardId);
             if (swapIndex !== -1) {
                 const temp = newRemaining[0];
                 newRemaining[0] = newRemaining[swapIndex];
                 newRemaining[swapIndex] = temp;
             }
        }
        
        this.cards = [...reviewed, ...newRemaining];
        
        // Save new order to server
        const ids = this.cards.map(c => c.id);
        fetch(`/api/set/${this.setId}/shuffle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ card_ids: ids })
        }).catch(err => console.error("Error saving shuffle order:", err));
        
        this.saveSession();
        // Reload current card (which might be new now)
        this.loadCard(this.currentCardIndex);
    }

    async togglePracticeMode(enabled) {
        // Only show popup when ENABLING
        if (enabled) {
            this.showInfoPopup(
                "Practice Mode", 
                "In Practice Mode, you can review all cards freely without affecting your statistics or card levels. Perfect for cramming!",
                // onCancel
                () => {
                    this.practiceModeCheckbox.checked = false;
                },
                // onConfirm
                async () => {
                    this.isPracticeMode = true;
                    this.clearSession();
                    await this.fetchAndLoadCards();
                    // New session -> Shuffle immediately to persist random order
                    this.shuffleCards();
                }
            );
        } else {
            // Disabling (returning to learning mode)
            this.isPracticeMode = false;
            this.clearSession();
            await this.fetchAndLoadCards();
        }
    }
    
    toggleWrongAnswersMode(enabled) {
        // Only show popup when ENABLING
        if (enabled) {
            const message = this.isPracticeMode 
                ? "Showing only cards you answered incorrectly during practice sessions."
                : "Focusing exclusively on cards at Level 1 (new or recently answered incorrectly).";
            
            this.showInfoPopup(
                "Wrong Answers Only", 
                message,
                // onCancel
                () => {
                    this.wrongAnswersCheckbox.checked = false;
                },
                // onConfirm
                () => {
                    this.isWrongAnswersMode = true;
                    this.clearSession();
                    this.fetchAndLoadCards();
                }
            );
        } else {
            // Disabling
            this.isWrongAnswersMode = false;
            this.clearSession();
            this.fetchAndLoadCards();
        }
    }
    
    showInfoPopup(title, message, onCancel = null, onConfirm = null) {
        // Remove existing if any
        const existing = document.getElementById('dynamic-info-popup');
        if (existing) existing.remove();

        const overlay = document.createElement('div');
        overlay.id = 'dynamic-info-popup';
        overlay.className = 'popup-overlay active';
        overlay.style.zIndex = '3000'; // Ensure it's on top

        const content = document.createElement('div');
        content.className = 'popup-content';
        
        // Header
        const header = document.createElement('div');
        header.className = 'popup-header';
        
        const titleEl = document.createElement('h3');
        titleEl.className = 'popup-title';
        titleEl.textContent = title;
        
        const closeBtn = document.createElement('button');
        closeBtn.className = 'popup-close-btn';
        closeBtn.innerHTML = '<span class="material-symbols-outlined">close</span>';
        closeBtn.onclick = () => {
            if (onCancel) onCancel();
            overlay.remove();
        };
        
        header.appendChild(titleEl);
        header.appendChild(closeBtn);
        
        // Body
        const body = document.createElement('div');
        body.className = 'popup-body';
        const p = document.createElement('p');
        p.textContent = message;
        body.appendChild(p);
        
        // Footer
        const footer = document.createElement('div');
        footer.className = 'popup-footer';
        
        // Add Cancel button if onCancel callback is provided
        if (onCancel) {
            const cancelBtn = document.createElement('button');
            cancelBtn.className = 'btn-secondary';
            cancelBtn.textContent = 'Cancel';
            cancelBtn.onclick = () => {
                onCancel();
                overlay.remove();
            };
            footer.appendChild(cancelBtn);
        }
        
        const okBtn = document.createElement('button');
        okBtn.className = 'btn-primary';
        okBtn.textContent = 'Got it';
        okBtn.onclick = () => {
            if (onConfirm) onConfirm();
            overlay.remove();
        };
        
        footer.appendChild(okBtn);
        
        // Assemble
        content.appendChild(header);
        content.appendChild(body);
        content.appendChild(footer);
        overlay.appendChild(content);
        
        document.body.appendChild(overlay);
        
        // Close on outside click (triggers cancel if provided)
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                if (onCancel) onCancel();
                overlay.remove();
            }
        });
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
        this.updateBackButtonState();
        if (this.shuffleBtn) this.shuffleBtn.disabled = false;
        if (this.practiceModeCheckbox) this.practiceModeCheckbox.disabled = false;
    }

    queueSync(syncItem) {
        this.syncQueue.push(syncItem);
        this.processSyncQueue();
    }

    async processSyncQueue() {
        if (this.isSyncProcessing || this.syncQueue.length === 0) return;

        this.isSyncProcessing = true;

        while (this.syncQueue.length > 0) {
            const syncItem = this.syncQueue[0];

            try {
                await fetch(`/api/set/${this.setId}/rate`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        card_front: syncItem.cardFront,
                        quality: syncItem.quality
                    })
                });

                this.syncQueue.shift();
            } catch (error) {
                console.error("Error syncing card:", error);

                syncItem.retries++;
                if (syncItem.retries >= 3) {
                    console.error(`Failed to sync card after 3 retries:`, syncItem.cardFront);
                    this.syncQueue.shift(); 
                } else {
                    const delay = Math.pow(2, syncItem.retries - 1) * 1000;
                    await new Promise(resolve => setTimeout(resolve, delay));
                }
            }
        }

        this.isSyncProcessing = false;
    }

    queuePracticeSync(syncItem) {
        this.syncQueue.push(syncItem);
        this.processPracticeSyncQueue();
    }

    async processPracticeSyncQueue() {
        if (this.isSyncProcessing || this.syncQueue.length === 0) return;

        this.isSyncProcessing = true;

        while (this.syncQueue.length > 0) {
            const syncItem = this.syncQueue[0];

            try {
                await fetch(`/api/set/${this.setId}/${syncItem.endpoint}`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        card_front: syncItem.cardFront
                    })
                });

                this.syncQueue.shift();
            } catch (error) {
                console.error("Error syncing practice card:", error);

                syncItem.retries++;
                if (syncItem.retries >= 3) {
                    console.error(`Failed to sync practice card after 3 retries:`, syncItem.cardFront);
                    this.syncQueue.shift(); 
                } else {
                    const delay = Math.pow(2, syncItem.retries - 1) * 1000;
                    await new Promise(resolve => setTimeout(resolve, delay));
                }
            }
        }

        this.isSyncProcessing = false;
    }

    cancelPendingSync(cardFront) {
        this.syncQueue = this.syncQueue.filter(item => item.cardFront !== cardFront);
    }
}

