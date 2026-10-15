/**
 * Flashcard Module
 * Handles flashcard learning functionality including persistence, shuffle, and progress
 */

import { renderCardContent } from './card-text.js';

export class FlashcardManager {
    constructor(setId) {
        this.setId = setId;
        
        // Session
        this.cards = [];
        this.currentCardIndex = 0;
        this.sessionStats = { correct: 0, wrong: 0, total: 0 };
        this.undoHistory = [];
        
        // Mode
        this.studyMode = document.querySelector('.study-page')?.dataset.studyMode || 'learn';
        this.isPracticeMode = this.studyMode !== 'learn';
        this.isWrongAnswersMode = this.studyMode === 'mistakes';
        
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
        this.cardLevels = [this.cardLevel, document.getElementById("card-level-back")].filter(Boolean);
        this.flipBtn = document.getElementById("flip-btn");
        this.feedbackBtns = document.getElementById("feedback-btns");
        this.knownBtn = document.getElementById("known-btn");
        this.notKnownBtn = document.getElementById("not-known-btn");
        this.prevCardBtn = document.getElementById("back-btn");
        this.shuffleBtn = document.getElementById("shuffle-btn");
        this.restartBtn = document.getElementById("restart-btn");
        this.completion = document.getElementById('study-completion');
        this.emptyAction = document.getElementById('study-empty-action');
        this.completionText = document.getElementById('study-completion-text');
        this.continuePracticeBtn = document.getElementById('continue-practice-btn');
        this.continuePracticeLabel = document.getElementById('continue-practice-label');
        
        // Progress Elements
        this.progressText = document.getElementById("progress-text");
        this.progressCorrect = document.getElementById("progress-correct");
        this.progressWrong = document.getElementById("progress-wrong");
        this.progressRemaining = document.getElementById("progress-remaining");
        this.progressContainer = document.getElementById("progress-container");
        this.progressTrack = document.getElementById('round-progress');
        this.roundLabel = document.getElementById('round-label');
        this.mascot = document.querySelector('[data-study-mascot]');
        this.mascotReacting = false;
        this.mascotNextPose = null;
        this.mascot?.addEventListener('animationend', (event) => {
            if (event.target === this.mascot && event.animationName === 'mascot-cheer')
                this.finishMascotReaction();
        });

        // Constants
        this.LEVEL_COLORS = {
            1: 'var(--level-1)',
            2: 'var(--level-2)',
            3: 'var(--level-3)',
            4: 'var(--level-4)',
            5: 'var(--level-5)'
        };

        this.ANIMATION_DURATION = 250; // Matches the outgoing card animation.

        this.updateModeUI();

        this.init();
    }

    async init() {
        this.attachEventListeners();
        this.attachKeyboardListeners();
        this.disableControls();
        try {
        
        // Try loading session first
        if (!this.loadSession()) {
             await this.fetchAndLoadCards();
        } else {
             console.log("Session restored from local storage.");
             this.updateBackButtonState();
             this.updateUI();
        }
        } finally {
            this.enableControls();
        }
    }

    getStorageKey() {
        const mode = this.isPracticeMode ? this.practiceStorageKey : this.learningStorageKey;
        return `${mode}_${this.isWrongAnswersMode ? 'MISTAKES' : 'ALL'}`;
    }

    updateModeUI() {
        this.cardContainer.classList.toggle('wrong-mode-active', this.isWrongAnswersMode);
        if (this.roundLabel) this.roundLabel.textContent = this.isPracticeMode ? 'Practice Progress' : 'Round Progress';
    }

    setMascotPose(pose, react = false) {
        if (!this.mascot) return;

        // Preserve the running motion; apply the latest resting pose afterward.
        if (this.mascot.classList.contains('mascot-reacting')) {
            this.mascotNextPose = react ? 'peek' : pose;
            return;
        }

        this.mascot.dataset.pose = pose;

        if (react && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            this.mascotReacting = true;
            this.mascot.classList.add('mascot-reacting');
        }
    }

    finishMascotReaction() {
        this.mascotReacting = false;
        this.mascot.classList.remove('mascot-reacting');
        this.mascot.dataset.pose = this.mascotNextPose || 'peek';
        this.mascotNextPose = null;
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
        const legacyKey = this.isPracticeMode ? this.practiceStorageKey : this.learningStorageKey;
        const currentSaved = localStorage.getItem(this.getStorageKey());
        if (!currentSaved && this.isWrongAnswersMode) return false; // Do not restore the old Level 1 filter.
        const saved = currentSaved || localStorage.getItem(legacyKey);
        if (!saved) return false;

        try {
            const data = JSON.parse(saved);
            if (Boolean(data.isWrongAnswersMode) !== this.isWrongAnswersMode) return false;
            // Optional: Expiry check (e.g. 24 hours)? For now, keep it simple.
            
            this.cards = data.cards || [];
            this.currentCardIndex = data.currentCardIndex || 0;
            this.undoHistory = data.undoHistory || [];
            this.sessionStats = data.paddingStats || { correct: 0, wrong: 0, total: this.cards.length };
            // Mode is determined by checkbox state, not saved data
            this.updateModeUI();
            
            return true;
        } catch (e) {
            console.error("Failed to load session", e);
            return false;
        }
    }

    clearSession() {
        localStorage.removeItem(this.getStorageKey());
        // A completed migration must not resurrect an old round on Restart.
        const legacyKey = this.isPracticeMode ? this.practiceStorageKey : this.learningStorageKey;
        localStorage.removeItem(legacyKey);
    }
    
    updateProgress() {
         // Calculate for both modes
         const total = this.sessionStats.total; // Use fixed total from session start
         
         // Calculate reviewed based on stats
         const reviewed = this.sessionStats.correct + this.sessionStats.wrong;
         const remaining = Math.max(0, total - reviewed);
         
         // Update Text
         if (this.progressText) {
             this.progressText.textContent = total > 0 && remaining === 0
                 ? `${reviewed} / ${total} · Complete`
                 : `${reviewed} / ${total}`;
         }
         
         // Update Bars (percentage based on initial due cards count)
         if (this.progressCorrect) this.progressCorrect.style.width = `${total ? (this.sessionStats.correct / total) * 100 : 0}%`;
         if (this.progressWrong) this.progressWrong.style.width = `${total ? (this.sessionStats.wrong / total) * 100 : 0}%`;
         if (this.progressRemaining) this.progressRemaining.style.width = `${total ? (remaining / total) * 100 : 100}%`;
         this.progressTrack?.setAttribute('aria-valuemax', total);
         this.progressTrack?.setAttribute('aria-valuenow', reviewed);
         this.progressTrack?.setAttribute('aria-valuetext', `${reviewed} of ${total} answered; ${this.sessionStats.correct} knew it, ${this.sessionStats.wrong} didn't know, ${remaining} remaining`);
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
        this.restartBtn?.addEventListener("click", async () => {
             await this.restartRound();
             this.restartBtn.blur();
        });
        this.continuePracticeBtn?.addEventListener('click', async () => {
            if (this.areControlsDisabled) return;
            if (this.isWrongAnswersMode && this.sessionStats.wrong === 0) {
                await this.processSyncQueue();
                window.location.assign(`/set/${this.setId}?mode=practice`);
                return;
            }
            await this.restartRound();
        });
    }

    async restartRound() {
        if (this.areControlsDisabled) return;
        this.disableControls();
        this.showLoading();
        try {
            // The mistakes query must see the final answers from this round.
            await this.processSyncQueue();
            await this.fetchAndLoadCards();
        } finally { this.enableControls(); }
    }

    updateCompletionAction(visible = false) {
        if (this.emptyAction) this.emptyAction.hidden = true;
        if (!this.completion) return;
        this.completion.hidden = !visible || !this.isPracticeMode;
        if (this.completion.hidden) return;
        this.completionText.textContent = '';
        this.completionText.hidden = true;
        if (!this.isWrongAnswersMode) {
            this.continuePracticeLabel.textContent = 'Practice Again';
        } else if (this.sessionStats.wrong > 0) {
            this.continuePracticeLabel.textContent = 'Review Remaining Mistakes';
        } else {
            this.continuePracticeLabel.textContent = 'Practice All Cards';
        }
        const icon = this.continuePracticeBtn?.querySelector('.material-symbols-rounded');
        if (icon) icon.textContent = this.isWrongAnswersMode && this.sessionStats.wrong === 0 ? 'stacks' : 'refresh';
    }

    attachKeyboardListeners() {
        document.addEventListener('keydown', (event) => {
            if (document.querySelector('dialog[open], [popover]:popover-open')) return;
            // Keep typing and modified shortcuts native, but let study shortcuts
            // take priority over a button left focused by a previous click.
            const activeElement = document.activeElement;
            if (activeElement?.matches('input, textarea, select') || activeElement?.isContentEditable) return;
            if (event.altKey || event.ctrlKey || event.metaKey) return;

            // Cancel native Space activation even on the answer side or while
            // controls are busy, so it cannot re-click the focused button.
            if (event.code === 'Space') {
                event.preventDefault();
                // Space is a card shortcut here, not keyboard interaction with
                // the previously clicked button. Release that stale focus so
                // the browser does not reveal its focus-visible outline.
                if (activeElement?.matches('button, [role="button"]')) activeElement.blur();
            }
            if (event.repeat) return;

            if (this.areControlsDisabled) return;

            const isFlipped = this.flashcard.classList.contains("flipped");

            if (event.code === 'Space' && !isFlipped && this.flipBtn.style.display !== 'none') {
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
        if (this.isPracticeMode || this.isWrongAnswersMode) {
            url = `/api/set/${this.setId}/cards`;
            if (this.isWrongAnswersMode) {
                url += '?last_wrong_only=true'; // Only cards whose last answer was incorrect.
            }
        } else {
            url = `/api/set/${this.setId}/due_cards`;
        }

        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error('Could not load cards');
            const data = await response.json();
            let loadedCards = data.cards || [];
            
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
        this.updateCompletionAction();
        if (this.emptyAction) this.emptyAction.hidden = !this.isWrongAnswersMode;
        this.setMascotPose(this.isPracticeMode ? 'peek' : 'celebrate');
        this.cardFront.textContent = this.isWrongAnswersMode 
            ? "No Previous Mistakes to Review."
            : (this.isPracticeMode ? "This Set Is Empty." : "No Cards Due for Review!");
        this.cardBack.textContent = "";
        this.flipBtn.style.display = "none";
        this.feedbackBtns.style.display = "none";
        this.cardLevels.forEach(level => { level.style.display = "none"; });
    }

    showLoading() {
        this.updateCompletionAction();
        this.cardFront.textContent = "Loading...";
        this.cardBack.textContent = "";
        this.frameRequest = requestAnimationFrame(() => {
            this.cardContainer.classList.remove('animate-swipe-right', 'animate-swipe-left', 'load-in');
            this.flashcard.classList.remove("flipped");
        });
        this.flipBtn.style.display = "none";
        this.feedbackBtns.style.display = "none";
        this.cardLevels.forEach(level => { level.style.display = "none"; });
    }

    showErrorMessage(message) {
        this.updateCompletionAction();
        this.cardFront.textContent = message;
        this.cardBack.textContent = "";
        this.flipBtn.style.display = "none";
        this.feedbackBtns.style.display = "none";
        this.cardLevels.forEach(level => { level.style.display = "none"; });
    }

    updateCardContent(card) {
        this.updateCompletionAction();
        renderCardContent(this.cardFront, card.front);
        renderCardContent(this.cardBack, card.back);
        const displayLevel = Math.max(1, Math.min(card.level, 5));
        this.cardLevels.forEach(level => {
            level.textContent = `Level ${displayLevel}`;
            level.style.backgroundColor = this.LEVEL_COLORS[displayLevel];
            level.style.color = displayLevel === 3 ? 'var(--color-text-on-yellow)' : 'white';
            level.style.display = 'block';
        });
    }

    loadCard(index, isFirstLoad = false) {
        if (index < 0 || index >= this.cards.length) return;

        if (!this.mascotReacting) this.setMascotPose('peek');

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
            this.setMascotPose('peek', true);
            this.flashcard.classList.add("flipped");
            this.flipBtn.style.display = "none";
            this.feedbackBtns.style.display = "flex";
        }
    }

    async handleFeedback(quality) {
        if (this.areControlsDisabled) return;

        this.setMascotPose(quality === 5 ? 'celebrate' : 'peek', true);
        
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
        this.setMascotPose('celebrate');
        this.cardContainer.classList.remove('animate-swipe-right', 'animate-swipe-left');
        this.flashcard.classList.remove("flipped");
        this.cardFront.textContent = "All Cards Reviewed!";
        this.updateCompletionAction(true);
        this.cardBack.textContent = "";
        this.feedbackBtns.style.display = "none";
        this.cardLevels.forEach(level => { level.style.display = "none"; });
        this.flipBtn.style.display = 'none';
        this.updateProgress();

        void this.cardContainer.offsetHeight;
        this.cardContainer.classList.add('load-in');
        
        // We do strictly NOT clear session here to allow user to see result
        // User must click Restart to clear.
    }

    async undoLastCard() {
        if (this.undoHistory.length === 0) return;
        this.disableControls();
        try {

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

            // Let in-flight feedback finish before restoring its original state.
            await this.processSyncQueue();
            if (!this.isPracticeMode) {
                try {
                    await fetch("/api/restore_card", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            set_id: this.setId,
                            card_front: cardToRestore.front,
                            level: cardToRestore.level,
                            next_review: cardToRestore.next_review,
                            last_answer_wrong: cardToRestore.last_answer_wrong ?? cardToRestore.last_practice_wrong ?? false
                        })
                    });
                } catch (error) {
                    console.error("Error restoring card:", error);
                }
            } else {
                const wasWrong = cardToRestore.last_answer_wrong ?? cardToRestore.last_practice_wrong ?? false;
                this.queuePracticeSync({cardFront: cardToRestore.front, endpoint: wasWrong ? 'mark_wrong' : 'mark_correct', retries: 0});
            }
        }
        } finally {
            this.enableControls();
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
        if (!this.isPracticeMode) fetch(`/api/set/${this.setId}/shuffle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ card_ids: ids })
        }).catch(err => console.error("Error saving shuffle order:", err));
        
        this.saveSession();
        // Reload current card (which might be new now)
        this.loadCard(this.currentCardIndex);
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
        if (this.restartBtn) this.restartBtn.disabled = true;
        if (this.continuePracticeBtn) this.continuePracticeBtn.disabled = true;
    }

    enableControls() {
        this.areControlsDisabled = false;
        if (this.flipBtn) this.flipBtn.disabled = false;
        if (this.knownBtn) this.knownBtn.disabled = false;
        if (this.notKnownBtn) this.notKnownBtn.disabled = false;
        this.updateBackButtonState();
        if (this.shuffleBtn) this.shuffleBtn.disabled = false;
        if (this.restartBtn) this.restartBtn.disabled = false;
        if (this.continuePracticeBtn) this.continuePracticeBtn.disabled = false;
    }

    queueSync(syncItem) {
        this.syncQueue.push(syncItem);
        this.processSyncQueue();
    }

    processSyncQueue() {
        if (this.syncPromise) return this.syncPromise;
        this.syncPromise = this.flushSyncQueue().finally(() => { this.syncPromise = null; });
        return this.syncPromise;
    }

    async flushSyncQueue() {
        while (this.syncQueue.length > 0) {
            const syncItem = this.syncQueue[0];
            const endpoint = syncItem.endpoint || 'rate';
            try {
                const response = await fetch(`/api/set/${this.setId}/${endpoint}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        card_front: syncItem.cardFront,
                        ...(endpoint === 'rate' ? { quality: syncItem.quality } : {})
                    })
                });
                if (!response.ok) throw new Error('Could not save the answer');
                // Undo may have canceled this item while the request was running.
                if (this.syncQueue[0] === syncItem) this.syncQueue.shift();
            } catch (error) {
                syncItem.retries++;
                if (syncItem.retries >= 3) {
                    console.error('Failed to save answer:', error);
                    if (this.syncQueue[0] === syncItem) this.syncQueue.shift();
                } else {
                    await new Promise(resolve => setTimeout(resolve, 1000 * syncItem.retries));
                }
            }
        }
    }

    queuePracticeSync(syncItem) {
        this.queueSync(syncItem);
    }

    cancelPendingSync(cardFront) {
        this.syncQueue = this.syncQueue.filter(item => item.cardFront !== cardFront);
    }
}
