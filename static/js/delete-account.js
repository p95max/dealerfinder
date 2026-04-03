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

const collapseToggle = document.querySelector('[data-bs-toggle="collapse"]');

if (collapseToggle) {
    collapseToggle.addEventListener("shown.bs.collapse", (event) => {
        const span = collapseToggle.querySelector("span");
        if (span) {
            span.textContent = "▾";
        }
    });

    collapseToggle.addEventListener("hidden.bs.collapse", (event) => {
        const span = collapseToggle.querySelector("span");
        if (span) {
            span.textContent = "▸";
        }
    });
}