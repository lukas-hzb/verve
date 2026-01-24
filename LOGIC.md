# Algorithm Documentation

This document provides detailed explanations of all algorithms and logic systems used in the Verve vocabulary learning application.

---

## Table of Contents

1. [SM2 Spaced Repetition Algorithm](#sm2-spaced-repetition-algorithm)
2. [Progress Bar Tracking Logic](#progress-bar-tracking-logic)
3. [Study Session Mechanics](#study-session-mechanics)
4. [Practice Mode vs Learning Mode](#practice-mode-vs-learning-mode)
5. [Wrong Answers Filtering](#wrong-answers-filtering)
6. [Session Persistence](#session-persistence)

---

## SM2 Spaced Repetition Algorithm

The SM2 (SuperMemo 2) algorithm is the core of our learning system. It determines when a card should be reviewed based on user performance and card history.

### Core Concept

Cards advance through levels based on how well you know them. Each level has an increasing review interval, optimizing long-term retention.

### Implementation Details

**File**: `app/services/sm2_algorithm.py`

#### Input Parameters

- **quality** (0-5): User's self-reported knowledge
  - `0`: Complete blackout
  - `1`: Incorrect response; correct answer remembered
  - `2`: Incorrect response; correct answer seemed easy to recall
  - `3`: Correct response recalled with serious difficulty
  - `4`: Correct response after some hesitation
  - `5`: Perfect response
  
- **level**: Current repetition level (1-based, starts at 1)
- **last_interval**: Days since last review
- **ease_factor**: Personalized difficulty multiplier (default: 2.5)

#### Algorithm Logic

```
IF quality >= 3 (correct answer):
    IF level == 1:
        interval = 1 day
    ELSE IF level == 2:
        interval = 6 days
    ELSE:
        interval = round(last_interval × ease_factor)
    
    ease_factor += (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
    ease_factor = max(ease_factor, 1.3)  # minimum threshold
    
    level += 1

ELSE (incorrect answer, quality < 3):
    level = 1
    interval = 1 day
    ease_factor unchanged
```

#### Output

Returns a tuple: `(new_level, interval_days, ease_factor)`

#### Example Progression

| Review | Quality | Level | Interval |
|--------|---------|-------|----------|
| 1st    | 5       | 1→2   | 1 day    |
| 2nd    | 5       | 2→3   | 6 days   |
| 3rd    | 4       | 3→4   | ~15 days |
| 4th    | 5       | 4→5   | ~37 days |
| ...    | 2       | 5→1   | 1 day    |

### Database Integration

**File**: `app/models/card.py`

Each card stores:
- `level`: Current repetition level
- `next_review`: Timestamp when card becomes due
- `last_practice_wrong`: Practice mode tracking (doesn't affect SM2)

The `is_due()` method checks if `next_review <= current_time`.

---

## Progress Bar Tracking Logic

The progress bar visualizes learning progress during a study session.

### Design Requirements

**Location**: Positioned directly above the flashcard with matching width

**Display**: Three-segment bar showing:
- **Green** (`var(--color-accent-4)`): Correctly answered cards
- **Red** (`var(--color-accent-1)`): Incorrectly answered cards  
- **Gray** (transparent): Remaining cards

### Tracking Logic

#### Learning Mode (Normal Mode)

The progress bar tracks **only cards that were due today** at session start:

```
Initial State:
- Fetch due_cards = cards where next_review <= today
- total_due = count(due_cards)
- correct_count = 0
- wrong_count = 0
- remaining = total_due

On Each Answer:
- IF quality >= 3: correct_count++
- ELSE: wrong_count++
- remaining = total_due - (correct_count + wrong_count)

Progress Calculation:
- correct_percentage = (correct_count / total_due) × 100%
- wrong_percentage = (wrong_count / total_due) × 100%
- remaining_percentage = (remaining / total_due) × 100%
```

**Key Point**: The denominator is always `total_due` (cards due today), not the total number of cards in the set.

#### Practice Mode

**Progress bar is DISABLED** in practice mode because:
- Practice mode doesn't affect card statistics
- Users can review ALL cards, not just due cards
- The concept of "progress" doesn't apply to casual practice

```
IF isPracticeMode:
    Hide progress bar
ELSE:
    Show progress bar with due cards tracking
```

### Implementation Details

**Files**: 
- Frontend: `static/js/modules/flashcard.js`
- Template: `templates/set.html`

The progress bar state is saved in `sessionStats`:
```javascript
sessionStats: {
    correct: 0,
    wrong: 0,
    total: initial_due_cards_count
}
```

**IMPORTANT**: `sessionStats.total` is set once at session start and represents the count of due cards at that moment, NOT all cards in the set.

### Visual Behavior

- Segments animate smoothly with CSS transitions (0.3s)
- Width is calculated dynamically based on current counts
- Text displays: "X / Y" where X = reviewed, Y = total due

---

## Study Session Mechanics

### Card Fetching

**Learning Mode**:
- Endpoint: `GET /api/set/<set_id>/due_cards`
- Returns: Cards where `is_due() == True`
- Order: Database order (not shuffled)

**Practice Mode**:
- Endpoint: `GET /api/set/<set_id>/cards`
- Returns: ALL cards in the set
- Automatically shuffled on fetch

### Answer Processing

**Learning Mode**:
```
User rates card with quality 0-5
↓
Frontend calls POST /api/set/<set_id>/rate
  { card_front, quality }
↓
Backend: VocabService.update_card_performance()
  - Calls SM2 algorithm
  - Updates card.level and card.next_review
  - Commits to database
↓
Card removed from session (already processed)
```

**Practice Mode**:
```
User rates card (correct/incorrect)
↓
Frontend calls:
  - POST /api/set/<set_id>/mark_correct, OR
  - POST /api/set/<set_id>/mark_wrong
  { card_front }
↓
Backend: VocabService.mark_practice_correct/wrong()
  - Updates ONLY card.last_practice_wrong flag
  - Does NOT modify card.level or next_review
  - Commits to database
↓
Card removed from session
```

### Undo Functionality

When user clicks "Undo":
```
1. Pop last card from undoHistory[]
2. Decrement currentCardIndex
3. Restore card to current position
4. Revert sessionStats (correct-- or wrong--)
5. Cancel any pending API sync for that card
6. Re-display the card
```

**Limitation**: Cannot undo past session boundaries (after restart/reload).

---

## Practice Mode vs Learning Mode

| Aspect | Learning Mode | Practice Mode |
|--------|---------------|---------------|
| **Cards Shown** | Only due cards | All cards |
| **Order** | Database order | Shuffled |
| **Affects SM2** | ✅ Yes | ❌ No |
| **Updates `level`** | ✅ Yes | ❌ No |
| **Updates `next_review`** | ✅ Yes | ❌ No |
| **Tracks `last_practice_wrong`** | ❌ No | ✅ Yes |
| **Progress Bar** | ✅ Enabled | ❌ Disabled |
| **Use Case** | Long-term retention | Quick review/cramming |

### Mode Toggle Behavior

When enabling Practice Mode:
- Show popup: "In Practice Mode, you can review all cards freely..."
- Fetch all cards via `/api/set/<set_id>/cards`
- Shuffle cards
- Hide progress bar

When disabling Practice Mode:
- **NO popup shown** (user feedback)
- Fetch due cards via `/api/set/<set_id>/due_cards`
- Keep database order
- Show progress bar

---

## Wrong Answers Filtering

The "Wrong Only" toggle filters cards to show only those the user struggles with.

### Filter Logic

#### Learning Mode + Wrong Only

```
Fetch: GET /api/set/<set_id>/due_cards
Filter client-side: cards.filter(c => c.level === 1)
```

**Rationale**: `level === 1` means the card is either:
- Brand new, OR
- Recently answered incorrectly (SM2 reset it to level 1)

#### Practice Mode + Wrong Only

```
Fetch: GET /api/set/<set_id>/cards?wrong_only=true
Filter server-side: cards WHERE last_practice_wrong = TRUE
```

**Rationale**: `last_practice_wrong` tracks cards answered incorrectly specifically during practice sessions, independent of SM2 levels.

### Mode Interactions

| Learning Mode | Practice Mode | Wrong Only | Result |
|---------------|---------------|------------|--------|
| ✅ | ❌ | ❌ | Due cards |
| ✅ | ❌ | ✅ | Due cards at level 1 |
| ❌ | ✅ | ❌ | All cards (shuffled) |
| ❌ | ✅ | ✅ | Cards marked wrong in practice |

### Database Schema

**New Column**: `card.last_practice_wrong` (boolean, default: false)

- Updated via `/api/set/<set_id>/mark_wrong` → `TRUE`
- Updated via `/api/set/<set_id>/mark_correct` → `FALSE`
- Never automatically reset (persists across sessions)

**Migration**: `scripts/add_practice_tracking.py`

---

## Session Persistence

Study sessions are saved to `localStorage` to survive page reloads.

### Saved State

```javascript
{
    cards: Card[],              // Full card array in current order
    currentCardIndex: number,   // Position in session
    undoHistory: Card[],        // Stack of previous cards
    sessionStats: {             // Progress tracking
        correct: number,
        wrong: number,
        total: number
    },
    isPracticeMode: boolean,    // Current mode
    isWrongAnswersMode: boolean, // Current filter
    timestamp: number           // When saved
}
```

### Load Behavior

On page load:
```
IF localStorage has session data:
    Restore cards, index, stats, modes
    Resume exactly where left off
ELSE:
    Fetch fresh cards from API
    Initialize new session
```

### Clearing Sessions

Sessions are cleared when:
- User clicks "Restart"
- User toggles Practice Mode or Wrong Only
- User explicitly starts a new session

**NOT cleared on**:
- Page reload
- Browser back/forward navigation
- Completing a session (preserved for potential resume)

---

## Future Enhancements

Potential algorithmic improvements:

1. **Adaptive Ease Factor**: Persist `ease_factor` per card for personalized intervals
2. **Lapse Tracking**: Count how many times a card was reset to level 1
3. **Time-of-Day Learning**: Track performance by time of day
4. **Batch Review Optimization**: Group cards by similarity for efficient review
5. **Forgetting Curve Integration**: Adjust intervals based on forgetting probability

---

*Last Updated: 2026-01-24*
