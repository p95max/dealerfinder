document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector("form[action*='contact']");
    if (!form) return;

    const nameInput = form.querySelector("input[name='name']");
    const emailInput = form.querySelector("input[name='email']");
    const messageInput = form.querySelector("textarea[name='message']");
    const submitBtn = document.getElementById("submitBtn");

    function setError(input, message, errorId) {
        const errorEl = document.getElementById(errorId);
        input.classList.add("is-invalid");
        if (errorEl) errorEl.textContent = message;
    }

    function clearError(input, errorId) {
        const errorEl = document.getElementById(errorId);
        input.classList.remove("is-invalid");
        if (errorEl) errorEl.textContent = "";
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
        const value = emailInput.value.trim();
        const isValid = emailInput.checkValidity();

        if (!isValid) {
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
        const valid =
            validateName() &
            validateEmail() &
            validateMessage();

        return Boolean(valid);
    }

    // live validation
    nameInput.addEventListener("input", validateName);
    emailInput.addEventListener("input", validateEmail);
    messageInput.addEventListener("input", validateMessage);

    // submit guard
    form.addEventListener("submit", (e) => {
        if (!validateForm()) {
            e.preventDefault();
        }
    });
});