/** Hover greetings queue at rest; touch taps during a greeting are ignored. */
export function initializeWelcomeMascot() {
    const mascot = document.querySelector('[data-welcome-mascot]');
    if (!mascot) return;
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const image = mascot.querySelector('.mascot-image');
    if (!image) return;
    let pendingGreetings = 0;

    const greet = (queueIfBusy = true) => {
        if (reducedMotion.matches) return;
        if (mascot.classList.contains('mascot-reacting')) {
            if (queueIfBusy) pendingGreetings++;
            return;
        }
        mascot.classList.add('mascot-reacting');
    };

    mascot.addEventListener('pointerenter', (event) => {
        if (event.pointerType === 'mouse' || event.pointerType === 'pen') greet();
    });
    mascot.addEventListener('pointerup', (event) => {
        if (event.pointerType === 'touch') greet(false);
    });
    image.addEventListener('animationiteration', (event) => {
        if (event.target !== image || event.animationName !== 'mascot-greet') return;
        if (pendingGreetings > 0) {
            pendingGreetings--;
        } else {
            mascot.classList.remove('mascot-reacting');
        }
    });
}
