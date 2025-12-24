document.addEventListener('DOMContentLoaded', () => {
    // Open Popup
    window.openPopup = function (popupId) {
        const popup = document.getElementById(popupId);
        if (popup) {
            popup.classList.add('active');
            document.body.style.overflow = 'hidden'; // Prevent background scrolling
        }
    };

    // Close Popup
    window.closePopup = function (popupId) {
        const popup = document.getElementById(popupId);
        if (popup) {
            popup.classList.remove('active');
            document.body.style.overflow = ''; // Restore background scrolling
        }
    };

    // Close on Outside Click
    document.querySelectorAll('.popup-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                // Check if popup is static
                if (overlay.dataset.static === "true") {
                    // Optional: Visual cue (shake?) that it can't be closed this way
                    const content = overlay.querySelector('.popup-content');
                    content.style.transform = 'scale(1.02)';
                    setTimeout(() => content.style.transform = 'scale(1)', 150);
                    return;
                }
                overlay.classList.remove('active');
                document.body.style.overflow = '';
            }
        });
    });

    // Close on Escape Key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const activePopup = document.querySelector('.popup-overlay.active');
            if (activePopup) {
                // Check if popup is static
                if (activePopup.dataset.static === "true") return;

                activePopup.classList.remove('active');
                document.body.style.overflow = '';
            }
        }
    });
});
