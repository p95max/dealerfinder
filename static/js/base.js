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

function getContactForm() {
    return document.querySelector("form[action*='contact']");
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

    toggleTurnstileButtonState(hasTurnstileToken && isContactFormValid(form));
}

function onTurnstileSuccess() {
    syncContactSubmitState();
}

function onTurnstileExpired() {
    toggleTurnstileButtonState(false);
}

function onTurnstileError() {
    toggleTurnstileButtonState(false);
}

document.addEventListener("DOMContentLoaded", () => {
    const textarea = document.querySelector('textarea[name="message"]');
    const counter = document.getElementById("messageCounter");

    if (textarea && counter) {
        const updateCounter = () => {
            counter.textContent = textarea.value.length;
        };

        textarea.addEventListener("input", updateCounter);
        updateCounter();
    }
});

document.addEventListener("DOMContentLoaded", () => {
    const form = getContactForm();
    if (!form) {
        return;
    }

    const nameInput = form.querySelector('input[name="name"]');
    const emailInput = form.querySelector('input[name="email"]');
    const messageInput = form.querySelector('textarea[name="message"]');

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
        const nameValid = validateName();
        const emailValid = validateEmail();
        const messageValid = validateMessage();

        return nameValid && emailValid && messageValid;
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
        syncContactSubmitState();
    });

    form.addEventListener("submit", (e) => {
        if (!validateForm()) {
            e.preventDefault();
        }

        syncContactSubmitState();
    });

    syncContactSubmitState();
});

function onLoginTurnstileSuccess() {
    const button = document.getElementById("loginBtn");
    if (button) {
        button.disabled = false;
    }
}

function onLoginTurnstileExpired() {
    const button = document.getElementById("loginBtn");
    if (button) {
        button.disabled = true;
    }
}

function onLoginTurnstileError() {
    const button = document.getElementById("loginBtn");
    if (button) {
        button.disabled = true;
    }
}