function getContactForm() {
    return document.querySelector("form[action*='contact']");
}

function getTurnstileButton(widget) {
    const btnId = widget?.dataset.buttonId;
    if (!btnId) {
        return null;
    }

    return document.getElementById(btnId);
}

function setWidgetButtonState(isEnabled) {
    document.querySelectorAll(".cf-turnstile").forEach((widget) => {
        const button = getTurnstileButton(widget);
        if (button) {
            button.disabled = !isEnabled;
        }
    });
}

function isContactFormValid(form) {
    const nameInput = form.querySelector("input[name='name']");
    const emailInput = form.querySelector("input[name='email']");
    const messageInput = form.querySelector("textarea[name='message']");

    if (!nameInput || !emailInput || !messageInput) {
        return false;
    }

    return (
        nameInput.value.trim().length >= 2 &&
        emailInput.checkValidity() &&
        messageInput.value.trim().length >= 10
    );
}

function syncContactSubmitState() {
    const form = getContactForm();
    if (!form) {
        return;
    }

    const turnstileResponse = form.querySelector('input[name="cf-turnstile-response"]');
    const hasTurnstileToken = Boolean(turnstileResponse && turnstileResponse.value);

    setWidgetButtonState(hasTurnstileToken && isContactFormValid(form));
}

function onContactTurnstileSuccess() {
    syncContactSubmitState();
}

function onContactTurnstileExpired() {
    setWidgetButtonState(false);
}

function onContactTurnstileError() {
    setWidgetButtonState(false);
}

document.addEventListener("DOMContentLoaded", () => {
    const form = getContactForm();
    if (!form) {
        return;
    }

    const nameInput = form.querySelector('input[name="name"]');
    const emailInput = form.querySelector('input[name="email"]');
    const messageInput = form.querySelector('textarea[name="message"]');
    const counter = document.getElementById("messageCounter");

    function setError(input, message, errorId) {
        const errorEl = document.getElementById(errorId);
        input.classList.add("is-invalid");

        if (errorEl) {
            errorEl.textContent = message;
        }
    }

    function clearError(input, errorId) {
        const errorEl = document.getElementById(errorId);
        input.classList.remove("is-invalid");

        if (errorEl) {
            errorEl.textContent = "";
        }
    }

    function validateName() {
        const value = nameInput.value.trim();

        if (value.length < 2) {
            setError(nameInput, "Name must be at least 2 characters", "nameError");
            return false;
        }

        clearError(nameInput, "nameError");
        return true;
    }

    function validateEmail() {
        if (!emailInput.checkValidity()) {
            setError(emailInput, "Enter a valid email address", "emailError");
            return false;
        }

        clearError(emailInput, "emailError");
        return true;
    }

    function validateMessage() {
        const value = messageInput.value.trim();

        if (value.length < 10) {
            setError(messageInput, "Message must be at least 10 characters", "messageError");
            return false;
        }

        clearError(messageInput, "messageError");
        return true;
    }

    function validateForm() {
        const isValid = validateName() && validateEmail() && validateMessage();
        syncContactSubmitState();
        return isValid;
    }

    function updateCounter() {
        if (counter) {
            counter.textContent = messageInput.value.length;
        }
    }

    nameInput.addEventListener("input", () => {
        validateName();
        syncContactSubmitState();
    });

    emailInput.addEventListener("input", () => {
        validateEmail();
        syncContactSubmitState();
    });

    messageInput.addEventListener("input", () => {
        validateMessage();
        updateCounter();
        syncContactSubmitState();
    });

    form.addEventListener("submit", (event) => {
        if (!validateForm()) {
            event.preventDefault();
        }
    });

    updateCounter();
    syncContactSubmitState();
});