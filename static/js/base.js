document.addEventListener("DOMContentLoaded", () => {
    const messages = document.querySelectorAll(".flash-message");

    messages.forEach((el) => {
        setTimeout(() => {
            el.style.transition = "opacity 0.3s ease, transform 0.3s ease";
            el.style.opacity = "0";
            el.style.transform = "translateY(-6px)";

            setTimeout(() => el.remove(), 300);
        }, 10000);
    });
});

document.addEventListener("click", (e) => {
    document.querySelectorAll("details.nav-user-dropdown[open]").forEach((el) => {
        if (!el.contains(e.target)) {
            el.removeAttribute("open");
        }
    });
});

document.addEventListener("DOMContentLoaded", () => {
    const banner = document.getElementById("cookie-banner");
    const overlay = document.getElementById("cookie-overlay");
    const acceptBtn = document.getElementById("cookie-accept-btn");
    const rejectBtn = document.getElementById("cookie-reject-btn");

    if (!banner || !overlay) {
        return;
    }

    function closeCookieBanner() {
        banner.remove();
        overlay.remove();
    }

    async function submitCookieChoice(choice) {
        try {
            const response = await fetch("/users/cookie-consent/", {
                method: "POST",
                headers: {
                    "X-CSRFToken": getCsrfToken(),
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                body: new URLSearchParams({ choice }),
            });

            if (!response.ok) {
                throw new Error("Failed to save cookie consent");
            }

            closeCookieBanner();

            if (choice === "accepted") {
                document.dispatchEvent(new CustomEvent("cookieConsentAccepted"));
            }
        } catch (error) {
            console.error(error);
        }
    }

    acceptBtn?.addEventListener("click", () => {
        submitCookieChoice("accepted");
    });

    rejectBtn?.addEventListener("click", () => {
        submitCookieChoice("rejected");
    });
});

function getCsrfToken() {
    const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (csrfInput) {
        return csrfInput.value;
    }

    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : "";
}