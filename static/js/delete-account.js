function setDeleteButtonState(isEnabled) {
    const button = document.getElementById("deleteBtn");
    if (button) {
        button.disabled = !isEnabled;
    }
}

function onDeleteTurnstileSuccess() {
    setDeleteButtonState(true);
}

function onDeleteTurnstileExpired() {
    setDeleteButtonState(false);
}

function onDeleteTurnstileError() {
    setDeleteButtonState(false);
}