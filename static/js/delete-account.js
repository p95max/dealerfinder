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

document.querySelector('[data-bs-toggle="collapse"]').addEventListener('shown.bs.collapse', e => {
    e.target.querySelector('span').textContent = '▾';
});
document.querySelector('[data-bs-toggle="collapse"]').addEventListener('hidden.bs.collapse', e => {
    e.target.querySelector('span').textContent = '▸';
});