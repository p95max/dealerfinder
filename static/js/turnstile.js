function toggleTurnstileButton(buttonId, isEnabled) {
    const button = document.getElementById(buttonId);
    if (button) {
        button.disabled = !isEnabled;
    }
}

function onLoginTurnstileSuccess() {
    toggleTurnstileButton("loginBtn", true);
}

function onLoginTurnstileExpired() {
    toggleTurnstileButton("loginBtn", false);
}

function onLoginTurnstileError() {
    toggleTurnstileButton("loginBtn", false);
}

function onDeleteTurnstileSuccess() {
    toggleTurnstileButton("deleteBtn", true);
}

function onDeleteTurnstileExpired() {
    toggleTurnstileButton("deleteBtn", false);
}

function onDeleteTurnstileError() {
    toggleTurnstileButton("deleteBtn", false);
}