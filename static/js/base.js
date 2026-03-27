function toggleTurnstileButtonState(isEnabled) {
    document.querySelectorAll(".cf-turnstile").forEach((widget) => {
        const btnId = widget.dataset.buttonId;
        if (!btnId) {
            return;
        }

        const button = document.getElementById(btnId);
        if (!button) {
            return;
        }

        button.disabled = !isEnabled;
    });
}

function onTurnstileSuccess() {
    toggleTurnstileButtonState(true);
}

function onTurnstileExpired() {
    toggleTurnstileButtonState(false);
}

function onTurnstileError() {
    toggleTurnstileButtonState(false);
}

document.addEventListener("DOMContentLoaded", () => {
    const textarea = document.querySelector("textarea[name='message']");
    const counter = document.getElementById("messageCounter");

    if (!textarea || !counter) return;

    const updateCounter = () => {
        counter.textContent = textarea.value.length;
    };

    textarea.addEventListener("input", updateCounter);
    updateCounter();
});