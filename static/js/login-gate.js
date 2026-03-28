function setLoginButtonState(isEnabled) {
    const button = document.getElementById("loginBtn");
    if (button) {
        button.disabled = !isEnabled;
    }
}

function onLoginTurnstileSuccess() {
    setLoginButtonState(true);
}

function onLoginTurnstileExpired() {
    setLoginButtonState(false);
}

function onLoginTurnstileError() {
    setLoginButtonState(false);
}