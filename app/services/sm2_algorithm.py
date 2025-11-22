"""
SM2 (SuperMemo 2) Spaced Repetition Algorithm.

This module implements the SM2 algorithm for calculating optimal
review intervals based on user performance.

Reference: https://www.supermemo.com/en/archives1990-2015/english/ol/sm2
"""

from typing import Tuple


def calculate_next_review(
    quality: int,
    level: int,
    last_interval: int = 1,
    ease_factor: float = 2.5
) -> Tuple[int, int, float]:
    """
    Calculate the next review parameters using the SM2 algorithm.
    
    The SM2 algorithm determines when a card should be reviewed next based
    on how well the user knew the answer (quality) and the card's review history.
    
    Args:
        quality: User's self-reported knowledge (0-5)
                 0: Complete blackout
                 1: Incorrect response; correct one remembered
                 2: Incorrect response; correct one seemed easy to recall
                 3: Correct response recalled with serious difficulty
                 4: Correct response after some hesitation
                 5: Perfect response
        level: Current repetition level of the card (1-based)
        last_interval: Days since last review (default: 1)
        ease_factor: Easiness factor for the card (default: 2.5)
    
    Returns:
        Tuple containing:
        - new_level: Updated repetition level
        - interval: Days until next review
        - ease_factor: Updated easiness factor
    
    Examples:
        >>> calculate_next_review(5, 1)  # Perfect recall, first review
        (2, 1, 2.6)
        
        >>> calculate_next_review(2, 3, 10, 2.5)  # Poor recall
        (1, 1, 2.18)
    """
    # Quality score of 3 or higher means the user knew the answer
    if quality >= 3:
        # Calculate next interval based on level
        if level == 1:
            interval = 1  # First successful review: 1 day
        elif level == 2:
            interval = 6  # Second successful review: 6 days
        else:
            # Subsequent reviews: multiply by ease factor
            interval = round(last_interval * ease_factor)
        
        # Update ease factor based on quality
        # Quality 5 increases EF, quality 3 decreases it slightly
        ease_factor += (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        
        # Ensure ease factor doesn't drop below minimum threshold
        if ease_factor < 1.3:
            ease_factor = 1.3
        
        # Advance to next level
        level += 1
    else:
        # Quality score below 3: reset to level 1
        level = 1
        interval = 1
        # Note: ease_factor is not updated on failure in this implementation
    
    return level, interval, ease_factor


def get_initial_interval_for_level(level: int) -> int:
    """
    Get the default interval for a given level.
    
    This is used when the exact last interval is not known.
    
    Args:
        level: The repetition level
        
    Returns:
        The default interval in days for that level
    """
    if level <= 1:
        return 1
    elif level == 2:
        return 6
    else:
        return 10
