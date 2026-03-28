document.addEventListener("DOMContentLoaded", () => {
    const messages = document.querySelectorAll(".flash-message");

    messages.forEach((el) => {
        setTimeout(() => {
            el.style.transition = "opacity 0.3s ease, transform 0.3s ease";
            el.style.opacity = "0";
            el.style.transform = "translateY(-6px)";

            setTimeout(() => el.remove(), 300);
        }, 10000); // timeout 10 sec
    });
});