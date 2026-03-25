function onTurnstileSuccess() {
    const widget = document.querySelector('.cf-turnstile');
    const btnId = widget ? widget.dataset.buttonId : null;
    if (btnId) document.getElementById(btnId).removeAttribute('disabled');
}